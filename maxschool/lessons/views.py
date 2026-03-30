from django.shortcuts import render, redirect, get_object_or_404
from .forms import LessonBookingForm
from .models import LessonBooking
from accounts.models import Lesson
from django.contrib.auth.decorators import login_required

# 📌 1. Ученик бронирует урок
from django.shortcuts import render, redirect

from django.shortcuts import render, get_object_or_404
from accounts.models import CustomUser

from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db.models import Q
import copy
import json
import uuid
import logging
import jwt
# В начале файла lessons/views.py добавьте:
from django.contrib import messages
from datetime import datetime, date, timedelta
from .utils import SERIES_WEEKS, BOOKING_MIN_HOURS, build_calendar_events, get_teacher_tz

logger = logging.getLogger(__name__)

@login_required
def book_lesson_view(request, teacher_id):
    if getattr(request.user, 'role', None) != 'student':
        return redirect('dashboard')

    if request.user.balance <= 0:
        messages.error(request, 'Недостаточно уроков на балансе. Пополните баланс.')
        return redirect('student_dashboard')

    teacher = get_object_or_404(CustomUser, id=teacher_id, role='teacher', is_approved=True)

    if request.user.balance <= 0:
        messages.error(request, 'Недостаточно уроков на балансе. Пополните баланс.')
        return redirect('student_dashboard')

    if request.method == 'POST':
        form = LessonBookingForm(request.POST, student=request.user, teacher=teacher)
        if form.is_valid():
            try:
                lessons = form.save()
                # Закрепляем учителя за учеником после успешной записи
                request.user.teachers.add(teacher)
                if isinstance(lessons, list):
                    first = lessons[0]
                    messages.success(
                        request,
                        f"Вы успешно записались на {len(lessons)} занятий. Первое: {first.date} в {first.time.strftime('%H:%M')}"
                    )
                else:
                    messages.success(request, f"Вы успешно записались на урок на {lessons.date} в {lessons.time.strftime('%H:%M')}")
                return redirect('student_dashboard')
            except ValidationError as e:
                messages.error(request, "; ".join(e.messages))
            except Exception as e:
                messages.error(request, f"Ошибка при создании урока: {str(e)}")
    else:
        form = LessonBookingForm(student=request.user, teacher=teacher)

    return render(request, 'lessons/book_lesson.html', {
        'form': form,
        'teacher': teacher
    })



# 📌 2. Преподаватель видит все заявки от учеников
@login_required
def booking_requests_view(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')

    bookings = LessonBooking.objects.filter(teacher=request.user, is_confirmed=False)
    return render(request, 'lessons/teacher_bookings.html', {'bookings': bookings})


# 📌 3. Преподаватель подтверждает заявку → создаётся урок
from django.shortcuts import get_object_or_404, redirect, render
from lessons.models import LessonBooking, TeacherAvailability
from accounts.models import Lesson  # 👈 так правильно, т.к. Lesson в другом приложении
 # убедись, что импорт верный

@login_required
def confirm_booking_view(request, booking_id):
    booking = get_object_or_404(LessonBooking, id=booking_id, teacher=request.user)

    if booking.student.balance <= 0:
        messages.error(request, "У ученика недостаточно уроков на балансе.")
        return redirect('teacher_bookings')

    booking.is_confirmed = True
    booking.save()

    booking.student.teachers.add(booking.teacher)
    booking.student.save()

    # Отмечаем слот занятым, если он существует
    slot = TeacherAvailability.objects.filter(
        teacher=booking.teacher,
        date=booking.date,
        time=booking.time
    ).first()
    if slot:
        slot.is_booked = True
        slot.save()

    # Не дублируем урок, если он уже создан
    lesson = Lesson.objects.filter(
        teacher=booking.teacher,
        student=booking.student,
        subject=booking.subject,
        date=booking.date,
        time=booking.time
    ).first()

    if not lesson:
        Lesson.objects.create(
            teacher=booking.teacher,
            student=booking.student,
            subject=booking.subject,
            date=booking.date,
            time=booking.time,
            duration_minutes=30,
            is_recurring=booking.is_recurring
        )

    return redirect('teacher_bookings')

@login_required
def reschedule_lesson_view(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.user not in [lesson.teacher, lesson.student]:
        return redirect('dashboard')

    teacher = lesson.teacher
    teacher_tz = get_teacher_tz(teacher)
    today = timezone.now().astimezone(teacher_tz).date()

    available_one_time = TeacherAvailability.objects.filter(
        teacher=teacher,
        is_booked=False,
        is_recurring=False,
        date__gte=today
    ).order_by('date', 'time')

    available_recurring = TeacherAvailability.objects.filter(
        teacher=teacher,
        is_booked=False,
        is_recurring=True
    ).order_by('weekday', 'time')

    if request.method == 'POST':
        reschedule_type = request.POST.get('reschedule_type', 'single')
        slot_id = request.POST.get('slot_id')

        if not slot_id:
            messages.error(request, "Выберите свободный слот для переноса.")
            return redirect('reschedule_lesson', lesson_id=lesson.id)

        slot = get_object_or_404(TeacherAvailability, id=slot_id, teacher=teacher, is_booked=False)

        if reschedule_type == 'series':
            if not lesson.is_recurring:
                messages.error(request, "Этот урок не является регулярным.")
                return redirect('reschedule_lesson', lesson_id=lesson.id)
            if not slot.is_recurring:
                messages.error(request, "Для переноса серии выберите регулярный слот.")
                return redirect('reschedule_lesson', lesson_id=lesson.id)

            # Разрешаем перенос серии только на тот же день недели
            lesson_weekday = lesson.date.weekday()
            if slot.weekday is not None and slot.weekday != lesson_weekday:
                messages.error(request, "Для серии выберите слот в тот же день недели.")
                return redirect('reschedule_lesson', lesson_id=lesson.id)

            future_lessons = Lesson.objects.filter(
                teacher=teacher,
                student=lesson.student,
                subject=lesson.subject,
                is_recurring=True,
                date__gte=lesson.date
            )
            updated = 0
            for l in future_lessons:
                if l.date.weekday() == lesson_weekday:
                    l.time = slot.time
                    l.save()
                    updated += 1

            messages.success(request, f"Перенос серии выполнен. Обновлено уроков: {updated}.")
            return redirect('teacher_dashboard' if request.user == teacher else 'student_dashboard')

        # Разовый перенос
        if slot.is_recurring or slot.date is None:
            messages.error(request, "Для разового переноса выберите разовый слот с датой.")
            return redirect('reschedule_lesson', lesson_id=lesson.id)

        # Освобождаем старый разовый слот (если был)
        old_slot = TeacherAvailability.objects.filter(
            teacher=teacher,
            is_recurring=False,
            date=lesson.date,
            time=lesson.time
        ).first()
        if old_slot:
            old_slot.is_booked = False
            old_slot.save()

        lesson.date = slot.date
        lesson.time = slot.time
        lesson.save()

        slot.is_booked = True
        slot.save()

        messages.success(request, "Урок перенесён на выбранный слот.")
        return redirect('teacher_dashboard' if request.user == teacher else 'student_dashboard')

    return render(request, 'lessons/reschedule_lesson.html', {
        'lesson': lesson,
        'available_one_time': available_one_time,
        'available_recurring': available_recurring,
    })

@login_required
def add_availability_view(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')

    if request.method == 'POST':
        slot_type = request.POST.get('slot_type', 'once')  # 'once' или 'recurring'
        time = request.POST.get('time')
        duration = int(request.POST.get('duration', 30))

        if slot_type == 'recurring':
            # Регулярный слот
            weekday = request.POST.get('weekday')
            if weekday is not None:
                existing = TeacherAvailability.objects.filter(
                    teacher=request.user,
                    date=None,
                    time=time,
                    weekday=int(weekday),
                    is_recurring=True
                ).exists()
                if existing:
                    messages.warning(request, "Такой регулярный слот уже существует.")
                else:
                    TeacherAvailability.objects.create(
                        teacher=request.user,
                        date=None,  # у регулярных слотов нет конкретной даты
                        time=time,
                        duration_minutes=duration,
                        is_recurring=True,
                        weekday=int(weekday),
                        is_booked=False
                    )
                    messages.success(request, "Регулярный слот успешно добавлен!")
        else:
            # Разовый слот
            slot_date = request.POST.get('date')
            if slot_date:
                existing = TeacherAvailability.objects.filter(
                    teacher=request.user,
                    date=slot_date,
                    time=time,
                    weekday=None,
                    is_recurring=False
                ).exists()
                if existing:
                    messages.warning(request, "Такой разовый слот уже существует.")
                else:
                    TeacherAvailability.objects.create(
                        teacher=request.user,
                        date=slot_date,
                        time=time,
                        duration_minutes=duration,
                        is_recurring=False,
                        weekday=None,  # у разовых слотов нет дня недели
                        is_booked=False
                    )
                    messages.success(request, "Разовый слот успешно добавлен!")

        return redirect('teacher_availability')

    teacher_tz = get_teacher_tz(request.user)
    context = {
        "today": timezone.now().astimezone(teacher_tz).date(),
        "weekdays": [
            (0, "Понедельник"),
            (1, "Вторник"),
            (2, "Среда"),
            (3, "Четверг"),
            (4, "Пятница"),
            (5, "Суббота"),
            (6, "Воскресенье"),
        ]
    }
    return render(request, 'lessons/add_availability.html', context)

@login_required
def teacher_availability_view(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')

    teacher_tz = get_teacher_tz(request.user)
    now_local = timezone.now().astimezone(teacher_tz)
    today_local = now_local.date()
    now_time = now_local.time().replace(second=0, microsecond=0)

    slots = (
        TeacherAvailability.objects
        .filter(teacher=request.user)
        .filter(
            Q(is_recurring=True) |
            Q(date__gt=today_local) |
            Q(date=today_local, time__gte=now_time)
        )
        .order_by('date', 'time')
    )
    free_slots_count = slots.filter(is_booked=False).count()
    booked_slots_count = slots.filter(is_booked=True).count()
    one_time_count = slots.filter(is_recurring=False).count()
    recurring_count = slots.filter(is_recurring=True).count()
    total_minutes = sum((s.duration_minutes or 0) for s in slots)
    total_hours = round(total_minutes / 60, 1)
    return render(request, 'lessons/teacher_availability.html', {
        'slots': slots,
        'free_slots_count': free_slots_count,
        'booked_slots_count': booked_slots_count,
        'one_time_count': one_time_count,
        'recurring_count': recurring_count,
        'total_hours': total_hours,
    })

@login_required
def delete_availability_view(request, slot_id):
    slot = get_object_or_404(TeacherAvailability, id=slot_id, teacher=request.user)
    if request.method == 'POST':
        slot.delete()
    return redirect('teacher_availability')

#доска и связь

from datetime import datetime, timedelta


def _normalize_jaas_key_id(app_id, key_id):
    """Accept short tenant/key format and normalize it to <app_id>/<key>."""
    if not key_id:
        return ''

    key_id = key_id.strip()
    if key_id.startswith(f'{app_id}/'):
        return key_id

    tenant_id = app_id.removeprefix('vpaas-magic-cookie-')
    if key_id.startswith(f'{tenant_id}/'):
        return f'{app_id}/{key_id.split("/", 1)[1]}'

    # If only the key suffix is provided, prepend the app id.
    if '/' not in key_id:
        return f'{app_id}/{key_id}'

    return key_id


def _build_jaas_jwt(*, user, is_teacher):
    app_id = (settings.JAAAS_APP_ID or '').strip()
    key_id = _normalize_jaas_key_id(app_id, (settings.JAAAS_KEY_ID or '').strip())
    private_key = settings.JAAAS_PRIVATE_KEY or ''
    issuer = (settings.JAAAS_JWT_ISSUER or 'chat').strip()

    if not (app_id and key_id and private_key):
        return ''

    now_ts = int(timezone.now().timestamp())
    payload = {
        'aud': 'jitsi',
        'iss': issuer,
        'sub': app_id,
        'room': '*',
        'nbf': now_ts - 10,
        'exp': now_ts + 2 * 60 * 60,
        'context': {
            'user': {
                'name': user.get_full_name() or user.username,
                'email': user.email or '',
                'moderator': 'true' if is_teacher else 'false',
            },
            # JaaS expects this object in the JWT payload.
            'features': {
                'livestreaming': False,
                'recording': False,
                'transcription': False,
                'inbound-call': False,
                'outbound-call': False,
                'sip-inbound-call': False,
                'sip-outbound-call': False,
            },
        },
    }
    headers = {'kid': key_id, 'typ': 'JWT'}
    token = jwt.encode(payload, private_key, algorithm='RS256', headers=headers)
    return token.decode('utf-8') if isinstance(token, bytes) else token


@login_required
def lesson_session(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.user not in (lesson.teacher, lesson.student):
        return HttpResponse('Нет доступа', status=403)
    
    # Вычисляем, пора ли показывать ссылку
    teacher_tz = get_teacher_tz(lesson.teacher)
    start_datetime = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
    show_video = timezone.now().astimezone(teacher_tz) >= (start_datetime - timedelta(minutes=5))

    if not show_video:
        # return render(request, "lesson_not_started.html", {"lesson": lesson})
        return HttpResponse(f"Урок еще не начался. Начнется {lesson.date} в {lesson.time}")
    
    # Проверяем, является ли текущий пользователь учителем этого урока
    is_teacher = False
    if hasattr(lesson, 'teacher'):
        # Если урок связан с конкретным учителем
        is_teacher = (request.user == lesson.teacher)
    else:
        # Альтернативная проверка: является ли пользователь учителем в группе
        is_teacher = request.user.groups.filter(name='Teachers').exists()
    
    room_name = f"maxschool_lesson_{lesson.id}"
    jitsi_domain = 'meet.jit.si'
    jitsi_room = room_name
    jitsi_script_url = f'https://{jitsi_domain}/external_api.js'
    jitsi_external_url = f'https://{jitsi_domain}/{jitsi_room}'
    jitsi_jwt = ''

    app_id = (settings.JAAAS_APP_ID or '').strip()
    use_jaas = bool(app_id and settings.JAAAS_KEY_ID and settings.JAAAS_PRIVATE_KEY)
    if use_jaas:
        try:
            jitsi_domain = (settings.JAAAS_DOMAIN or '8x8.vc').strip()
            jitsi_room = f'{app_id}/{room_name}'
            jitsi_script_url = f'https://{jitsi_domain}/{app_id}/external_api.js'
            jitsi_external_url = f'https://{jitsi_domain}/{jitsi_room}'
            jitsi_jwt = _build_jaas_jwt(user=request.user, is_teacher=is_teacher)
            if not jitsi_jwt:
                raise ValueError('JaaS JWT is empty')
        except Exception as exc:
            logger.exception('JaaS setup failed, fallback to meet.jit.si: %s', exc)
            jitsi_domain = 'meet.jit.si'
            jitsi_room = room_name
            jitsi_script_url = f'https://{jitsi_domain}/external_api.js'
            jitsi_external_url = f'https://{jitsi_domain}/{jitsi_room}'
            jitsi_jwt = ''

    return render(request, "lessons/lesson_session.html", {
        "lesson": lesson,
        "lesson_id": lesson.id,  # ✅ добавляем для WebSocket
        "jitsi_room": jitsi_room,
        "jitsi_domain": jitsi_domain,
        "jitsi_script_url": jitsi_script_url,
        "jitsi_external_url": jitsi_external_url,
        "jitsi_jwt": jitsi_jwt,
        "user_name": request.user.get_full_name() or request.user.username,
        "is_teacher": is_teacher  # Передаем флаг в шаблон
    })


def _try_fix_cp1251_mojibake(value):
    if not isinstance(value, str):
        return value
    fixed = value
    # Two passes are enough for our historical data.
    for _ in range(2):
        try:
            candidate = fixed.encode('cp1251').decode('utf-8')
        except (UnicodeEncodeError, UnicodeDecodeError):
            break
        if candidate == fixed:
            break
        fixed = candidate
    return fixed


def _normalize_board_state_names(state):
    if not isinstance(state, dict):
        return state, False
    boards = state.get('boards')
    if not isinstance(boards, list):
        return state, False

    changed = False
    for board in boards:
        if not isinstance(board, dict):
            continue
        name = board.get('name')
        if not isinstance(name, str):
            continue
        fixed_name = _try_fix_cp1251_mojibake(name).strip() or '\u0414\u043e\u0441\u043a\u0430'
        if fixed_name != name:
            board['name'] = fixed_name
            changed = True
    return state, changed


BOARD_STATE_MAX_REQUEST_BYTES = int(getattr(settings, "BOARD_STATE_MAX_REQUEST_BYTES", 6_000_000))
BOARD_STATE_MAX_SERIALIZED_BYTES = int(getattr(settings, "BOARD_STATE_MAX_SERIALIZED_BYTES", 6_000_000))
BOARD_STATE_MAX_BOARDS = int(getattr(settings, "BOARD_STATE_MAX_BOARDS", 40))
BOARD_STATE_MAX_IMAGE_DATA_URL_LENGTH = int(getattr(settings, "BOARD_STATE_MAX_IMAGE_DATA_URL_LENGTH", 1_500_000))


def _json_size_bytes(value):
    try:
        return len(json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
    except (TypeError, ValueError):
        return BOARD_STATE_MAX_SERIALIZED_BYTES + 1


def _validate_board_state_payload(state):
    boards = state.get('boards')
    if boards is None:
        boards = []
    if not isinstance(boards, list):
        return 'Некорректный формат досок', 400
    if len(boards) > BOARD_STATE_MAX_BOARDS:
        return 'Слишком много досок в состоянии', 413

    for board in boards:
        if not isinstance(board, dict):
            return 'Некорректный формат доски', 400
        images = board.get('images')
        if images is None:
            continue
        if not isinstance(images, list):
            return 'Некорректный формат изображений', 400
        for image in images:
            if not isinstance(image, dict):
                return 'Некорректный формат изображения', 400
            src = image.get('src')
            if src is None:
                continue
            if not isinstance(src, str):
                return 'Некорректный формат источника изображения', 400
            if len(src) > BOARD_STATE_MAX_IMAGE_DATA_URL_LENGTH:
                return 'Изображение слишком большое для сохранения', 413

    if _json_size_bytes(state) > BOARD_STATE_MAX_SERIALIZED_BYTES:
        return 'Состояние доски слишком большое', 413

    return None, None


@login_required
@require_http_methods(["GET", "POST"])
def lesson_board_state(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    if request.user not in (lesson.teacher, lesson.student):
        return JsonResponse({'error': 'Нет доступа'}, status=403)

    if request.method == 'GET':
        state = copy.deepcopy(lesson.board_state or {})
        state, changed = _normalize_board_state_names(state)
        if changed:
            lesson.board_state = state
            lesson.board_state_updated_at = timezone.now()
            lesson.save(update_fields=['board_state', 'board_state_updated_at'])
        return JsonResponse({'state': state}, status=200)

    raw_body = request.body or b''
    if len(raw_body) > BOARD_STATE_MAX_REQUEST_BYTES:
        return JsonResponse({'error': 'Состояние доски слишком большое'}, status=413)

    try:
        payload = json.loads(raw_body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return JsonResponse({'error': 'Некорректные данные'}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({'error': 'Некорректный формат запроса'}, status=400)

    state = payload.get('state')
    if not isinstance(state, dict):
        return JsonResponse({'error': 'Некорректный формат состояния'}, status=400)

    state, _ = _normalize_board_state_names(state)
    validation_error, validation_status = _validate_board_state_payload(state)
    if validation_error:
        return JsonResponse({'error': validation_error}, status=validation_status)

    lesson.board_state = state
    lesson.board_state_updated_at = timezone.now()
    lesson.save(update_fields=['board_state', 'board_state_updated_at'])
    return JsonResponse({'success': True}, status=200)
from .models import TeacherAvailability


@login_required
def select_teacher(request):
    if getattr(request.user, 'role', None) != 'student':
        return redirect('dashboard')

    # Основной источник — преподаватели, закрепленные за учеником в админке.
    teachers = (
        request.user.teachers
        .filter(role='teacher', is_approved=True)
        .select_related('desired_subject')
        .prefetch_related('subjects_taught')
        .order_by('first_name', 'last_name', 'username')
        .distinct()
    )

    # Fallback для старых данных: преподаватели из подтвержденных уроков.
    if not teachers.exists():
        teachers = (
            CustomUser.objects
            .filter(
                role='teacher',
                lessons_to_teach__student=request.user,
                lessons_to_teach__is_confirmed=True,
                is_approved=True,
            )
            .select_related('desired_subject')
            .prefetch_related('subjects_taught')
            .order_by('first_name', 'last_name', 'username')
            .distinct()
        )

    return render(request, "lessons/select_teacher.html", {"teachers": teachers})

#     teacher = get_object_or_404(CustomUser, id=teacher_id, role='teacher')
    
#     # Показываем только свободные слоты
#     slots = TeacherAvailability.objects.filter(
#         teacher=teacher,
#         is_booked=False
#     ).order_by('date', 'time')
    
#     return render(request, "lessons/available_slots_in_cabinet.html", {
#         "teacher": teacher,
#         "slots": slots
#     })

from django.shortcuts import redirect

@login_required
def book_lesson(request, slot_id):
    slot = get_object_or_404(TeacherAvailability, id=slot_id)

    if getattr(request.user, 'role', None) != 'student':
        return redirect('dashboard')

    if request.user.balance <= 0:
        messages.error(request, 'Недостаточно уроков на балансе. Пополните баланс.')
        return redirect('student_dashboard')

    # Запрет записи менее чем за N часов (только для ученика)
    if slot.date:
        teacher_tz = get_teacher_tz(slot.teacher)
        now = timezone.now().astimezone(teacher_tz)
        min_dt = now + timedelta(hours=BOOKING_MIN_HOURS)
        slot_dt = timezone.make_aware(datetime.combine(slot.date, slot.time), teacher_tz)
        if slot_dt <= min_dt:
            messages.error(request, f'Нельзя записаться менее чем за {BOOKING_MIN_HOURS} часа(ов) до урока.')
            return redirect('student_dashboard')

    # проверяем, что ученик может записаться к этому учителю
    if slot.teacher not in request.user.teachers.all():
        return redirect("schedule_lesson")

    subjects_qs = slot.teacher.subjects_taught.all()
    if not subjects_qs.exists() and getattr(slot.teacher, 'desired_subject', None):
        subjects_qs = subjects_qs.model.objects.filter(id=slot.teacher.desired_subject_id)

    if request.method != 'POST':
        return render(request, 'lessons/book_lesson_in_cabinet.html', {
            'slot': slot,
            'teacher': slot.teacher,
            'subjects': subjects_qs,
        })

    subject_id = request.POST.get('subject')
    subject = None
    if subject_id:
        subject = subjects_qs.filter(id=subject_id).first()

    if not subject:
        messages.error(request, "Выберите предмет")
        return render(request, 'lessons/book_lesson_in_cabinet.html', {
            'slot': slot,
            'teacher': slot.teacher,
            'subjects': subjects_qs,
        })

    # создаем урок
    lesson = Lesson.objects.create(
        student=request.user,
        teacher=slot.teacher,
        subject=subject,
        date=slot.date,
        time=slot.time,
        duration_minutes=slot.duration_minutes or 30,
        is_recurring=False
    )

    # история бронирования
    LessonBooking.objects.create(
        student=request.user,
        teacher=slot.teacher,
        subject=subject,
        date=slot.date,
        time=slot.time,
        is_confirmed=True,
        is_recurring=False
    )

    # отмечаем слот как занятый
    slot.is_booked = True
    slot.save()

    # закрепляем учителя, если ещё не закреплён
    request.user.teachers.add(slot.teacher)

    return redirect("student_dashboard")

@login_required
def my_students(request):
    if request.user.role != 'teacher':
        return render(request, "not_allowed.html")  # или редирект
    
    # Находим всех учеников, у которых есть уроки с этим учителем
    lessons = Lesson.objects.filter(teacher=request.user).select_related('student').order_by('student__username')

    # Убираем дубликаты (один ученик может быть в нескольких уроках)
    students = {lesson.student for lesson in lessons}

    return render(request, "lessons/my_students.html", {"students": students})



import json
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime

from accounts.models import Lesson, CustomUser, Subject, StudentNotification

# Создание свободного слота

@login_required
def create_free_slot(request):
    """Создает свободные слоты - разовые или регулярные"""
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    if getattr(request.user, 'role', None) != "teacher":
        return JsonResponse({"success": False, "error": "Доступ запрещён"}, status=403)
    
    try:
        data = json.loads(request.body)
        slots_data = data.get("slots")
        slot_type = data.get("slot_type", "once")  # "once" или "recurring"
        weekday = data.get("weekday")  # 0-6 для регулярных слотов
        duration = data.get("duration", 60)  # продолжительность в минутах
        
        if not slots_data:
            return JsonResponse({"success": False, "error": "Нет данных о слотах"})

        created_slots = []
        
        teacher_tz = get_teacher_tz(request.user)

        for slot in slots_data:
            start_str = slot.get("start")
            end_str = slot.get("end")

            if not start_str or not end_str:
                continue

            try:
                # Преобразуем строки в datetime
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except Exception:
                # Альтернативный способ парсинга
                start = parse_datetime(start_str)
                end = parse_datetime(end_str)

            if not start or not end:
                continue

            # Нормализуем к часовому поясу учителя (МСК)
            if timezone.is_naive(start):
                start = timezone.make_aware(start, teacher_tz)
            else:
                start = start.astimezone(teacher_tz)
            if timezone.is_naive(end):
                end = timezone.make_aware(end, teacher_tz)
            else:
                end = end.astimezone(teacher_tz)

            # Для разовых слотов
            if slot_type == "once":
                exists = TeacherAvailability.objects.filter(
                    teacher=request.user,
                    date=start.date(),
                    time=start.time(),
                    weekday=None,
                    is_recurring=False
                ).exists()
                if not exists:
                    new_slot = TeacherAvailability.objects.create(
                        teacher=request.user,
                        date=start.date(),
                        time=start.time(),
                        duration_minutes=duration or int((end - start).seconds / 60),
                        is_booked=False,
                        is_recurring=False
                    )
                    
                    created_slots.append({
                        "id": new_slot.id,
                        "start": start.isoformat(),
                        "end": end.isoformat(),
                        "type": "once"
                    })
                
            # Для регулярных слотов
            elif slot_type == "recurring":
                selected_weekday = int(weekday) if weekday is not None else start.weekday()
                exists = TeacherAvailability.objects.filter(
                    teacher=request.user,
                    date=None,
                    time=start.time(),
                    weekday=selected_weekday,
                    is_recurring=True
                ).exists()
                if not exists:
                    # Создаем регулярный слот (без конкретной даты)
                    new_slot = TeacherAvailability.objects.create(
                        teacher=request.user,
                        date=None,  # У регулярных слотов нет конкретной даты
                        time=start.time(),
                        duration_minutes=duration or int((end - start).seconds / 60),
                        is_booked=False,
                        is_recurring=True,
                        weekday=selected_weekday
                    )
                    
                    created_slots.append({
                        "id": new_slot.id,
                        "start": start.time().isoformat(),  # Только время для регулярных
                        "end": end.time().isoformat(),
                        "weekday": selected_weekday,
                        "type": "recurring"
                    })

        if not created_slots:
            return JsonResponse({"success": False, "error": "Не удалось создать слоты"})

        return JsonResponse({
            "success": True, 
            "slots": created_slots,
            "slot_type": slot_type,
            "count": len(created_slots)
        })

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({"success": False, "error": str(e)}, status=500)
@login_required
def assign_student_to_slot(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    if getattr(request.user, 'role', None) != "teacher":
        return JsonResponse({"success": False, "error": "Доступ запрещён"}, status=403)

    try:
        data = json.loads(request.body)
        slot_id = data.get("slot_id")
        student_id = data.get("student_id")
        subject_id = data.get("subject_id")
        is_recurring_requested = bool(data.get("is_recurring", False))
        requested_count = data.get("recurrence_count")
        try:
            recurrence_count = int(requested_count) if requested_count is not None else SERIES_WEEKS
        except (TypeError, ValueError):
            recurrence_count = SERIES_WEEKS
        if recurrence_count <= 0:
            recurrence_count = SERIES_WEEKS
        if recurrence_count > SERIES_WEEKS:
            recurrence_count = SERIES_WEEKS
        slot_date_str = data.get("slot_date")

        slot = get_object_or_404(TeacherAvailability, id=slot_id)
        student = get_object_or_404(CustomUser, id=student_id, role="student")

        if not subject_id:
            return JsonResponse({"success": False, "error": "Выберите предмет"}, status=400)

        if not Lesson.objects.filter(teacher=slot.teacher, student=student, subject_id=subject_id).exists():
            return JsonResponse({"success": False, "error": "Этот предмет недоступен для данного ученика"}, status=400)

        subject = Subject.objects.filter(id=subject_id).first()
        if not subject:
            return JsonResponse({"success": False, "error": "Предмет не найден"}, status=400)

        if student.balance <= 0:
            return JsonResponse({"success": False, "error": "Недостаточно уроков на балансе"}, status=400)

        # Проверка: только учитель слота может назначить ученика
        if request.user != slot.teacher:
            return JsonResponse({"success": False, "error": "Нет доступа"}, status=403)

        if slot.is_booked:
            return JsonResponse({"success": False, "error": "Слот уже занят"})

        lesson_id = None
        teacher_tz = get_teacher_tz(slot.teacher)

        # Создаем урок(и)
        if slot.is_recurring and is_recurring_requested:
            weekday_names_english = {
                0: "Monday",
                1: "Tuesday",
                2: "Wednesday",
                3: "Thursday",
                4: "Friday",
                5: "Saturday",
                6: "Sunday"
            }
            english_weekday = weekday_names_english.get(slot.weekday, "Monday")

            today = timezone.now().astimezone(teacher_tz).date()
            days_ahead = (slot.weekday - today.weekday() + 7) % 7
            if days_ahead == 0:
                days_ahead = 7
            start_date = today + timedelta(days=days_ahead)
            end_date = start_date + timedelta(weeks=recurrence_count)

            lessons_created = []
            for week in range(recurrence_count):
                lesson_date = start_date + timedelta(weeks=week)

                lesson = Lesson.objects.create(
                    subject=subject,
                    teacher=slot.teacher,
                    student=student,
                    date=lesson_date,
                    time=slot.time,
                    duration_minutes=slot.duration_minutes or 30,
                    is_recurring=True,
                    days_of_week=english_weekday,
                    end_date=end_date
                )
                lessons_created.append(lesson)

            lesson_id = lessons_created[0].id if lessons_created else None

            # Бронируем регулярный слот
            slot.is_booked = True
            slot.save()

            # Запись в LessonBooking (единая история)
            LessonBooking.objects.create(
                student=student,
                teacher=slot.teacher,
                subject=subject,
                date=start_date,
                time=slot.time,
                is_confirmed=True,
                is_recurring=True
            )

            # Закрепляем учителя за учеником
            student.teachers.add(slot.teacher)

        else:
            # Одиночный урок даже для регулярного слота
            if slot_date_str:
                try:
                    single_date = date.fromisoformat(slot_date_str)
                except ValueError:
                    return JsonResponse({"success": False, "error": "Некорректная дата слота"}, status=400)
            else:
                single_date = slot.date or timezone.now().astimezone(teacher_tz).date()

            # Не допускаем пересечения
            if Lesson.objects.filter(teacher=slot.teacher, date=single_date, time=slot.time).exists():
                return JsonResponse({"success": False, "error": "На это время уже есть урок"}, status=400)

            lesson = Lesson.objects.create(
                subject=subject,
                teacher=slot.teacher,
                student=student,
                date=single_date,
                time=slot.time,
                duration_minutes=slot.duration_minutes or 30,
                is_recurring=False
            )

            # Для разового слота — блокируем, для регулярного оставляем доступным
            if not slot.is_recurring:
                slot.is_booked = True
                slot.save()

            lesson_id = lesson.id

            LessonBooking.objects.create(
                student=student,
                teacher=slot.teacher,
                subject=subject,
                date=single_date,
                time=slot.time,
                is_confirmed=True,
                is_recurring=False
            )

            # Закрепляем учителя за учеником
            student.teachers.add(slot.teacher)

        return JsonResponse({
            "success": True,
            "lesson_id": lesson_id,
            "student_name": student.get_full_name() or student.username,
            "is_recurring": slot.is_recurring
        })

    except Exception as e:
        print(f"Ошибка при назначении ученика: {str(e)}")
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@login_required
def delete_free_slot(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    if getattr(request.user, 'role', None) != "teacher":
        return JsonResponse({"success": False, "error": "Доступ запрещён"}, status=403)

    try:
        data = json.loads(request.body)
        slot_id = data.get("slot_id")

        slot = get_object_or_404(TeacherAvailability, id=slot_id)

        # Только владелец слота может удалять
        if request.user != slot.teacher:
            return JsonResponse({"success": False, "error": "Нет доступа"}, status=403)

        # Если слот был забронирован — удаляем уроки и записи бронирований
        if slot.is_booked:
            if slot.date:
                lessons_to_delete = Lesson.objects.filter(
                    teacher=slot.teacher,
                    date=slot.date,
                    time=slot.time
                )
                affected_students = list(lessons_to_delete.values_list('student_id', flat=True).distinct())
                lessons_to_delete.delete()
                LessonBooking.objects.filter(
                    teacher=slot.teacher,
                    date=slot.date,
                    time=slot.time
                ).delete()
                for sid in affected_students:
                    StudentNotification.objects.create(
                        student_id=sid,
                        message=f"Преподаватель отменил урок на {slot.date} {slot.time.strftime('%H:%M')}"
                    )
                for student_id in affected_students:
                    if not Lesson.objects.filter(teacher=slot.teacher, student_id=student_id).exists():
                        student = CustomUser.objects.filter(id=student_id).first()
                        if student:
                            student.teachers.remove(slot.teacher)
            else:
                weekday_map = {
                    0: "Monday",
                    1: "Tuesday",
                    2: "Wednesday",
                    3: "Thursday",
                    4: "Friday",
                    5: "Saturday",
                    6: "Sunday",
                }
                weekday_name = weekday_map.get(slot.weekday)
                affected_students = []
                if weekday_name:
                    lessons_to_delete = Lesson.objects.filter(
                        teacher=slot.teacher,
                        time=slot.time,
                        is_recurring=True,
                        days_of_week=weekday_name,
                    )
                    affected_students = list(lessons_to_delete.values_list('student_id', flat=True).distinct())
                    lessons_to_delete.delete()
                    for sid in affected_students:
                        StudentNotification.objects.create(
                            student_id=sid,
                            message=f"Преподаватель отменил серию уроков на {weekday_name} {slot.time.strftime('%H:%M')}"
                        )
                LessonBooking.objects.filter(
                    teacher=slot.teacher,
                    time=slot.time,
                    is_recurring=True
                ).delete()
                for student_id in affected_students:
                    if not Lesson.objects.filter(teacher=slot.teacher, student_id=student_id).exists():
                        student = CustomUser.objects.filter(id=student_id).first()
                        if student:
                            student.teachers.remove(slot.teacher)

        slot.delete()
        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

@login_required
def get_students(request):
    """Возвращает JSON учеников для календаря - ТЕХ ЖЕ, что и на странице 'Мои ученики'"""
    if request.user.role != "teacher":
        return JsonResponse({"success": False, "error": "Доступ запрещён"}, status=403)
    
    try:
        # ВАЖНО: Используем ТОЧНО ТАКУЮ ЖЕ логику как в my_students!
        # 1. Находим все уроки с этим учителем
        lessons = Lesson.objects.filter(teacher=request.user).select_related('student')
        
        # 2. Получаем уникальных учеников из этих уроков
        student_ids = lessons.values_list('student_id', flat=True).distinct()
        
        # 3. Получаем объекты учеников
        students = CustomUser.objects.filter(id__in=student_ids, role='student')
        
        print(f"DEBUG get_students: Найдено {students.count()} учеников")
        
        # 4. Формируем данные для JSON
        students_data = []
        for student in students:
            # Подсчитываем количество уроков у каждого ученика
            subjects = lessons.filter(student=student).values('subject_id', 'subject__name').distinct()
            subjects_list = [{'id': s['subject_id'], 'name': s['subject__name']} for s in subjects]
            lesson_count = lessons.filter(student=student).count()

            students_data.append({
                "id": student.id,
                "name": (student.first_name + " " + student.last_name).strip() or student.username,
                "username": student.username,
                "email": student.email,
                "lesson_count": lesson_count,
                "profile_url": f"/student/profile/{student.id}/",  # URL профиля ученика
                "subjects": subjects_list,
            })
        
        # Сортируем по количеству уроков (самые активные вверху)
        students_data.sort(key=lambda x: x['lesson_count'], reverse=True)
        
        return JsonResponse({
            "success": True,
            "students": students_data,
            "total": len(students_data),
            "debug_info": {
                "teacher": request.user.username,
                "total_lessons": lessons.count(),
                "unique_students": students.count()
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"ERROR в get_students: {str(e)}")
        
        # Fallback: возвращаем пустой список, но с успехом
        return JsonResponse({
            "success": True,
            "students": [],
            "total": 0,
            "error": str(e),
            "note": "Вернулся пустой список из-за ошибки"
        })
@login_required
def get_calendar_events(request):
    if request.user.role != "teacher":
        return JsonResponse([], safe=False)

    events = build_calendar_events(request.user, weeks=SERIES_WEEKS)
    return JsonResponse(events, safe=False)


@login_required
def delete_lesson(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    if getattr(request.user, 'role', None) != "teacher":
        return JsonResponse({"success": False, "error": "Доступ запрещён"}, status=403)

    try:
        data = json.loads(request.body)
        lesson_id = data.get("lesson_id")
        delete_type = data.get("delete_type", "single")

        lesson = get_object_or_404(Lesson, id=lesson_id, teacher=request.user)
        teacher = lesson.teacher
        student = lesson.student
        subject = lesson.subject

        if delete_type == "all" and lesson.is_recurring and lesson.days_of_week:
            lessons_qs = Lesson.objects.filter(
                teacher=teacher,
                student=student,
                subject=subject,
                time=lesson.time,
                is_recurring=True,
                days_of_week=lesson.days_of_week,
            )
            lessons_qs.delete()
            LessonBooking.objects.filter(
                teacher=teacher,
                student=student,
                subject=subject,
                time=lesson.time,
                is_recurring=True
            ).delete()
            StudentNotification.objects.create(
                student=student,
                message=f"Преподаватель отменил серию уроков по предмету {subject.name}."
            )
            return JsonResponse({"success": True})

        # Удаление одного урока
        date_val = lesson.date
        time_val = lesson.time
        weekday = date_val.weekday()
        lesson.delete()

        # Освобождаем слот (создаем разовый, если нет регулярного)
        has_recurring = TeacherAvailability.objects.filter(
            teacher=teacher,
            is_recurring=True,
            weekday=weekday,
            time=time_val
        ).exists()
        if not has_recurring:
            slot, created = TeacherAvailability.objects.get_or_create(
                teacher=teacher,
                date=date_val,
                time=time_val,
                defaults={'duration_minutes': 30, 'is_booked': False, 'is_recurring': False}
            )
            if not created:
                slot.is_booked = False
                slot.save(update_fields=['is_booked'])

        StudentNotification.objects.create(
            student=student,
            message=f"Преподаватель отменил урок {subject.name} на {date_val} {time_val.strftime('%H:%M')}"
        )

        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)


@login_required
def student_profile_view(request, student_id):
    if getattr(request.user, 'role', None) != "teacher":
        return HttpResponse('Нет доступа', status=403)

    student = get_object_or_404(CustomUser, id=student_id, role='student')
    lessons = Lesson.objects.filter(teacher=request.user, student=student).order_by('-date', '-time')

    return render(request, 'accounts/student_profile.html', {
        'student': student,
        'lessons': lessons
    })

