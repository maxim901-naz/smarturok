from __future__ import annotations

from typing import Any


def _clean_text(value: Any) -> str:
    return str(value or '').strip()


def _to_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, default: float = 0.0) -> float:
    if isinstance(value, str):
        value = value.replace(',', '.').strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_spaces(value: str) -> str:
    return ' '.join(value.split())


def parse_test_payload(payload: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    if not isinstance(payload, dict):
        payload = {}

    raw_questions = payload.get('questions')
    if not isinstance(raw_questions, list):
        raw_questions = []

    config = {
        'title': _clean_text(payload.get('title')),
        'passing_score_percent': max(1, min(100, _to_int(payload.get('passing_score_percent'), 70))),
        'duration_minutes': max(0, _to_int(payload.get('duration_minutes'), 0)),
        'show_correct_after_submit': bool(payload.get('show_correct_after_submit', True)),
    }

    questions: list[dict[str, Any]] = []
    for idx, raw in enumerate(raw_questions, start=1):
        if not isinstance(raw, dict):
            continue

        qid = _clean_text(raw.get('id') or f'q{idx}')
        raw_type = _clean_text(raw.get('type') or raw.get('question_type') or 'text').lower()
        qtype = {
            'single': 'single',
            'single_choice': 'single',
            'radio': 'single',
            'multiple': 'multiple',
            'multiple_choice': 'multiple',
            'checkbox': 'multiple',
            'text': 'text',
            'short_text': 'text',
            'number': 'number',
        }.get(raw_type, 'text')

        prompt = _clean_text(raw.get('prompt') or raw.get('question') or raw.get('title'))
        if not prompt:
            continue

        points = max(1, min(100, _to_int(raw.get('points'), 1)))
        question: dict[str, Any] = {
            'id': qid,
            'order': idx,
            'type': qtype,
            'prompt': prompt,
            'image_url': _clean_text(raw.get('image_url') or raw.get('image')),
            'image_alt': _clean_text(raw.get('image_alt')),
            'points': points,
            'required': bool(raw.get('required', True)),
            'explanation': _clean_text(raw.get('explanation')),
        }

        if qtype in {'single', 'multiple'}:
            options: list[dict[str, str]] = []
            raw_options = raw.get('options')
            if isinstance(raw_options, list):
                for opt in raw_options:
                    if isinstance(opt, dict):
                        value = _clean_text(opt.get('value') or opt.get('id') or opt.get('label') or opt.get('text'))
                        label = _clean_text(opt.get('label') or opt.get('text') or value)
                        image_url = _clean_text(opt.get('image_url') or opt.get('image'))
                        image_alt = _clean_text(opt.get('image_alt'))
                    else:
                        value = _clean_text(opt)
                        label = value
                        image_url = ''
                        image_alt = ''
                    if value:
                        options.append({
                            'value': value,
                            'label': label,
                            'image_url': image_url,
                            'image_alt': image_alt,
                        })

            if len(options) < 2:
                continue

            correct_values: set[str] = set()
            raw_correct = raw.get('correct')
            if isinstance(raw_correct, list):
                correct_values = {_clean_text(item) for item in raw_correct if _clean_text(item)}
            else:
                single_value = _clean_text(raw_correct)
                if single_value:
                    correct_values = {single_value}

            if not correct_values:
                continue

            question['options'] = options
            question['correct_values'] = correct_values

        elif qtype == 'number':
            if raw.get('correct') is None:
                continue
            question['correct_number'] = _to_float(raw.get('correct'))
            question['tolerance'] = max(0.0, _to_float(raw.get('tolerance'), 0.0))

        else:
            raw_correct = raw.get('correct')
            texts: list[str] = []
            if isinstance(raw_correct, list):
                texts.extend([_clean_text(item) for item in raw_correct if _clean_text(item)])
            else:
                correct_value = _clean_text(raw_correct)
                if correct_value:
                    texts.append(correct_value)

            aliases = raw.get('aliases')
            if isinstance(aliases, list):
                texts.extend([_clean_text(item) for item in aliases if _clean_text(item)])

            if not texts:
                continue

            question['case_sensitive'] = bool(raw.get('case_sensitive', False))
            question['correct_texts'] = texts
            question['placeholder'] = _clean_text(raw.get('placeholder'))

        questions.append(question)

    return config, questions


def build_public_questions(questions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    public_questions: list[dict[str, Any]] = []
    for q in questions:
        public_q = {
            'id': q['id'],
            'order': q['order'],
            'type': q['type'],
            'prompt': q['prompt'],
            'image_url': q.get('image_url', ''),
            'image_alt': q.get('image_alt', ''),
            'points': q['points'],
            'required': q.get('required', True),
        }
        if q['type'] in {'single', 'multiple'}:
            public_q['options'] = q.get('options', [])
        if q['type'] == 'text':
            public_q['placeholder'] = q.get('placeholder', '')
        public_questions.append(public_q)
    return public_questions


def extract_answers(post_data: Any, questions: list[dict[str, Any]]) -> dict[str, Any]:
    answers: dict[str, Any] = {}
    for q in questions:
        field_name = f"answer_{q['id']}"
        if q['type'] == 'multiple':
            values = [value.strip() for value in post_data.getlist(field_name) if str(value).strip()]
            answers[q['id']] = values
        else:
            answers[q['id']] = str(post_data.get(field_name, '') or '').strip()
    return answers


def _normalize_text_answer(value: str, case_sensitive: bool) -> str:
    normalized = _normalize_spaces(value.strip())
    return normalized if case_sensitive else normalized.lower()


def evaluate_answers(
    questions: list[dict[str, Any]],
    answers: dict[str, Any],
    passing_score_percent: int,
) -> dict[str, Any]:
    max_points = sum(int(q['points']) for q in questions)
    earned_points = 0
    question_results: list[dict[str, Any]] = []

    for q in questions:
        qid = q['id']
        qtype = q['type']
        points = int(q['points'])
        user_answer = answers.get(qid)

        is_correct = False
        is_answered = False
        answer_display = ''
        correct_display = ''

        if qtype == 'single':
            answer_value = _clean_text(user_answer)
            is_answered = bool(answer_value)
            answer_display = answer_value
            correct_values = q.get('correct_values', set())
            is_correct = answer_value in correct_values
            correct_display = ', '.join(sorted(correct_values))

        elif qtype == 'multiple':
            answer_values = [item for item in (user_answer or []) if _clean_text(item)]
            answer_set = {_clean_text(item) for item in answer_values}
            correct_values = set(q.get('correct_values', set()))
            is_answered = bool(answer_set)
            answer_display = ', '.join(sorted(answer_set))
            is_correct = bool(answer_set) and answer_set == correct_values
            correct_display = ', '.join(sorted(correct_values))

        elif qtype == 'number':
            raw_value = _clean_text(user_answer)
            is_answered = bool(raw_value)
            answer_display = raw_value
            if is_answered:
                value = _to_float(raw_value, default=float('nan'))
                correct_number = float(q.get('correct_number', 0.0))
                tolerance = float(q.get('tolerance', 0.0))
                if value == value:
                    is_correct = abs(value - correct_number) <= tolerance
            correct_display = str(q.get('correct_number', ''))

        else:
            raw_value = _clean_text(user_answer)
            is_answered = bool(raw_value)
            answer_display = raw_value
            case_sensitive = bool(q.get('case_sensitive', False))
            normalized_user = _normalize_text_answer(raw_value, case_sensitive)
            normalized_correct = {
                _normalize_text_answer(item, case_sensitive)
                for item in q.get('correct_texts', [])
            }
            is_correct = bool(normalized_user) and normalized_user in normalized_correct
            correct_display = ' / '.join(q.get('correct_texts', []))

        earned = points if is_correct else 0
        earned_points += earned
        question_results.append({
            'id': qid,
            'prompt': q['prompt'],
            'type': qtype,
            'points': points,
            'earned_points': earned,
            'is_correct': is_correct,
            'is_answered': is_answered,
            'answer_display': answer_display,
            'correct_display': correct_display,
            'explanation': q.get('explanation', ''),
        })

    score_percent = round((earned_points / max_points * 100) if max_points else 0.0, 2)
    passed = score_percent >= float(passing_score_percent)

    return {
        'max_points': max_points,
        'earned_points': earned_points,
        'score_percent': score_percent,
        'passed': passed,
        'question_results': question_results,
    }
