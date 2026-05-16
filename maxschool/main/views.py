import re
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.core.cache import cache
from django.db.models import Count, F, Max, Q
from django.utils import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.urls import reverse

from accounts.models import BalanceTopUpRequest, CustomUser, TrialRequest, Subject
from .models import MaterialCategory, MaterialItem, MaterialTestAttempt, Review
from .test_engine import (
    build_public_questions,
    evaluate_answers,
    extract_answers,
    parse_test_payload,
)


def _get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', '').strip()


def _clean_tracking_value(value, max_length=255):
    return (value or '').strip().replace('\r', ' ').replace('\n', ' ')[:max_length]


def _analytics_context():
    return {
        'ga4_id': settings.GA4_MEASUREMENT_ID,
        'yandex_id': settings.YANDEX_METRIKA_COUNTER_ID,
        'meta_pixel_id': settings.META_PIXEL_ID,
    }


def _split_lines(text):
    return [line.strip() for line in (text or '').splitlines() if line.strip()]


def _split_delimited_lines(text, parts_count):
    rows = []
    for line in _split_lines(text):
        parts = [part.strip() for part in line.split('|', parts_count - 1)]
        if len(parts) != parts_count:
            continue
        if not all(parts):
            continue
        rows.append(parts)
    return rows


def _published_materials_qs():
    return (
        MaterialItem.objects
        .filter(status='published')
        .select_related('category', 'subject', 'related_theory', 'related_test')
    )


THEORY_CONTENT_TYPES = ('article', 'video', 'pdf')
MATERIAL_SECTION_CHOICES = {'all', 'theory', 'practice', 'tests', 'mock'}
EXAM_SEARCH_ALIASES = {
    'огэ': 'oge',
    'oge': 'oge',
    'егэ': 'ege',
    'ege': 'ege',
    'впр': 'school',
    'мцко': 'school',
}


def _normalize_material_section(section):
    normalized = (section or 'all').strip().lower()
    return normalized if normalized in MATERIAL_SECTION_CHOICES else 'all'


def _apply_material_section_filter(queryset, section):
    if section == 'theory':
        return queryset.filter(content_type__in=THEORY_CONTENT_TYPES)
    if section == 'practice':
        return queryset.filter(
            content_type__in=THEORY_CONTENT_TYPES,
            exam_type__in=('oge', 'ege', 'school'),
        )
    if section == 'tests':
        return queryset.filter(content_type='test')
    if section == 'mock':
        return queryset.filter(content_type='test', exam_type__in=('oge', 'ege'))
    return queryset


def _order_materials(queryset):
    return queryset.order_by(F('task_number').asc(nulls_last=True), '-published_at', '-created_at')


def _material_search_token_q(token):
    token = token.strip().lower()
    if not token:
        return Q()

    token_q = (
        Q(title__icontains=token)
        | Q(description__icontains=token)
        | Q(meta_description__icontains=token)
        | Q(article_markdown__icontains=token)
        | Q(subject__name__icontains=token)
        | Q(category__title__icontains=token)
        | Q(category__slug__icontains=token)
    )

    alias_exam_type = EXAM_SEARCH_ALIASES.get(token)
    if alias_exam_type:
        token_q |= Q(exam_type=alias_exam_type)

    if token.isdigit():
        value = int(token)
        token_q |= Q(grade=value) | Q(task_number=value)

    return token_q


def _apply_material_search_filter(queryset, search_query):
    query = (search_query or '').strip()
    if not query:
        return queryset

    tokens = [token for token in re.split(r'\s+', query.lower()) if token]
    if not tokens:
        return queryset

    # Keep AND semantics between tokens, while each token can match multiple fields.
    for token in tokens:
        queryset = queryset.filter(_material_search_token_q(token))
    return queryset


def _pick_related_material(material, target='test'):
    queryset = _published_materials_qs().exclude(pk=material.pk)

    if material.category_id:
        queryset = queryset.filter(category_id=material.category_id)
    if material.subject_id:
        queryset = queryset.filter(subject_id=material.subject_id)
    if material.exam_type:
        queryset = queryset.filter(exam_type=material.exam_type)

    if target == 'test':
        queryset = queryset.filter(content_type='test')
    else:
        queryset = queryset.filter(content_type__in=THEORY_CONTENT_TYPES)

    if material.task_number is not None:
        same_task_qs = queryset.filter(task_number=material.task_number)
        if same_task_qs.exists():
            queryset = same_task_qs

    return _order_materials(queryset).first()


def _user_has_paid_material_access(user):
    if not user.is_authenticated:
        return False

    user_role = getattr(user, 'role', '')
    if user.is_staff or user_role in ('admin', 'teacher'):
        return True

    if getattr(user, 'balance', 0) > 0:
        return True

    return BalanceTopUpRequest.objects.filter(user=user, status='approved').exists()


def _material_is_accessible(user, material):
    if material.access_level == 'public':
        return True
    if material.access_level == 'authenticated':
        return user.is_authenticated
    if material.access_level == 'paid':
        return _user_has_paid_material_access(user)
    return False


def _material_video_embed_url(video_url):
    if not video_url:
        return ''

    parsed = urlparse(video_url.strip())
    host = (parsed.netloc or '').lower()
    path = (parsed.path or '').strip('/')

    if 'youtu.be' in host:
        video_id = path.split('/')[0]
        return f'https://www.youtube.com/embed/{video_id}' if video_id else ''

    if 'youtube.com' in host:
        if path.startswith('shorts/'):
            parts = path.split('/')
            if len(parts) >= 2:
                return f'https://www.youtube.com/embed/{parts[1]}'
        query = parse_qs(parsed.query)
        video_id = (query.get('v') or [''])[0]
        return f'https://www.youtube.com/embed/{video_id}' if video_id else ''

    if 'vimeo.com' in host:
        video_id = path.split('/')[0]
        if video_id.isdigit():
            return f'https://player.vimeo.com/video/{video_id}'

    return ''



def _next_test_attempt_no(material, user=None, session_key=''):
    queryset = MaterialTestAttempt.objects.filter(material=material)
    if user is not None:
        queryset = queryset.filter(user=user)
    elif session_key:
        queryset = queryset.filter(user__isnull=True, session_key=session_key)
    else:
        return 1

    last_no = queryset.aggregate(max_no=Max('attempt_no'))['max_no'] or 0
    return last_no + 1


def _build_test_from_bank(material):
    test_bank = getattr(material, 'test_bank', None)
    if not test_bank or not test_bank.is_active:
        return {}, []

    questions = []
    question_queryset = (
        test_bank.questions
        .filter(is_active=True)
        .order_by('order', 'id')
        .prefetch_related('options')
    )
    for idx, question in enumerate(question_queryset, start=1):
        q_type = question.question_type
        item = {
            'id': question.code or f'q{idx}',
            'order': idx,
            'type': q_type,
            'prompt': question.prompt,
            'image_url': question.image.url if question.image else '',
            'image_alt': (question.image_alt or '').strip(),
            'points': max(1, int(question.points or 1)),
            'required': bool(question.required),
            'explanation': (question.explanation or '').strip(),
        }

        if q_type in {'single', 'multiple'}:
            options = list(
                question.options
                .filter(is_active=True)
                .order_by('order', 'id')
            )
            if len(options) < 2:
                continue
            correct_values = {option.value for option in options if option.is_correct}
            if not correct_values:
                continue
            item['options'] = [
                {
                    'value': option.value,
                    'label': option.label,
                    'image_url': option.image.url if option.image else '',
                    'image_alt': (option.image_alt or '').strip(),
                }
                for option in options
            ]
            item['correct_values'] = correct_values

        elif q_type == 'number':
            if question.correct_number is None:
                continue
            item['correct_number'] = float(question.correct_number)
            item['tolerance'] = float(question.number_tolerance or 0)

        else:
            correct_texts = _split_lines(question.correct_text)
            if not correct_texts:
                continue
            item['case_sensitive'] = bool(question.case_sensitive)
            item['correct_texts'] = correct_texts
            item['placeholder'] = question.placeholder or ''

        questions.append(item)

    config = {
        'title': (test_bank.title or material.title).strip(),
        'passing_score_percent': max(1, min(100, int(test_bank.passing_score_percent or 70))),
        'duration_minutes': max(0, int(test_bank.duration_minutes or 0)),
        'show_correct_after_submit': bool(test_bank.show_correct_after_submit),
        'max_attempts': int(test_bank.max_attempts) if test_bank.max_attempts else None,
        'source': 'bank',
    }
    return config, questions


def _load_material_test_content(material):
    bank_config, bank_questions = _build_test_from_bank(material)
    if bank_questions:
        return bank_config, bank_questions

    payload_config, payload_questions = parse_test_payload(material.test_payload)
    payload_config['source'] = 'payload'
    return payload_config, payload_questions


def home(request):
    teachers = CustomUser.objects.filter(role='teacher', is_approved=True).prefetch_related('subjects_taught', 'desired_subject')
    subjects = Subject.objects.all()
    reviews = Review.objects.filter(is_published=True).order_by('-created_at')[:12]
    material_categories_qs = (
        MaterialCategory.objects
        .filter(is_active=True)
        .annotate(
            published_count=Count(
                'materials',
                filter=Q(materials__status='published'),
                distinct=True,
            )
        )
        .order_by('sort_order', 'title')
    )
    home_material_categories = list(material_categories_qs[:8])
    home_latest_materials = list(_published_materials_qs().order_by('-published_at', '-created_at')[:4])
    materials_categories_total = material_categories_qs.count()
    materials_total_count = _published_materials_qs().count()
    return render(request, 'main/index.html', {
        'teachers': teachers,
        'subjects': subjects,
        'reviews': reviews,
        'home_material_categories': home_material_categories,
        'home_latest_materials': home_latest_materials,
        'materials_categories_total': materials_categories_total,
        'materials_total_count': materials_total_count,
        'analytics': _analytics_context(),
    })


def teachers_list(request):
    teachers = (
        CustomUser.objects
        .filter(role='teacher', is_approved=True)
        .prefetch_related('subjects_taught', 'desired_subject')
    )

    subjects = (
        Subject.objects
        .filter(
            Q(teachers__role='teacher', teachers__is_approved=True)
            | Q(customuser__role='teacher', customuser__is_approved=True)
        )
        .distinct()
        .order_by('name')
    )

    selected_subject = (request.GET.get('subject') or '').strip()
    search_query = (request.GET.get('q') or '').strip()

    if selected_subject and selected_subject.isdigit():
        subject_id = int(selected_subject)
        teachers = teachers.filter(
            Q(subjects_taught__id=subject_id) | Q(desired_subject__id=subject_id)
        )
    else:
        selected_subject = ''

    if search_query:
        teachers = teachers.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
        )

    teachers = teachers.distinct()
    return render(request, 'main/teachers_list.html', {
        'teachers': teachers,
        'subjects': subjects,
        'selected_subject': selected_subject,
        'search_query': search_query,
    })


def materials_list(request):
    search_query = (request.GET.get('q') or '').strip()
    categories = MaterialCategory.objects.filter(is_active=True).order_by('sort_order', 'title')
    items_qs = _published_materials_qs()
    if search_query:
        items_qs = _apply_material_search_filter(items_qs, search_query)
    search_total = items_qs.count() if search_query else 0
    latest_items = _order_materials(items_qs)[:24]
    subjects = Subject.objects.all()
    return render(request, 'main/materials_list.html', {
        'categories': categories,
        'latest_items': latest_items,
        'subjects': subjects,
        'search_query': search_query,
        'search_total': search_total,
    })


def materials_category(request, slug):
    category = get_object_or_404(MaterialCategory, slug=slug, is_active=True)
    base_items = _published_materials_qs().filter(category=category)
    subjects = Subject.objects.all()

    subject_id = request.GET.get('subject')
    grade = request.GET.get('grade')
    search_query = (request.GET.get('q') or '').strip()
    selected_section = _normalize_material_section(request.GET.get('section'))

    if subject_id and subject_id.isdigit():
        base_items = base_items.filter(subject_id=int(subject_id))
    if grade and grade.isdigit():
        base_items = base_items.filter(grade=int(grade))
    if search_query:
        base_items = _apply_material_search_filter(base_items, search_query)

    section_counts = {
        'all': base_items.count(),
        'theory': _apply_material_section_filter(base_items, 'theory').count(),
        'practice': _apply_material_section_filter(base_items, 'practice').count(),
        'tests': _apply_material_section_filter(base_items, 'tests').count(),
        'mock': _apply_material_section_filter(base_items, 'mock').count(),
    }

    items = _order_materials(_apply_material_section_filter(base_items, selected_section))

    return render(request, 'main/materials_category.html', {
        'category': category,
        'items': items,
        'subjects': subjects,
        'selected_subject': subject_id or '',
        'selected_grade': grade or '',
        'search_query': search_query,
        'selected_section': selected_section,
        'section_counts': section_counts,
        'grade_options': [4, 5, 6, 7, 8],
    })


def material_detail(request, slug):
    material = get_object_or_404(_published_materials_qs(), slug=slug)

    if not _material_is_accessible(request.user, material):
        if not request.user.is_authenticated:
            messages.info(request, 'Sign in to open this material.')
            return redirect(f"{reverse('login')}?next={request.path}")

        if material.access_level == 'paid':
            messages.warning(request, 'This material is available only after paid package activation.')
            return redirect('student_balance')

        messages.warning(request, 'You do not have enough permissions to access this material.')
        return redirect('materials_list')

    MaterialItem.objects.filter(pk=material.pk).update(views_count=F('views_count') + 1)
    material.views_count = (material.views_count or 0) + 1

    related_theory = None
    related_test = None

    if material.related_theory and material.related_theory.status == 'published':
        if _material_is_accessible(request.user, material.related_theory):
            related_theory = material.related_theory

    if material.related_test and material.related_test.status == 'published':
        if _material_is_accessible(request.user, material.related_test):
            related_test = material.related_test

    if material.content_type == 'test' and not related_theory:
        related_candidate = _pick_related_material(material, target='theory')
        if related_candidate and _material_is_accessible(request.user, related_candidate):
            related_theory = related_candidate
    elif material.content_type in THEORY_CONTENT_TYPES and not related_test:
        related_candidate = _pick_related_material(material, target='test')
        if related_candidate and _material_is_accessible(request.user, related_candidate):
            related_test = related_candidate

    test_config = {}
    test_questions = []
    selected_attempt = None
    selected_attempt_results = []
    latest_attempts = []

    if material.content_type == 'test':
        test_config, parsed_questions = _load_material_test_content(material)
        test_questions = build_public_questions(parsed_questions)

        if request.user.is_authenticated:
            latest_attempts = list(
                MaterialTestAttempt.objects
                .filter(material=material, user=request.user)
                .order_by('-submitted_at')[:10]
            )
        else:
            if not request.session.session_key:
                request.session.save()
            latest_attempts = list(
                MaterialTestAttempt.objects
                .filter(material=material, user__isnull=True, session_key=request.session.session_key)
                .order_by('-submitted_at')[:5]
            )

        if request.method == 'POST':
            if not parsed_questions:
                messages.error(request, 'This test is not configured yet. Add questions in admin.')
                return redirect(request.path)

            started_ts = request.POST.get('test_started_ts', '').strip()
            duration_seconds = 0
            if started_ts:
                try:
                    started_float = float(started_ts)
                    duration_seconds = max(0, int(timezone.now().timestamp() - started_float))
                except (TypeError, ValueError):
                    duration_seconds = 0

            answers = extract_answers(request.POST, parsed_questions)
            result = evaluate_answers(
                questions=parsed_questions,
                answers=answers,
                passing_score_percent=int(test_config.get('passing_score_percent', 70)),
            )

            session_key = ''
            user = request.user if request.user.is_authenticated else None
            if user is None:
                if not request.session.session_key:
                    request.session.save()
                session_key = request.session.session_key or ''

            next_attempt_no = _next_test_attempt_no(material, user=user, session_key=session_key)
            max_attempts = test_config.get('max_attempts')
            if max_attempts and next_attempt_no > int(max_attempts):
                messages.warning(request, 'Attempt limit reached for this test.')
                return redirect(request.path)

            attempt = MaterialTestAttempt.objects.create(
                material=material,
                user=user,
                session_key=session_key,
                attempt_no=next_attempt_no,
                max_points=result['max_points'],
                score_points=result['earned_points'],
                score_percent=result['score_percent'],
                passed=result['passed'],
                duration_seconds=duration_seconds,
                answers_payload=answers,
                result_payload={
                    'config': test_config,
                    'questions': result['question_results'],
                },
            )

            if result['passed']:
                messages.success(
                    request,
                    f"Test passed: {result['earned_points']} of {result['max_points']} ({result['score_percent']}%).",
                )
            else:
                messages.warning(
                    request,
                    f"Result: {result['earned_points']} of {result['max_points']} ({result['score_percent']}%). You can try again.",
                )

            return redirect(f"{request.path}?attempt={attempt.id}")

        attempt_id = request.GET.get('attempt', '').strip()
        if attempt_id.isdigit():
            attempts_qs = MaterialTestAttempt.objects.filter(material=material, id=int(attempt_id))
            if request.user.is_authenticated:
                if request.user.is_staff or getattr(request.user, 'role', '') in ('admin', 'teacher'):
                    selected_attempt = attempts_qs.first()
                else:
                    selected_attempt = attempts_qs.filter(user=request.user).first()
            elif request.session.session_key:
                selected_attempt = attempts_qs.filter(
                    user__isnull=True,
                    session_key=request.session.session_key,
                ).first()
        elif latest_attempts:
            selected_attempt = latest_attempts[0]

        if selected_attempt:
            payload = selected_attempt.result_payload if isinstance(selected_attempt.result_payload, dict) else {}
            if isinstance(payload.get('questions'), list):
                selected_attempt_results = payload['questions']

    return render(request, 'main/material_detail.html', {
        'material': material,
        'video_embed_url': _material_video_embed_url(material.video_url),
        'test_config': test_config,
        'test_questions': test_questions,
        'test_attempt': selected_attempt,
        'test_attempt_results': selected_attempt_results,
        'latest_attempts': latest_attempts,
        'test_source': test_config.get('source', ''),
        'related_theory': related_theory,
        'related_test': related_test,
    })

def subject_detail(request, slug):
    subject = get_object_or_404(Subject, slug=slug)
    teachers = (
        CustomUser.objects
        .filter(role='teacher', is_approved=True)
        .filter(Q(subjects_taught=subject) | Q(desired_subject=subject))
        .distinct()[:6]
    )

    metrics_rows = _split_delimited_lines(subject.metrics, 2)
    if not metrics_rows:
        metrics_rows = [
            ['Формат', 'Индивидуально 1:1'],
            ['Возраст', 'Дети и подростки'],
            ['Контроль прогресса', 'После каждого урока'],
            ['Старт', 'С пробного урока'],
        ]
    metrics = [{'label': row[0], 'value': row[1]} for row in metrics_rows[:4]]

    results_title = subject.results_title or 'Почему этот курс дает результат'
    result_points_rows = _split_delimited_lines(subject.result_points, 2)
    if not result_points_rows:
        result_points_rows = [
            ['Диагностика на старте', 'Понимаем текущий уровень и сразу строим персональный план.'],
            ['Стабильная практика', 'Ученик тренируется на заданиях нужного формата без перегруза.'],
        ]
    result_points = [{'title': row[0], 'description': row[1]} for row in result_points_rows[:4]]

    include_items_title = subject.include_items_title or 'Что входит в обучение'
    include_items = _split_lines(subject.include_items)
    if not include_items:
        include_items = [
            'Индивидуальные занятия 1 на 1',
            'Домашние задания с разбором ошибок',
            'Обратная связь для родителя',
            'Гибкий график и перенос уроков',
        ]

    benefits = _split_lines(subject.benefits)
    if not benefits:
        benefits = [
            'Понимание ключевых тем и уверенность на уроках в школе.',
            'Индивидуальный план подготовки под уровень ученика.',
            'Регулярная обратная связь для родителей по прогрессу.',
            'Домашние задания с разбором ошибок и поддержкой преподавателя.',
        ]

    program = _split_lines(subject.program)
    if not program:
        program = [
            'Диагностика уровня и постановка учебной цели.',
            'База и закрытие пробелов по теме.',
            'Интенсивная практика на заданиях формата экзаменов.',
            'Итоговый контроль и план на следующий этап.',
        ]

    progress_title = subject.progress_title or 'Что меняется уже в первые 2-4 недели'
    progress_subtitle = subject.progress_subtitle or 'Фокус на понятность, скорость решения и уверенность ученика на школьных уроках.'
    progress_cards_rows = _split_delimited_lines(subject.progress_cards, 3)
    if not progress_cards_rows:
        progress_cards_rows = [
            ['Понимание тем', '+ глубокое', 'Ученик перестает учить "по шаблону" и начинает понимать логику.'],
            ['Домашние задания', 'быстрее', 'Уходит зависание на задачах, появляется уверенный темп решения.'],
            ['Оценки и контроль', 'стабильнее', 'Результат становится предсказуемым за счет системной работы.'],
        ]
    progress_cards = [
        {'title': row[0], 'highlight': row[1], 'description': row[2]}
        for row in progress_cards_rows[:3]
    ]

    hero_title = subject.hero_title or f'{subject.name} онлайн с опытным преподавателем'
    hero_subtitle = subject.hero_subtitle or 'Индивидуальные занятия, понятные объяснения и стабильный прогресс с первых недель обучения.'
    page_title = subject.seo_title or f'{subject.name} онлайн для школьников | SmartUrok'
    page_description = subject.seo_description or f'Индивидуальные онлайн-занятия по предмету «{subject.name}». Подберем преподавателя и начнем с бесплатного пробного урока.'

    return render(request, 'main/subject_detail.html', {
        'subject': subject,
        'teachers': teachers,
        'metrics': metrics,
        'results_title': results_title,
        'result_points': result_points,
        'include_items_title': include_items_title,
        'include_items': include_items,
        'benefits': benefits,
        'program': program,
        'progress_title': progress_title,
        'progress_subtitle': progress_subtitle,
        'progress_cards': progress_cards,
        'hero_title': hero_title,
        'hero_subtitle': hero_subtitle,
        'page_title': page_title,
        'page_description': page_description,
        'analytics': _analytics_context(),
    })


def privacy_policy(request):
    return render(request, 'main/privacy_policy.html')


def public_offer(request):
    return render(request, 'main/public_offer.html')


def home_lead(request):
    if request.method != 'POST':
        return redirect('home')

    # Honeypot: bots often fill hidden fields.
    if (request.POST.get('website') or '').strip():
        return redirect('home')

    def _parse_positive_int(value):
        cleaned = (value or '').strip().replace(' ', '').replace(',', '')
        if not cleaned.isdigit():
            return None
        return int(cleaned)

    name = (request.POST.get('name') or '').strip()
    email = (request.POST.get('email') or '').strip()
    phone = (request.POST.get('phone') or '').strip()
    preferred_time = (request.POST.get('preferred_time') or '').strip()
    message = (request.POST.get('message') or '').strip()
    subject_id = (request.POST.get('subject') or '').strip()
    promo_interest = _clean_tracking_value(request.POST.get('promo_interest'), max_length=120)
    pricing_subject_id = (request.POST.get('pricing_subject_id') or '').strip()
    pricing_subject_name = _clean_tracking_value(request.POST.get('pricing_subject_name'), max_length=120)
    pricing_lessons_count = _parse_positive_int(request.POST.get('pricing_lessons_count'))
    pricing_discount_percent = _parse_positive_int(request.POST.get('pricing_discount_percent'))
    pricing_total_price = _parse_positive_int(request.POST.get('pricing_total_price'))
    pricing_old_price = _parse_positive_int(request.POST.get('pricing_old_price'))
    consent_given = request.POST.get('privacy_consent') == '1'
    lead_form = _clean_tracking_value(request.POST.get('lead_form'), max_length=64)
    attribution_map = [
        ('Форма', lead_form),
        ('UTM source', _clean_tracking_value(request.POST.get('utm_source'))),
        ('UTM medium', _clean_tracking_value(request.POST.get('utm_medium'))),
        ('UTM campaign', _clean_tracking_value(request.POST.get('utm_campaign'))),
        ('UTM content', _clean_tracking_value(request.POST.get('utm_content'))),
        ('UTM term', _clean_tracking_value(request.POST.get('utm_term'))),
        ('GCLID', _clean_tracking_value(request.POST.get('gclid'))),
        ('FBCLID', _clean_tracking_value(request.POST.get('fbclid'))),
        ('YCLID', _clean_tracking_value(request.POST.get('yclid'))),
        ('Landing', _clean_tracking_value(request.POST.get('landing_path'), max_length=500)),
        ('Referrer', _clean_tracking_value(request.POST.get('referrer'), max_length=500)),
    ]

    client_ip = _get_client_ip(request) or 'unknown'
    user_agent = (request.META.get('HTTP_USER_AGENT') or '')[:255]

    # Promo modal should keep only explicit interest from popup chips.
    # Calculator pricing context is ignored here to avoid ambiguous leads.
    if lead_form == 'promo_modal':
        subject_id = ''
        pricing_subject_name = ''
        pricing_lessons_count = None
        pricing_discount_percent = None
        pricing_total_price = None
        pricing_old_price = None
    else:
        promo_interest = ''
        if not subject_id and pricing_subject_id.isdigit():
            subject_id = pricing_subject_id

    subject = None
    if subject_id.isdigit():
        subject = Subject.objects.filter(id=int(subject_id)).first()

    if not name or not email or not phone:
        messages.error(request, 'Пожалуйста, заполните имя, email и телефон.')
        return redirect('home')

    if not consent_given:
        messages.error(request, 'Нужно подтвердить согласие на обработку персональных данных.')
        return redirect('home')

    # Basic per-IP throttling to reduce spam.
    throttle_key = f'home_lead:ip:{client_ip}'
    attempts = cache.get(throttle_key, 0)
    if attempts >= 5:
        messages.error(request, 'Слишком много запросов. Попробуйте чуть позже.')
        return redirect('home')
    cache.set(throttle_key, attempts + 1, timeout=10 * 60)

    # Short dedupe window for accidental repeated submits.
    duplicate_from = timezone.now() - timedelta(minutes=3)
    if TrialRequest.objects.filter(
        email__iexact=email,
        phone=phone,
        created_at__gte=duplicate_from,
    ).exists():
        messages.info(request, 'Заявка уже отправлена. Мы скоро свяжемся с вами.')
        return redirect('home')

    attribution_lines = [f'{label}: {value}' for label, value in attribution_map if value]
    if attribution_lines:
        attribution_block = 'Маркетинг-атрибуция:\n' + '\n'.join(attribution_lines)
        message = f'{message}\n\n{attribution_block}' if message else attribution_block

    TrialRequest.objects.create(
        name=name,
        email=email,
        phone=phone,
        subject=subject,
        preferred_time=preferred_time,
        message=message,
        lead_form=lead_form,
        promo_interest=promo_interest,
        pricing_subject_name=pricing_subject_name,
        pricing_lessons_count=pricing_lessons_count,
        pricing_discount_percent=pricing_discount_percent,
        pricing_total_price=pricing_total_price,
        pricing_old_price=pricing_old_price,
        personal_data_consent=True,
        consent_at=timezone.now(),
        consent_ip=client_ip if client_ip != 'unknown' else None,
        consent_user_agent=user_agent,
    )
    messages.success(request, 'Заявка отправлена! Мы свяжемся с вами в ближайшее время.')
    return redirect('home')


def submit_review(request):
    if request.method != 'POST':
        return redirect('home')

    name = (request.POST.get('name') or '').strip()
    text = (request.POST.get('text') or '').strip()
    rating = request.POST.get('rating') or '5'

    try:
        rating_val = int(rating)
    except ValueError:
        rating_val = 5
    rating_val = max(1, min(5, rating_val))

    if not name or not text:
        messages.error(request, 'Пожалуйста, заполните имя и отзыв.')
        return redirect('home')

    Review.objects.create(
        name=name,
        text=text,
        rating=rating_val,
        is_published=False
    )
    messages.success(request, 'Спасибо! Отзыв отправлен и появится после модерации.')
    return redirect('home')
