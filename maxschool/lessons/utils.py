from datetime import date, datetime, timedelta

from django.utils import timezone
from zoneinfo import ZoneInfo

from accounts.models import Lesson
from .models import TeacherAvailability

# Единый источник правды по длине серии
SERIES_WEEKS = 8
BOOKING_MIN_HOURS = 4
TEACHER_TZ_NAME = "Europe/Moscow"
TEACHER_TZ = ZoneInfo(TEACHER_TZ_NAME)


def get_teacher_tz(teacher):
    return TEACHER_TZ


def _time_to_minutes(value):
    return value.hour * 60 + value.minute


def _has_lesson_overlap(teacher, lesson_date, lesson_time, duration_minutes):
    start_min = _time_to_minutes(lesson_time)
    end_min = start_min + (duration_minutes or 30)
    lessons = Lesson.objects.filter(teacher=teacher, date=lesson_date).exclude(
        lesson_status__in=['missed_student', 'missed_teacher']
    )
    for lesson in lessons:
        lesson_start = _time_to_minutes(lesson.time)
        lesson_end = lesson_start + (lesson.duration_minutes or 30)
        if start_min < lesson_end and lesson_start < end_min:
            return True
    return False


def build_calendar_events(teacher, weeks=SERIES_WEEKS):
    events = []
    teacher_tz = get_teacher_tz(teacher)
    now_local = timezone.now().astimezone(teacher_tz)
    today = now_local.date()
    end_date = today + timedelta(weeks=weeks)

    # 1. Уроки в периоде
    lessons = Lesson.objects.filter(
        teacher=teacher,
        date__gte=today,
        date__lte=end_date,
    ).exclude(lesson_status__in=['missed_student','missed_teacher'])
    for lesson in lessons:
        lesson_start = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        lesson_end = lesson_start + timedelta(minutes=lesson.duration_minutes or 30)
        is_recurring = bool(lesson.is_recurring)

        events.append({
            "id": f"lesson-{lesson.id}",
            "title": f"{lesson.subject.name} — {lesson.student.get_full_name() or lesson.student.username}" + (" (рег.)" if is_recurring else ""),
            "start": lesson_start.isoformat(),
            "end": lesson_end.isoformat(),
            "color": "#FBBF24" if is_recurring else "#F87171",
            "textColor": "white",
            "borderColor": "#D97706" if is_recurring else "#DC2626",
            "extendedProps": {
                "type": "lesson",
                "lesson_id": lesson.id,
                "student_id": lesson.student.id,
                "student_name": lesson.student.get_full_name() or lesson.student.username,
                "subject_name": lesson.subject.name,
                "is_recurring": is_recurring
            }
        })

    # 2. Свободные слоты
    slots = TeacherAvailability.objects.filter(teacher=teacher, is_booked=False)
    for slot in slots:
        if slot.is_recurring:
            base_days_ahead = (slot.weekday - today.weekday() + 7) % 7
            for week in range(weeks):
                days_ahead = base_days_ahead + week * 7

                slot_date = today + timedelta(days=days_ahead)
                if slot_date < today or slot_date > end_date:
                    continue

                has_lesson = _has_lesson_overlap(
                    teacher=teacher,
                    lesson_date=slot_date,
                    lesson_time=slot.time,
                    duration_minutes=slot.duration_minutes or 30
                )
                if has_lesson:
                    continue

                start_dt = timezone.make_aware(datetime.combine(slot_date, slot.time), teacher_tz)
                end_dt = start_dt + timedelta(minutes=slot.duration_minutes or 30)
                is_past = end_dt < now_local

                events.append({
                    "id": f"slot-{slot.id}-{slot_date.strftime('%Y%m%d')}",
                    "title": "Свободно (рег.)",
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "color": "#34D399",
                    "textColor": "white",
                    "borderColor": "#059669",
                    "className": ["free-slot"] + (["past-slot"] if is_past else []),
                    "extendedProps": {
                        "type": "slot",
                        "slot_id": slot.id,
                        "is_recurring": True,
                        "slot_date": slot_date.isoformat(),
                        "is_past": is_past
                    }
                })
        else:
            if slot.date and today <= slot.date <= end_date:
                start_dt = timezone.make_aware(datetime.combine(slot.date, slot.time), teacher_tz)
                end_dt = start_dt + timedelta(minutes=slot.duration_minutes or 30)
                is_past = end_dt < now_local

                has_lesson = _has_lesson_overlap(
                    teacher=teacher,
                    lesson_date=slot.date,
                    lesson_time=slot.time,
                    duration_minutes=slot.duration_minutes or 30
                )
                if has_lesson:
                    continue

                events.append({
                    "id": f"slot-{slot.id}",
                    "title": "Свободно",
                    "start": start_dt.isoformat(),
                    "end": end_dt.isoformat(),
                    "color": "#34D399",
                    "textColor": "white",
                    "borderColor": "#059669",
                    "className": ["free-slot"] + (["past-slot"] if is_past else []),
                    "extendedProps": {
                        "type": "slot",
                        "slot_id": slot.id,
                        "is_recurring": False,
                        "is_past": is_past
                    }
                })

    return events
