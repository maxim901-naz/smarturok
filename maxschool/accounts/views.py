from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from datetime import date
import json

from .forms import (
    CustomUserCreationForm,
    TrialLessonForm,
    TeacherApplicationForm
)

from .models import (
    CustomUser,
    Lesson,
    TrialRequest,
    Subject
)

# Регистрация
def register_view(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if user.role == 'teacher':
                user.is_approved = False
            else:
                user.is_approved = True
            user.save()
            login(request, user)

            if user.role == 'student':
                return redirect('student_dashboard')
            elif user.role == 'teacher':
                return redirect('teacher_dashboard')
            else:
                return redirect('admin:index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'accounts/register.html', {'form': form})

# Вход
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.role == 'teacher' and not user.is_approved:
                messages.error(request, 'Ваш аккаунт преподавателя ещё не одобрен администратором.')
                return redirect('login')

            login(request, user)

            if user.role == 'student':
                return redirect('student_dashboard')
            elif user.role == 'teacher':
                return redirect('teacher_dashboard')
            else:
                return redirect('admin:index')
        else:
            messages.error(request, 'Неверное имя пользователя или пароль.')
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})

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

@login_required
def student_dashboard_view(request):
    now = tz_now()  # Текущее время с учётом таймзоны
    upcoming_lessons = []

    for lesson in Lesson.objects.filter(student=request.user).order_by('date', 'time'):
        # Преобразуем локальную дату и время в aware datetime
        local_start = timezone.make_aware(datetime.combine(lesson.date, lesson.time))
        local_end = local_start + timedelta(minutes=lesson.duration_minutes)

        # Сохраняем для шаблона
        lesson.lesson_start = local_start
        lesson.lesson_end = local_end
        lesson.show_video = local_start - timedelta(minutes=5) <= now <= local_end

        # ✅ Добавляем только если урок ещё не закончился
        if local_end >= now:
            upcoming_lessons.append(lesson)

    return render(request, 'accounts/student_dashboard.html', {
        'lessons': upcoming_lessons,
        'now': now,
    })


# Кабинет преподавателя
# @login_required
# def teacher_dashboard_view(request):
#     lessons = Lesson.objects.filter(teacher=request.user)
#     events = [
#         {
#             'title': f"{lesson.subject.name} — {lesson.student.get_full_name()}",
#             'start': f"{lesson.date}T{lesson.time}"
#         }
#         for lesson in lessons
#     ]
#     return render(request, 'accounts/teacher_dashboard.html', {'events': events})
from datetime import datetime, timedelta
from django.utils import timezone

from django.utils import timezone
from datetime import datetime, timedelta
import json

# @login_required
# def teacher_dashboard_view(request):
#     all_lessons = Lesson.objects.filter(teacher=request.user).order_by('date', 'time')
#     now = timezone.localtime()  # ✅ aware datetime

#     upcoming_lessons = []  # сюда попадут только будущие/текущие уроки

#     for lesson in all_lessons:
#         # aware datetime начала и конца урока
#         start_dt = datetime.combine(lesson.date, lesson.time)
#         local_start = timezone.make_aware(start_dt)
#         local_end = local_start + timedelta(minutes=lesson.duration_minutes)

#         # Для шаблона
#         lesson.lesson_start = local_start
#         lesson.lesson_end = local_end
#         lesson.show_video = local_start - timedelta(minutes=5) <= now <= local_end

#         # Добавляем в предстоящие, если урок ещё не закончился
#         if local_end >= now:
#             upcoming_lessons.append(lesson)

#     # Все уроки остаются в календаре
#     events = [
#         {
#             'title': f"{lesson.subject.name} — {lesson.student.get_full_name() or lesson.student.username}",
#             'start': f"{lesson.date}T{lesson.time}"
#         }
#         for lesson in all_lessons
#     ]

#     return render(request, 'accounts/teacher_dashboard.html', {
#         'events': json.dumps(events),      # календарь — все уроки
#         'lessons': upcoming_lessons,       # главная — только будущие
#         'now': now,
#     })
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from datetime import datetime, timedelta
import json

# @login_required
def teacher_dashboard_view(request):
    from lessons.models import TeacherAvailability  # если не импортировано выше

    all_lessons = Lesson.objects.filter(teacher=request.user).order_by('date', 'time')
    slots = TeacherAvailability.objects.filter(teacher=request.user).order_by('date', 'time')

    now = timezone.localtime()
    upcoming_lessons = []

    for lesson in all_lessons:
        start_dt = datetime.combine(lesson.date, lesson.time)
        local_start = timezone.make_aware(start_dt)
        local_end = local_start + timedelta(minutes=lesson.duration_minutes)
        if local_end >= now:
            lesson.show_video = local_start - timedelta(minutes=5) <= now <= local_end
            upcoming_lessons.append(lesson)

    events = []

    # Уроки (кликаются как уроки)
    for lesson in all_lessons:
        events.append({
            'id': f'lesson-{lesson.id}',
            'title': f"{lesson.subject.name} — {lesson.student.get_full_name() or lesson.student.username}",
            'start': f"{lesson.date}T{lesson.time}",
            'color': '#F87171',
            'extendedProps': {
                'type': 'lesson',
                'lesson_id': lesson.id
            }
        })

    # Свободные слоты (кликаются как слоты)
    for slot in slots:
        if not slot.is_booked:
            events.append({
                'id': f'slot-{slot.id}',
                'title': 'Свободный слот',
                'start': f"{slot.date}T{slot.time}",
                'color': '#34D399',
                'extendedProps': {
                    'type': 'slot',
                    'slot_id': slot.id
                }
            })

    return render(request, 'accounts/teacher_dashboard.html', {
        'events': json.dumps(events),
        'lessons': upcoming_lessons,
        'now': now,
    })


# Общий просмотр расписания (опционально)
@login_required
def my_schedule_view(request):
    if request.user.role == 'student':
        lessons = Lesson.objects.filter(student=request.user).order_by('date', 'time')
    elif request.user.role == 'teacher':
        lessons = Lesson.objects.filter(teacher=request.user).order_by('date', 'time')
    else:
        lessons = []
    return render(request, 'accounts/my_schedule.html', {'lessons': lessons})

# Заявка на вакансию
def teacher_application_view(request):
    if request.method == 'POST':
        form = TeacherApplicationForm(request.POST)
        if form.is_valid():
            application = form.save()
            subject = "Новая заявка на вакансию преподавателя"
            body = (
                f"Имя: {application.name}\n"
                f"Email: {application.email}\n"
                f"Телефон: {application.phone}\n"
                f"Специализация: {application.specialization}\n"
                f"Опыт: {application.experience}\n"
                f"Мотивация: {application.motivation}"
            )
            send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL])
            return render(request, 'accounts/teacher_application_success.html')
    else:
        form = TeacherApplicationForm()
    return render(request, 'accounts/teacher_application.html', {'form': form})
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
    now = timezone.localtime()

    # Все уроки ученика, начиная с последнего
    all_lessons = Lesson.objects.filter(student=request.user).order_by('-date', '-time')

    history_lessons = []
    for lesson in all_lessons:
        start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time))
        end_dt = start_dt + timedelta(minutes=lesson.duration_minutes)

        # ✅ В историю — если урок завершился
        if end_dt < now:
            history_lessons.append(lesson)

    return render(request, 'accounts/student_lesson_history.html', {
        'lessons': history_lessons
    })


from django.utils.timezone import now as tz_now

@login_required
def teacher_lesson_history_view(request):
    now = timezone.localtime()  # Текущее время с учетом часового пояса

    # Все уроки учителя
    all_lessons = Lesson.objects.filter(teacher=request.user).order_by('-date', '-time')

    # ✅ В историю — только те, что уже завершились
    history_lessons = []
    for lesson in all_lessons:
        start_dt = timezone.make_aware(datetime.combine(lesson.date, lesson.time))
        end_dt = start_dt + timedelta(minutes=lesson.duration_minutes)

        if end_dt < now:
            history_lessons.append(lesson)

    return render(request, 'accounts/teacher_lesson_history.html', {
        'lessons': history_lessons
    })

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from accounts.models import Lesson
from .forms import LessonFeedbackForm
from lessons.forms import HomeworkSubmissionForm
from lessons.models import TeacherAvailability


@login_required
def lesson_feedback_view(request, lesson_id):
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
    # Все уроки ученика, где выдано ДЗ
    lessons = Lesson.objects.filter(
        student=request.user
    ).exclude(homework='').order_by('-date', '-time')

    return render(request, 'accounts/student_homeworks.html', {
        'lessons': lessons
    })
@login_required
def submit_homework_view(request, lesson_id):
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
    submissions = HomeworkSubmission.objects.filter(
        lesson__teacher=request.user
    ).select_related('lesson', 'student').order_by('-submitted_at')

    return render(request, 'accounts/teacher_homework_submissions.html', {
        'submissions': submissions
    })

# from django.shortcuts import render

# from django.shortcuts import render, redirect
# from django.contrib.auth import login
# from .forms import CustomUserCreationForm

# from django.shortcuts import render
# from django.core.mail import send_mail
# from django.conf import settings
# from .forms import TrialLessonForm
# from .models import TrialRequest, Subject

# def register_view(request):
#     if request.method == 'POST':
#         form = CustomUserCreationForm(request.POST)
#         if form.is_valid():
#             user = form.save(commit=False)
#             if user.role == 'teacher':
#                 user.is_approved = False
#             else:
#                 user.is_approved = True
#             user.save()
#             login(request, user)
#             return redirect('dashboard')
#     else:
#         form = CustomUserCreationForm()
#     return render(request, 'accounts/register.html', {'form': form})

# from django.contrib.auth import authenticate, login
# from django.contrib import messages
# from django.contrib.auth.forms import AuthenticationForm

# def login_view(request):
#     if request.method == 'POST':
#         form = AuthenticationForm(request, data=request.POST)

#         # Вручную достаем username и password
#         username = request.POST.get('username')
#         password = request.POST.get('password')
#         user = authenticate(request, username=username, password=password)

#         if user is not None:
#             if user.role == 'teacher' and not user.is_approved:
#                 messages.error(request, 'Ваш аккаунт преподавателя ещё не одобрен администратором.')
#                 return redirect('login')
#             login(request, user)
#             return redirect('dashboard')
#         else:
#             messages.error(request, 'Неверное имя пользователя или пароль.')
#     else:
#         form = AuthenticationForm()
#     return render(request, 'accounts/login.html', {'form': form})
# from django.contrib.auth.decorators import login_required

# @login_required
# def dashboard_view(request):
#     return render(request, 'accounts/dashboard.html', {'user': request.user})
# from django.contrib.auth import logout

# def logout_view(request):
#     logout(request)
#     return redirect('login')
# from django.core.mail import send_mail
# from django.conf import settings
# from .forms import TrialLessonForm

# from .models import TrialRequest
# from .forms import TrialLessonForm
# from django.core.mail import send_mail
# from django.conf import settings

# def trial_lesson_view(request):
#     if request.method == 'POST':
#         form = TrialLessonForm(request.POST)
#         if form.is_valid():
#             data = form.cleaned_data

#             # 1. Сохраняем в базу данных
#             TrialRequest.objects.create(
#                 name=data['name'],
#                 email=data['email'],
#                 phone=data['phone'],
#                 subject=data['subject'],
#                 preferred_time=data['preferred_time'],
#                 message=data['message']
#             )

#             # 2. Отправляем письмо
#             # subject = "Заявка на пробный урок"
#             # body = (
#             #     f"Имя: {data['name']}\n"
#             #     f"Email: {data['email']}\n"
#             #     f"Телефон: {data['phone']}\n"
#             #     f"Предмет: {data['subject']}\n"
#             #     f"Удобное время: {data['preferred_time']}\n"
#             #     f"Комментарий: {data['message']}"
#             # )
#             # send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL])

#             return render(request, 'accounts/trial_success.html')
#     else:
#         form = TrialLessonForm()
#     subjects = Subject.objects.all()  # 👈 передаём список предметов
#     return render(request, 'accounts/trial_lesson.html', {
#         'form': form,
#         'subjects': subjects
#     })
#     # return render(request, 'accounts/trial_lesson.html', {'form': form})

# from datetime import date
# from .models import Lesson
# from django.contrib.auth.decorators import login_required

# @login_required
# def my_schedule_view(request):
#     if request.user.role == 'student':
#         lessons = Lesson.objects.filter(student=request.user).order_by('date', 'time')
#     elif request.user.role == 'teacher':
#         lessons = Lesson.objects.filter(teacher=request.user).order_by('date', 'time')
#     else:
#         lessons = []

#     return render(request, 'accounts/my_schedule.html', {'lessons': lessons})


# from django.shortcuts import render, redirect
# from django.core.mail import send_mail
# from django.conf import settings
# from .forms import TeacherApplicationForm

# def teacher_application_view(request):
#     if request.method == 'POST':
#         form = TeacherApplicationForm(request.POST)
#         if form.is_valid():
#             application = form.save()

#             # Уведомление на почту админа
#             subject = "Новая заявка на вакансию преподавателя"
#             body = (
#                 f"Имя: {application.name}\n"
#                 f"Email: {application.email}\n"
#                 f"Телефон: {application.phone}\n"
#                 f"Специализация: {application.specialization}\n"
#                 f"Опыт: {application.experience}\n"
#                 f"Мотивация: {application.motivation}"
#             )
#             send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.ADMIN_EMAIL])

#             return render(request, 'accounts/teacher_application_success.html')
#     else:
#         form = TeacherApplicationForm()
#     return render(request, 'accounts/teacher_application.html', {'form': form})

# @login_required
# def student_dashboard_view(request):
#     lessons = Lesson.objects.filter(student=request.user).order_by('date', 'time')
#     return render(request, 'accounts/student_dashboard.html', {'lessons': lessons})