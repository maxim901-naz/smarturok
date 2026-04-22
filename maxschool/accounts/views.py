from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from django.core.cache import cache
from django.conf import settings
from django.urls import reverse
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from email.utils import make_msgid
from datetime import date
import json
import random
from datetime import datetime, date, timedelta
from zoneinfo import ZoneInfo
import logging
from .forms import (
    BalanceTopUpRequestForm,
    CustomUserCreationForm,
    StudentVacationRequestForm,
    TrialLessonForm,
    TeacherApplicationForm
)

from .models import (
    TeacherNotification,
    StudentNotification,
    BalanceTransaction,
    TeacherFinanceEntry,
    CustomUser,
    Lesson,
    TrialRequest,
    Subject,
    Vacancy
)
from .finance import get_teacher_payout_amount_for_lesson
from lessons.utils import SERIES_WEEKS

DEFAULT_APP_TZ_NAME = getattr(settings, 'TIME_ZONE', None) or 'UTC'
try:
    DEFAULT_APP_TZ = ZoneInfo(DEFAULT_APP_TZ_NAME)
except Exception:
    DEFAULT_APP_TZ = ZoneInfo('UTC')
TEACHER_TZ_NAME = 'Europe/Moscow'
try:
    TEACHER_TZ = ZoneInfo(TEACHER_TZ_NAME)
except Exception:
    TEACHER_TZ = DEFAULT_APP_TZ
STUDENT_FALLBACK_TZ_NAME = TEACHER_TZ_NAME
REGISTER_RATE_LIMIT = 12
REGISTER_RATE_WINDOW_SECONDS = 60 * 60  # 1 hour
LOGIN_IP_RATE_LIMIT = 20
LOGIN_USER_RATE_LIMIT = 10
LOGIN_RATE_WINDOW_SECONDS = 15 * 60  # 15 minutes
RESEND_VERIFY_RATE_LIMIT = 8
RESEND_VERIFY_RATE_WINDOW_SECONDS = 15 * 60  # 15 minutes
REGISTER_CAPTCHA_ANSWER_KEY = 'register_captcha_answer'
REGISTER_CAPTCHA_LABEL_KEY = 'register_captcha_label'
logger = logging.getLogger(__name__)


def get_user_tz(user):
    if getattr(user, 'role', None) == 'teacher':
        return TEACHER_TZ
    tz_name = getattr(user, 'time_zone', None) or STUDENT_FALLBACK_TZ_NAME
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return TEACHER_TZ


def _client_ip(request):
    forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if forwarded_for:
        return forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR', 'unknown')


def _rate_limit_key(scope, value):
    return f'auth:{scope}:{value}'


def _rate_limit_exceeded(key, limit):
    return int(cache.get(key, 0) or 0) >= int(limit)


def _rate_limit_hit(key, window_seconds):
    if cache.add(key, 1, timeout=window_seconds):
        return 1
    try:
        return cache.incr(key)
    except ValueError:
        cache.set(key, 1, timeout=window_seconds)
        return 1


def _rate_limit_reset(key):
    cache.delete(key)


def _refresh_register_captcha(request):
    a = random.randint(1, 9)
    b = random.randint(1, 9)
    request.session[REGISTER_CAPTCHA_ANSWER_KEY] = a + b
    request.session[REGISTER_CAPTCHA_LABEL_KEY] = f'Сколько будет {a} + {b}?'


def _apply_register_captcha_label(form, request):
    if 'captcha_answer' not in form.fields:
        return
    label = request.session.get(REGISTER_CAPTCHA_LABEL_KEY)
    if not label:
        _refresh_register_captcha(request)
        label = request.session.get(REGISTER_CAPTCHA_LABEL_KEY, 'Сколько будет 1 + 1?')
    form.fields['captcha_answer'].label = label


def _send_email_verification(request, user):
    uidb64 = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verify_url = request.build_absolute_uri(
        reverse('verify_email', kwargs={'uidb64': uidb64, 'token': token})
    )
    subject = 'Подтверждение email в SmartUrok'
    body = (
        f'Здравствуйте, {user.username}!\n\n'
        'Подтвердите ваш email, перейдя по ссылке:\n'
        f'{verify_url}\n\n'
        'Если вы не регистрировались, просто игнорируйте это письмо.'
    )
    message = EmailMessage(
        subject=subject,
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email],
        headers={'Message-ID': make_msgid(domain='localhost')},
    )
    try:
        message.send(fail_silently=False)
        return True
    except Exception:
        logger.exception('Failed to send verification email to user_id=%s email=%s', user.pk, user.email)
        return False

# Регистрация
def register_view(request):
    ip = _client_ip(request)
    register_key = _rate_limit_key('register:ip', ip)
    default_time_zone = STUDENT_FALLBACK_TZ_NAME

    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        _apply_register_captcha_label(form, request)

        requested_role = (request.POST.get('role') or '').strip().lower()
        if requested_role and requested_role != 'student':
            form.add_error(
                None,
                'Самостоятельная регистрация преподавателя отключена. '
                'Для преподавателя нужно отправить заявку на вакансию.'
            )
            _refresh_register_captcha(request)
            _apply_register_captcha_label(form, request)
            return render(
                request,
                'accounts/register.html',
                {'form': form, 'default_time_zone': default_time_zone},
            )

        if _rate_limit_exceeded(register_key, REGISTER_RATE_LIMIT):
            form.add_error(None, 'Слишком много попыток регистрации. Повторите позже.')
            return render(request, 'accounts/register.html', {'form': form, 'default_time_zone': default_time_zone})

        expected_captcha = request.session.get(REGISTER_CAPTCHA_ANSWER_KEY)
        raw_captcha = (request.POST.get('captcha_answer') or '').strip()
        captcha_ok = False
        if expected_captcha is not None:
            try:
                captcha_ok = int(raw_captcha) == int(expected_captcha)
            except (TypeError, ValueError):
                captcha_ok = False

        form_valid = form.is_valid()
        if form_valid and captcha_ok:
            user = form.save(commit=False)
            browser_tz = (request.POST.get('time_zone') or '').strip()
            if browser_tz:
                try:
                    ZoneInfo(browser_tz)
                    user.time_zone = browser_tz
                except Exception:
                    user.time_zone = default_time_zone
            else:
                user.time_zone = default_time_zone
            user.is_approved = True
            user.is_email_verified = False
            user.save()
            email_sent = _send_email_verification(request, user)
            _rate_limit_reset(register_key)
            request.session.pop(REGISTER_CAPTCHA_ANSWER_KEY, None)
            request.session.pop(REGISTER_CAPTCHA_LABEL_KEY, None)
            if email_sent:
                messages.success(request, 'Регистрация завершена. Подтвердите email по ссылке из письма.')
            else:
                messages.warning(
                    request,
                    'Регистрация завершена, но письмо подтверждения не отправилось. '
                    'Попробуйте войти снова, чтобы отправить новую ссылку, или обратитесь в поддержку.'
                )
            return redirect('login')
        if not captcha_ok and 'captcha_answer' not in form.errors:
            form.add_error('captcha_answer', 'Неверный ответ на проверочный вопрос.')
        _rate_limit_hit(register_key, REGISTER_RATE_WINDOW_SECONDS)
        _refresh_register_captcha(request)
        _apply_register_captcha_label(form, request)
    else:
        form = CustomUserCreationForm()
        _refresh_register_captcha(request)
        _apply_register_captcha_label(form, request)
    return render(request, 'accounts/register.html', {'form': form, 'default_time_zone': default_time_zone})

# Вход
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = (request.POST.get('username') or '').strip()
        password = request.POST.get('password')
        ip = _client_ip(request)
        ip_key = _rate_limit_key('login:ip', ip)
        user_key = _rate_limit_key('login:user', username.lower()) if username else None

        ip_limited = _rate_limit_exceeded(ip_key, LOGIN_IP_RATE_LIMIT)
        user_limited = user_key and _rate_limit_exceeded(user_key, LOGIN_USER_RATE_LIMIT)
        if ip_limited or user_limited:
            form.add_error(None, 'Слишком много попыток входа. Повторите через 15 минут.')
            return render(request, 'accounts/login.html', {'form': form})

        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.role == 'student' and not getattr(user, 'is_email_verified', True):
                email_sent = _send_email_verification(request, user)
                if email_sent:
                    form.add_error(None, 'Подтвердите email. Мы отправили вам новую ссылку для подтверждения.')
                else:
                    form.add_error(None, 'Подтвердите email. Не удалось отправить письмо подтверждения, попробуйте позже.')
                return render(request, 'accounts/login.html', {'form': form})

            if user.role == 'teacher' and not user.is_approved:
                _rate_limit_reset(ip_key)
                if user_key:
                    _rate_limit_reset(user_key)
                messages.error(request, 'Ваш аккаунт преподавателя ещё не одобрен администратором.')
                return redirect('login')

            _rate_limit_reset(ip_key)
            if user_key:
                _rate_limit_reset(user_key)
            login(request, user)

            if user.role == 'student':
                return redirect('student_dashboard')
            elif user.role == 'teacher':
                return redirect('teacher_dashboard')
            else:
                return redirect('admin:index')
        else:
            _rate_limit_hit(ip_key, LOGIN_RATE_WINDOW_SECONDS)
            if user_key:
                _rate_limit_hit(user_key, LOGIN_RATE_WINDOW_SECONDS)
            form.add_error(None, 'Неверное имя пользователя или пароль.')
            messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def resend_verification_view(request):
    prefill_email = ''
    if request.method == 'POST':
        prefill_email = (request.POST.get('email') or '').strip().lower()
        ip = _client_ip(request)
        limit_key = _rate_limit_key('verify_resend:ip', ip)

        if _rate_limit_exceeded(limit_key, RESEND_VERIFY_RATE_LIMIT):
            messages.error(request, 'Слишком много запросов. Повторите через 15 минут.')
            return render(
                request,
                'accounts/resend_verification.html',
                {'prefill_email': prefill_email},
            )

        _rate_limit_hit(limit_key, RESEND_VERIFY_RATE_WINDOW_SECONDS)

        if not prefill_email:
            messages.error(request, 'Укажите email для повторной отправки ссылки.')
            return render(
                request,
                'accounts/resend_verification.html',
                {'prefill_email': prefill_email},
            )

        user = (
            CustomUser.objects
            .filter(email__iexact=prefill_email, role='student', is_active=True)
            .first()
        )
        if user and not user.is_email_verified:
            _send_email_verification(request, user)

        # Do not reveal whether email/account exists.
        messages.success(
            request,
            'Если аккаунт с таким email найден и ещё не подтверждён, мы отправили новую ссылку.',
        )
        return redirect('login')

    return render(
        request,
        'accounts/resend_verification.html',
        {'prefill_email': prefill_email},
    )


def verify_email_view(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = CustomUser.objects.get(pk=uid)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        user = None

    if user is not None and default_token_generator.check_token(user, token):
        if not user.is_email_verified:
            user.is_email_verified = True
            user.save(update_fields=['is_email_verified'])
            request.session['show_welcome_onboarding'] = True
        messages.success(request, 'Email подтвержден. Теперь вы можете войти в аккаунт.')
    else:
        messages.error(request, 'Ссылка подтверждения недействительна или устарела.')
    return redirect('login')

# Выход
def logout_view(request):
    logout(request)
    return redirect('login')

# Пробный урок
def trial_lesson_view(request):
    if request.method == 'POST':
        form = TrialLessonForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            TrialRequest.objects.create(
                name=data['name'],
                email=data['email'],
                phone=data['phone'],
                subject=data['subject'],
                preferred_time=data['preferred_time'],
                message=data['message']
            )
            # Пока без отправки письма
            return render(request, 'accounts/trial_success.html')
    else:
        form = TrialLessonForm()
    subjects = Subject.objects.all()
    return render(request, 'accounts/trial_lesson.html', {'form': form, 'subjects': subjects})

from datetime import datetime, timedelta

from django.utils.timezone import now as tz_now
from django.utils import timezone
from lessons.utils import build_calendar_events

@login_required

def student_dashboard_view(request):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    request.user.refresh_from_db(fields=['balance'])

    user_tz = get_user_tz(request.user)
    now_local = tz_now().astimezone(user_tz)
    upcoming_lessons = []
    completed_lessons = []

    all_lessons = (
        Lesson.objects
        .filter(student=request.user)
        .select_related('teacher', 'subject')
        .order_by('date', 'time')
    )
    for lesson in all_lessons:
        teacher_tz = get_user_tz(lesson.teacher)
        now_teacher = tz_now().astimezone(teacher_tz)
        start_teacher = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        end_teacher = start_teacher + timedelta(minutes=lesson.duration_minutes)

        # Время для ученика (его таймзона)
        local_start = start_teacher.astimezone(user_tz)
        local_end = end_teacher.astimezone(user_tz)

        # Сохраняем для шаблона
        lesson.lesson_start = local_start
        lesson.lesson_end = local_end
        lesson.display_date = local_start.date()
        lesson.display_time = local_start.time()
        lesson.teacher_display_date = start_teacher.date()
        lesson.teacher_display_time = start_teacher.time()
        lesson.show_video = start_teacher - timedelta(minutes=5) <= now_teacher <= end_teacher

        # ✅ Добавляем только если урок ещё не закончился
        if end_teacher >= now_teacher:
            upcoming_lessons.append(lesson)
        else:
            completed_lessons.append(lesson)

    # Балансовые подсказки
    balance_warning = None
    if request.user.balance <= 0:
        balance_warning = 'Баланс пуст. Пополните, чтобы записываться на уроки.'
    elif request.user.balance <= 2:
        balance_warning = f'Осталось всего {request.user.balance} урока(ов).'

    balance_history = BalanceTransaction.objects.filter(user=request.user).order_by('-created_at')[:10]

    next_lesson = upcoming_lessons[0] if upcoming_lessons else None

    # Фильтр: текущая неделя (Пн–Вс)
    today = now_local.date()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)
    lessons_week = [l for l in upcoming_lessons if week_start <= l.display_date <= week_end]
    total_upcoming_week = len(lessons_week)
    total_lessons_count = len(upcoming_lessons) + len(completed_lessons)

    show_welcome_onboarding = bool(request.session.pop('show_welcome_onboarding', False))
    show_onboarding = show_welcome_onboarding or total_lessons_count == 0

    payment_reminder_level = None
    payment_reminder_text = None
    if request.user.balance <= 0:
        payment_reminder_level = 'critical'
        payment_reminder_text = 'Баланс пуст. Пополните его сейчас, чтобы запись на уроки проходила без пауз.'
    elif request.user.balance <= 2:
        payment_reminder_level = 'warning'
        payment_reminder_text = f'На балансе осталось {request.user.balance} урока(ов). Рекомендуем пополнить заранее.'
    elif total_upcoming_week and request.user.balance < total_upcoming_week:
        payment_reminder_level = 'info'
        payment_reminder_text = (
            f'На этой неделе запланировано {total_upcoming_week} уроков, '
            f'а на балансе {request.user.balance}. Пополните баланс, чтобы избежать переносов.'
        )

    from lessons.models import HomeworkSubmission

    homework_assigned_qs = (
        Lesson.objects
        .filter(student=request.user)
        .exclude(homework__isnull=True)
        .exclude(homework__exact='')
    )
    homework_assigned_count = homework_assigned_qs.count()
    submitted_homeworks_count = (
        HomeworkSubmission.objects
        .filter(student=request.user, lesson__in=homework_assigned_qs)
        .values('lesson_id')
        .distinct()
        .count()
    )
    homework_completion = (
        round((submitted_homeworks_count / homework_assigned_count) * 100)
        if homework_assigned_count
        else 0
    )
    pending_homeworks = max(homework_assigned_count - submitted_homeworks_count, 0)

    recent_homework_lessons = list(
        homework_assigned_qs
        .select_related('teacher', 'subject')
        .order_by('-date', '-time')[:3]
    )
    submitted_homework_lesson_ids = set(
        HomeworkSubmission.objects
        .filter(student=request.user, lesson__in=recent_homework_lessons)
        .values_list('lesson_id', flat=True)
    )
    for lesson in recent_homework_lessons:
        teacher_tz = get_user_tz(lesson.teacher)
        start_teacher = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        local_start = start_teacher.astimezone(user_tz)
        lesson.display_date = local_start.date()
        lesson.display_time = local_start.time()

    unread_count = StudentNotification.objects.filter(student=request.user, is_read=False).count()
    return render(request, 'accounts/student_dashboard.html', {
        'lessons': lessons_week,
        'total_upcoming': total_upcoming_week,
        'now': now_local,
        'balance_warning': balance_warning,
        'payment_reminder_level': payment_reminder_level,
        'payment_reminder_text': payment_reminder_text,
        'show_welcome_onboarding': show_welcome_onboarding,
        'show_onboarding': show_onboarding,
        'balance_history': balance_history,
        'next_lesson': next_lesson,
        'completed_lessons': len(completed_lessons),
        'homework_completion': homework_completion,
        'pending_homeworks': pending_homeworks,
        'homework_assigned_count': homework_assigned_count,
        'submitted_homeworks_count': submitted_homeworks_count,
        'recent_homework_lessons': recent_homework_lessons,
        'submitted_homework_lesson_ids': submitted_homework_lesson_ids,
        'notifications': StudentNotification.objects.filter(student=request.user).order_by('-created_at')[:5],
        'unread_count': unread_count,
    })


# Кабинет преподавателя
@login_required

def teacher_dashboard_view(request):
    if getattr(request.user, 'role', None) != 'teacher':
        return HttpResponse('Нет доступа', status=403)

    from lessons.models import TeacherAvailability

    # Получаем ВСЕ уроки учителя, включая регулярные
    all_lessons = Lesson.objects.filter(teacher=request.user).order_by('date', 'time')
    slots = TeacherAvailability.objects.filter(teacher=request.user)
    teacher_tz = get_user_tz(request.user)
    now_msk = timezone.now().astimezone(teacher_tz)

    upcoming_lessons = []
    lessons_needing_status = []
    events = []

    # ============================
    # 1. Обработка ВСЕХ уроков для боковой панели
    # ============================
    for lesson in all_lessons:
        # Для ВСЕХ уроков проверяем, что они еще не закончились
        start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        end_dt = start_dt + timedelta(minutes=lesson.duration_minutes)

        # Добавляем в upcoming_lessons если урок в будущем
        if end_dt >= now_msk:
            lesson.show_video = start_dt - timedelta(minutes=5) <= now_msk <= end_dt
            lesson.lesson_start = start_dt
            lesson.lesson_end = end_dt
            lesson.is_recurring_display = lesson.is_recurring  # Добавляем флаг для шаблона
            upcoming_lessons.append(lesson)
        else:
            if getattr(lesson, 'lesson_status', 'pending') == 'pending':
                lessons_needing_status.append(lesson)

    # ============================
    # 2. Создание событий для календаря
    # ============================
    
    # 2. События для календаря
    events = build_calendar_events(request.user, weeks=SERIES_WEEKS)

    # =====================================
    # 4. Сортируем upcoming_lessons по дате и ограничиваем количество
    # =====================================
    upcoming_lessons.sort(key=lambda x: (x.date, x.time))
    # Берем только ближайшие 5 уроков для отображения
    recent_lessons = upcoming_lessons[:5]

    # =====================================
    # Рендер
    # =====================================
    unread_count = TeacherNotification.objects.filter(teacher=request.user, is_read=False).count()
    teacher_tz_name = getattr(teacher_tz, 'key', None) or str(teacher_tz) or TEACHER_TZ_NAME
    return render(request, 'accounts/teacher_dashboard.html', {
        'events': json.dumps(events),
        'lessons': recent_lessons,  # Только ближайшие
        'all_lessons': upcoming_lessons,  # Все предстоящие
        'lessons_needing_status': lessons_needing_status,
        'notifications': TeacherNotification.objects.filter(teacher=request.user).order_by('-created_at')[:5],
        'unread_count': unread_count,
        'now': now_msk,
        'teacher_time_zone': teacher_tz_name,
    })
# Общий просмотр расписания (опционально)
@login_required
def my_schedule_view(request):
    if request.user.role == 'student':
        lessons = Lesson.objects.filter(student=request.user).order_by('date', 'time')
        user_tz = get_user_tz(request.user)
        for lesson in lessons:
            teacher_tz = get_user_tz(lesson.teacher)
            start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
            local_start = start_dt.astimezone(user_tz)
            lesson.display_date = local_start.date()
            lesson.display_time = local_start.time()
            lesson.teacher_display_date = start_dt.date()
            lesson.teacher_display_time = start_dt.time()
    elif request.user.role == 'teacher':
        lessons = Lesson.objects.filter(teacher=request.user).order_by('date', 'time')
    else:
        lessons = []
    return render(request, 'accounts/my_schedule.html', {'lessons': lessons})

# Заявка на вакансию
def teacher_application_view(request):
    vacancies = Vacancy.objects.filter(is_active=True).order_by('order', 'title')
    has_open_vacancies = vacancies.exists()

    initial_data = {}
    requested_vacancy = (request.GET.get('vacancy') or '').strip()
    if requested_vacancy.isdigit():
        selected_vacancy = vacancies.filter(id=int(requested_vacancy)).first()
        if selected_vacancy:
            initial_data['vacancy'] = selected_vacancy

    if request.method == 'POST':
        form = TeacherApplicationForm(request.POST)
        if form.is_valid():
            application = form.save()
            vacancy_title = application.vacancy.title if application.vacancy_id else application.specialization
            subject = 'Новая заявка на вакансию преподавателя'
            body_lines = [
                f'Вакансия: {vacancy_title}',
                f'Имя: {application.first_name}',
                f'Фамилия: {application.last_name}',
                f'ФИО: {application.name}',
                f'Email: {application.email}',
                f'Телефон: {application.phone}',
                f'Опыт (лет): {application.years_experience or ""}',
                f'Опыт работы: {application.experience}',
                f'Мотивация: {application.motivation}',
            ]
            body = '\n'.join(body_lines)
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL], fail_silently=True)
            return render(request, 'accounts/teacher_application_success.html', {'application': application})
    else:
        form = TeacherApplicationForm(initial=initial_data)

    return render(
        request,
        'accounts/teacher_application.html',
        {
            'form': form,
            'vacancies': vacancies,
            'has_open_vacancies': has_open_vacancies,
        },
    )

@login_required
def dashboard_router_view(request):
    if request.user.role == 'student':
        return redirect('student_dashboard')
    elif request.user.role == 'teacher':
        return redirect('teacher_dashboard')
    else:
        return redirect('admin:index')

@login_required

def lesson_history_view(request):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    user_tz = get_user_tz(request.user)

    # Все уроки ученика, начиная с последнего
    all_lessons = (
        Lesson.objects
        .filter(student=request.user)
        .select_related('teacher', 'subject')
        .order_by('-date', '-time')
    )

    history_lessons = []
    for lesson in all_lessons:
        teacher_tz = get_user_tz(lesson.teacher)
        now_teacher = timezone.now().astimezone(teacher_tz)
        start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        end_dt = start_dt + timedelta(minutes=lesson.duration_minutes)

        # ✅ В историю — если урок завершился
        if end_dt < now_teacher:
            local_start = start_dt.astimezone(user_tz)
            local_end = end_dt.astimezone(user_tz)
            lesson.lesson_start = local_start
            lesson.lesson_end = local_end
            lesson.display_date = local_start.date()
            lesson.display_time = local_start.time()
            lesson.teacher_display_date = start_dt.date()
            lesson.teacher_display_time = start_dt.time()
            history_lessons.append(lesson)

    history_lessons.sort(key=lambda lesson: (lesson.display_date, lesson.display_time), reverse=True)

    return render(request, 'accounts/student_lesson_history.html', {
        'lessons': history_lessons
    })



@login_required

def teacher_lesson_history_view(request):
    if getattr(request.user, 'role', None) != 'teacher':
        return HttpResponse('Нет доступа', status=403)

    teacher_tz = get_user_tz(request.user)
    now_msk = timezone.now().astimezone(teacher_tz)

    # Все уроки учителя
    all_lessons = Lesson.objects.filter(teacher=request.user).order_by('-date', '-time')

    # ✅ В историю — только те, что уже завершились
    history_lessons = []
    for lesson in all_lessons:
        start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        end_dt = start_dt + timedelta(minutes=lesson.duration_minutes)

        if end_dt < now_msk:
            lesson.lesson_start = start_dt
            lesson.lesson_end = end_dt
            history_lessons.append(lesson)

    return render(request, 'accounts/teacher_lesson_history.html', {
        'lessons': history_lessons
    })

from django.shortcuts import render, get_object_or_404, redirect
from accounts.models import Lesson, Subject
from .forms import LessonFeedbackForm
from lessons.forms import HomeworkSubmissionForm
from lessons.models import TeacherAvailability


@login_required

def lesson_feedback_view(request, lesson_id):
    if getattr(request.user, 'role', None) != 'teacher':
        return HttpResponse('Нет доступа', status=403)

    lesson = get_object_or_404(Lesson, id=lesson_id, teacher=request.user)

    if request.method == 'POST':
        form = LessonFeedbackForm(request.POST, request.FILES, instance=lesson)  # 👈 request.FILES
        if form.is_valid():
            form.save()
            messages.success(request, "Комментарий и домашнее задание сохранены!")
            return redirect('teacher_dashboard')
    else:
        form = LessonFeedbackForm(instance=lesson)

    return render(request, 'lessons/lesson_feedback.html', {
        'lesson': lesson,
        'form': form
    })

from lessons.models import HomeworkSubmission

@login_required

def my_homeworks_view(request):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    # Все уроки ученика, где выдано ДЗ
    base_lessons = (
        Lesson.objects
        .filter(student=request.user)
        .select_related('teacher', 'subject')
        .exclude(homework__isnull=True)
        .exclude(homework__exact='')
        .order_by('-date', '-time')
    )
    selected_subject = request.GET.get('subject') or ''
    lessons = base_lessons
    if selected_subject:
        lessons = lessons.filter(subject_id=selected_subject)

    subjects = Subject.objects.filter(
        id__in=base_lessons.values_list('subject_id', flat=True)
    ).distinct().order_by('name')
    user_tz = get_user_tz(request.user)
    for lesson in lessons:
        teacher_tz = get_user_tz(lesson.teacher)
        start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        local_start = start_dt.astimezone(user_tz)
        lesson.display_date = local_start.date()
        lesson.display_time = local_start.time()
        lesson.teacher_display_date = start_dt.date()
        lesson.teacher_display_time = start_dt.time()

    return render(request, 'accounts/student_homeworks.html', {
        'lessons': lessons,
        'subjects': subjects,
        'selected_subject': selected_subject
    })

@login_required
def student_mark_notifications_read_view(request):
    if request.method != 'POST' or getattr(request.user, 'role', None) != 'student':
        return JsonResponse({'ok': False}, status=400)
    StudentNotification.objects.filter(student=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})

@login_required
def teacher_mark_notifications_read_view(request):
    if request.method != 'POST' or getattr(request.user, 'role', None) != 'teacher':
        return JsonResponse({'ok': False}, status=400)
    TeacherNotification.objects.filter(teacher=request.user, is_read=False).update(is_read=True)
    return JsonResponse({'ok': True})
@login_required

def submit_homework_view(request, lesson_id):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    lesson = get_object_or_404(Lesson, id=lesson_id, student=request.user)

    if request.method == 'POST':
        form = HomeworkSubmissionForm(request.POST, request.FILES)
        if form.is_valid():
            submission = form.save(commit=False)
            submission.lesson = lesson
            submission.student = request.user
            submission.save()
            messages.success(request, "Ответ отправлен!")
            return redirect('my_homeworks')
    else:
        form = HomeworkSubmissionForm()

    return render(request, 'accounts/submit_homework.html', {
        'lesson': lesson,
        'form': form
    })

from lessons.models import HomeworkSubmission  # убедись, что импортируешь правильно

@login_required

def teacher_homework_submissions_view(request):
    if getattr(request.user, 'role', None) != 'teacher':
        return HttpResponse('Нет доступа', status=403)

    submissions = HomeworkSubmission.objects.filter(
        lesson__teacher=request.user
    ).select_related('lesson', 'student').order_by('-submitted_at')

    return render(request, 'accounts/teacher_homework_submissions.html', {
        'submissions': submissions
    })



@login_required
def balance_topup_request_view(request):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    if request.method == 'POST':
        form = BalanceTopUpRequestForm(request.POST)
        if form.is_valid():
            req = form.save(commit=False)
            req.user = request.user
            req.status = 'pending'
            req.save()
            messages.success(request, 'Заявка на пополнение отправлена. Администратор свяжется с вами.')
            return redirect('student_dashboard')
    else:
        form = BalanceTopUpRequestForm()

    return render(request, 'accounts/balance_topup_request.html', {'form': form})


@login_required
def student_vacation_request_view(request):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    tomorrow = timezone.localdate() + timedelta(days=1)
    vacations = request.user.vacations.select_related('created_by').order_by('-created_at')[:20]

    if request.method == 'POST':
        form = StudentVacationRequestForm(request.POST)
        if form.is_valid():
            vacation = form.save(commit=False)
            vacation.student = request.user
            vacation.created_by = request.user
            vacation.save()
            affected = vacation.apply_vacation()
            messages.success(
                request,
                f'Отпуск оформлен. Снято уроков: {affected}. '
                'Слоты преподавателя на этот период освобождены.'
            )
            return redirect('student_vacation_request')
    else:
        form = StudentVacationRequestForm(initial={
            'start_date': tomorrow,
            'end_date': tomorrow,
        })

    return render(request, 'accounts/student_vacation_request.html', {
        'form': form,
        'vacations': vacations,
        'tomorrow': tomorrow,
    })


@login_required
def update_lesson_status(request, lesson_id):
    if getattr(request.user, 'role', None) != 'teacher':
        return HttpResponse('Нет доступа', status=403)

    lesson = get_object_or_404(Lesson, id=lesson_id, teacher=request.user)

    if request.method != 'POST':
        return HttpResponse('Метод не поддерживается', status=405)

    status = request.POST.get('status')
    allowed = {'conducted', 'missed_teacher', 'missed_student'}
    if status not in allowed:
        return HttpResponse('Некорректный статус', status=400)

    lesson.lesson_status = status
    lesson.is_completed = (status == 'conducted')
    lesson.save(update_fields=['lesson_status', 'is_completed'])

    messages.success(request, 'Статус урока обновлён')
    return redirect('teacher_dashboard')


@login_required
def teacher_finance_view(request):
    if getattr(request.user, 'role', None) != 'teacher':
        return HttpResponse('Нет доступа', status=403)

    entries = TeacherFinanceEntry.objects.filter(teacher=request.user).select_related('lesson', 'lesson__student', 'lesson__subject').order_by('-created_at')
    total_all = sum(e.amount for e in entries)

    from django.utils import timezone
    from datetime import timedelta
    since = timezone.now() - timedelta(days=30)
    entries_30 = entries.filter(created_at__gte=since)
    paid_30 = sum(e.amount for e in entries_30.filter(payout_status='paid'))
    accrued_30 = sum(e.amount for e in entries_30.filter(payout_status='accrued'))

    # В блоке "последние 30 дней" показываем только невыплаченное
    total_30_unpaid = accrued_30

    return render(request, 'accounts/teacher_finance.html', {
        'entries': entries,
        'total_all': total_all,
        'total_30': total_30_unpaid,
        'paid_30': paid_30,
        'accrued_30': accrued_30,
    })


@login_required
def student_balance_view(request):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    balance_history = BalanceTransaction.objects.filter(user=request.user).order_by('-created_at')[:50]

    return render(request, 'accounts/student_balance.html', {
        'balance_history': balance_history,
    })


@login_required
def student_upcoming_lessons_view(request):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    user_tz = get_user_tz(request.user)
    now_local = tz_now().astimezone(user_tz)
    lessons = []
    for lesson in (
        Lesson.objects
        .filter(student=request.user)
        .select_related('teacher', 'subject')
        .order_by('date', 'time')
    ):
        teacher_tz = get_user_tz(lesson.teacher)
        now_teacher = tz_now().astimezone(teacher_tz)
        start_teacher = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
        end_teacher = start_teacher + timedelta(minutes=lesson.duration_minutes)
        local_start = start_teacher.astimezone(user_tz)
        local_end = end_teacher.astimezone(user_tz)
        lesson.lesson_start = local_start
        lesson.lesson_end = local_end
        lesson.display_date = local_start.date()
        lesson.display_time = local_start.time()
        lesson.teacher_display_date = start_teacher.date()
        lesson.teacher_display_time = start_teacher.time()
        lesson.show_video = start_teacher - timedelta(minutes=5) <= now_teacher <= end_teacher
        if end_teacher >= now_teacher:
            lessons.append(lesson)

    return render(request, 'accounts/student_upcoming_lessons.html', {
        'lessons': lessons,
        'now': now_local,
    })


@login_required
def student_cancel_lesson_view(request, lesson_id):
    if getattr(request.user, 'role', None) != 'student':
        return HttpResponse('Нет доступа', status=403)

    lesson = get_object_or_404(Lesson, id=lesson_id, student=request.user)

    # Только будущие уроки можно отменять
    teacher_tz = get_user_tz(lesson.teacher)
    now_teacher = timezone.now().astimezone(teacher_tz)
    start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time), teacher_tz)
    if start_dt <= now_teacher:
        messages.error(request, 'Нельзя отменить уже начавшийся или прошедший урок.')
        return redirect('student_dashboard')

    if request.method != 'POST':
        return HttpResponse('Метод не поддерживается', status=405)

    teacher = lesson.teacher
    subject = lesson.subject
    date_val = lesson.date
    time_val = lesson.time

    # Проверка 4 часов
    hours_left = (start_dt - now_teacher).total_seconds() / 3600
    is_late_cancel = hours_left < 4

    if is_late_cancel:
        # Начисляем учителю оплату, списываем у ученика урок
        amount_value = get_teacher_payout_amount_for_lesson(teacher, lesson, subject=subject)

        # списание баланса (не уходим ниже 0)
        if request.user.balance > 0:
            request.user.balance -= 1
            request.user.save(update_fields=['balance'])
        BalanceTransaction.objects.create(
            user=request.user,
            lesson=lesson,
            direction='debit',
            amount=1,
            note='Поздняя отмена (менее 4 часов)'
        )

        subject_name = lesson.subject.name if getattr(lesson, "subject", None) else ""
        if getattr(lesson, "student", None):
            student_name = lesson.student.get_full_name() or lesson.student.username
        else:
            student_name = ""
        TeacherFinanceEntry.objects.create(
            teacher=teacher,
            lesson=lesson,
            subject_name=subject_name,
            student_name=student_name,
            lesson_date=lesson.date,
            lesson_time=lesson.time,
            lesson_status=getattr(lesson, "lesson_status", "") or "",
            amount=amount_value
        )

        # Статус урока
        lesson.lesson_status = 'missed_student'
        lesson.is_completed = False
        lesson.save(update_fields=['lesson_status', 'is_completed'])

    # Удаляем урок из расписания
    lesson.delete()

    # Освобождаем слот (создаем разовый, если нет регулярного на этот день)
    from lessons.models import TeacherAvailability
    weekday = date_val.weekday()
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

    # Уведомление преподавателю
    msg = f"Ученик {request.user.get_full_name() or request.user.username} отменил урок {subject.name} на {date_val} {time_val}"
    if is_late_cancel:
        msg += " (поздняя отмена, начисление сохранено)"

    TeacherNotification.objects.create(
        teacher=teacher,
        message=msg
    )

    if is_late_cancel:
        messages.warning(request, 'Урок отменён поздно (менее 4 часов). Начисление сохранено.')
    else:
        messages.success(request, 'Урок отменён. Преподавателю отправлено уведомление.')

    return redirect('student_dashboard')

    if request.method != 'POST':
        return HttpResponse('Метод не поддерживается', status=405)

    teacher = lesson.teacher
    subject = lesson.subject
    date_val = lesson.date
    time_val = lesson.time

    # Удаляем урок
    lesson.delete()

    # Освобождаем слот (создаем разовый, если не было)
    from lessons.models import TeacherAvailability
    slot, created = TeacherAvailability.objects.get_or_create(
        teacher=teacher,
        date=date_val,
        time=time_val,
        defaults={'duration_minutes': 30, 'is_booked': False, 'is_recurring': False}
    )
    if not created:
        slot.is_booked = False
        slot.save(update_fields=['is_booked'])

    # Уведомление преподавателю
    TeacherNotification.objects.create(
        teacher=teacher,
        message=f"Ученик {request.user.get_full_name() or request.user.username} отменил урок {subject.name} на {date_val} {time_val}"
    )

    messages.success(request, 'Урок отменён. Преподавателю отправлено уведомление.')
    return redirect('student_dashboard')
