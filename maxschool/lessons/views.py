from django.shortcuts import render, redirect, get_object_or_404
from .forms import LessonBookingForm
from .models import LessonBooking
from accounts.models import Lesson
from django.contrib.auth.decorators import login_required

# 📌 1. Ученик бронирует урок
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import LessonBookingForm

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .forms import LessonBookingForm
from accounts.models import CustomUser

from django.http import HttpResponse
import uuid

# @login_required
# def book_lesson_view(request, teacher_id):
#     teacher = get_object_or_404(CustomUser, id=teacher_id, role='teacher', is_approved=True)

#     if request.method == 'POST':
#         form = LessonBookingForm(request.POST, student=request.user, teacher=teacher)
#         if form.is_valid():
#             booking = form.save()  # 💡 ВСЁ уже будет в form.save() внутри
#             return render(request, 'lessons/booking_success.html', {'booking': booking})
#     else:
#         form = LessonBookingForm(student=request.user, teacher=teacher)

#     return render(request, 'lessons/book_lesson.html', {
#         'form': form,
#         'teacher': teacher
#     })

@login_required
def book_lesson_view(request, teacher_id):
    teacher = get_object_or_404(CustomUser, id=teacher_id, role='teacher', is_approved=True)

    if request.method == 'POST':
        form = LessonBookingForm(request.POST, student=request.user, teacher=teacher)
        if form.is_valid():
            booking = form.save()
            return render(request, 'lessons/booking_success.html', {'booking': booking})
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
import uuid
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from lessons.models import LessonBooking
from accounts.models import Lesson  # 👈 так правильно, т.к. Lesson в другом приложении
 # убедись, что импорт верный

@login_required
def confirm_booking_view(request, booking_id):
    booking = get_object_or_404(LessonBooking, id=booking_id, teacher=request.user)

    booking.is_confirmed = True
    booking.save()

    booking.student.teachers.add(booking.teacher)
    booking.student.save()
    unique_id = uuid.uuid4()

    # Общая комната доски (можно генерировать ключ, если хочешь приватность)
    excalidraw_url = f"https://excalidraw.com/#room=maxschool-{unique_id},UzFb4IpZYbG4wRz7Yp5pTQ"
    
    Lesson.objects.create(
        teacher=booking.teacher,
        student=booking.student,
        subject=booking.subject,
        date=booking.date,
        time=booking.time,
        duration_minutes=30,
        video_url=f"https://meet.jit.si/maxschool-{uuid.uuid4()}",  # 👈 уникальная ссылка
        
    )

    return redirect('teacher_bookings')
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import TeacherAvailability

@login_required
def add_availability_view(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')

    if request.method == 'POST':
        date = request.POST.get('date')
        time = request.POST.get('time')
        duration = request.POST.get('duration', 30)
        TeacherAvailability.objects.create(
            teacher=request.user,
            date=date,
            time=time,
            duration_minutes=duration
        )
        return redirect('teacher_availability')

    return render(request, 'lessons/add_availability.html')

@login_required
def teacher_availability_view(request):
    if request.user.role != 'teacher':
        return redirect('dashboard')

    slots = TeacherAvailability.objects.filter(teacher=request.user).order_by('date', 'time')
    return render(request, 'lessons/teacher_availability.html', {'slots': slots})

@login_required
def delete_availability_view(request, slot_id):
    slot = get_object_or_404(TeacherAvailability, id=slot_id, teacher=request.user)
    if request.method == 'POST':
        slot.delete()
    return redirect('teacher_availability')

#доска и связь
from django.shortcuts import render, get_object_or_404
from .models import Lesson

from datetime import datetime, timedelta

# def lesson_session(request, lesson_id):
#     lesson = get_object_or_404(Lesson, id=lesson_id)

#     # Вычисляем, пора ли показывать ссылку
#     start_datetime = datetime.combine(lesson.date, lesson.time)
#     show_video = datetime.now() >= (start_datetime - timedelta(minutes=5))

#     if not show_video:
#         return render(request, "lesson_not_started.html", {"lesson": lesson})

#     return render(request, "lessons/lesson_session.html", {
#         "lesson": lesson,
#         "jitsi_room": f"maxschool_lesson_{lesson.id}",
#         "user_name": request.user.get_full_name() or request.user.username
#     })
def lesson_session(request, lesson_id):
    lesson = get_object_or_404(Lesson, id=lesson_id)
    
    # Вычисляем, пора ли показывать ссылку
    start_datetime = datetime.combine(lesson.date, lesson.time)
    show_video = datetime.now() >= (start_datetime - timedelta(minutes=5))

    if not show_video:
        return render(request, "lesson_not_started.html", {"lesson": lesson})
    
    # Проверяем, является ли текущий пользователь учителем этого урока
    is_teacher = False
    if hasattr(lesson, 'teacher'):
        # Если урок связан с конкретным учителем
        is_teacher = (request.user == lesson.teacher)
    else:
        # Альтернативная проверка: является ли пользователь учителем в группе
        is_teacher = request.user.groups.filter(name='Teachers').exists()
    
    return render(request, "lessons/lesson_session.html", {
        "lesson": lesson,
        "lesson_id": lesson.id,  # ✅ добавляем для WebSocket
        "jitsi_room": f"maxschool_lesson_{lesson.id}",
        "user_name": request.user.get_full_name() or request.user.username,
        "is_teacher": is_teacher  # Передаем флаг в шаблон
    })
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404
from .models import TeacherAvailability, Lesson


@login_required
def select_teacher(request):
    # Берём всех учителей, у которых у этого студента есть подтверждённые уроки
    teachers = CustomUser.objects.filter(
        role='teacher',
        lessons_to_teach__student=request.user,
        lessons_to_teach__is_confirmed=True  # только подтверждённые
    ).distinct()
    
    print("Teachers:", teachers)  # Проверка
    return render(request, "lessons/select_teacher.html", {"teachers": teachers})

# @login_required
# def available_slots(request, teacher_id):
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
    
    # проверяем, что ученик может записаться к этому учителю
    if slot.teacher not in request.user.teachers.all():
        return redirect("schedule_lesson")

    # создаём урок
    Lesson.objects.create(
        student=request.user,
        teacher=slot.teacher,
        date=slot.date,
        time=slot.time  # исправлено
    )

    # отмечаем слот как занятый
    slot.is_booked = True
    slot.save()

    return redirect("my_lessons")

# views.py
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from .models import Lesson

@login_required
def my_students(request):
    if request.user.role != 'teacher':
        return render(request, "not_allowed.html")  # или редирект
    
    # Находим всех учеников, у которых есть уроки с этим учителем
    lessons = Lesson.objects.filter(teacher=request.user).select_related('student').order_by('student__username')

    # Убираем дубликаты (один ученик может быть в нескольких уроках)
    students = {lesson.student for lesson in lessons}

    return render(request, "lessons/my_students.html", {"students": students})


# #Для календаря
# import json
# from django.http import JsonResponse
# from django.views.decorators.csrf import csrf_exempt
# from django.contrib.auth.decorators import login_required
# from django.utils.dateparse import parse_datetime, parse_date, parse_time
# from django.shortcuts import get_object_or_404

# from .models import TeacherAvailability
# from accounts.models import Lesson, CustomUser, Subject


# @login_required
# def create_free_slot(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         start = parse_datetime(data.get("start"))
#         end = parse_datetime(data.get("end"))

#         slot = TeacherAvailability.objects.create(
#             teacher=request.user,
#             date=start.date(),
#             time=start.time(),
#             duration_minutes=int((end - start).seconds / 60),
#             is_booked=False
#         )
#         return JsonResponse({"success": True, "id": slot.id})
#     return JsonResponse({"success": False}, status=400)


# @login_required
# def assign_student_to_slot(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         slot_id = data.get("slot_id")
#         student_id = data.get("student_id")

#         slot = get_object_or_404(TeacherAvailability, id=slot_id)
#         student = get_object_or_404(CustomUser, id=student_id, role="student")

#         if slot.is_booked:
#             return JsonResponse({"success": False, "error": "Слот уже занят"})

#         # ⚡ выбираем предмет — можно усложнить если у учителя несколько
#         subject = getattr(request.user, "desired_subject", None)
#         if not subject:
#             return JsonResponse({"success": False, "error": "У преподавателя не назначен предмет"})

#         lesson = Lesson.objects.create(
#             subject=subject,
#             teacher=request.user,
#             student=student,
#             date=slot.date,
#             time=slot.time,
#             duration_minutes=slot.duration_minutes
#         )

#         slot.is_booked = True
#         slot.save()

#         return JsonResponse({
#             "success": True,
#             "lesson_id": lesson.id,
#             "student_name": student.get_full_name() or student.username
#         })
#     return JsonResponse({"success": False}, status=400)


# @login_required
# def delete_free_slot(request):
#     if request.method == "POST":
#         data = json.loads(request.body)
#         slot_id = data.get("slot_id")

#         slot = get_object_or_404(TeacherAvailability, id=slot_id, teacher=request.user)
#         slot.delete()
#         return JsonResponse({"success": True})
#     return JsonResponse({"success": False}, status=400)


# from django.http import JsonResponse
# from accounts.models import CustomUser

# @login_required
# def get_students(request):
#     if request.user.role != "teacher":
#         return JsonResponse({"success": False, "error": "Доступ запрещён"}, status=403)

#     # ⚡ тут можно отфильтровать только "своих" учеников
#     # пока отдаём всех студентов
#     students = CustomUser.objects.filter(role="student").values("id", "first_name", "last_name", "username")

#     return JsonResponse({
#         "success": True,
#         "students": [
#             {
#                 "id": s["id"],
#                 "name": (s["first_name"] + " " + s["last_name"]).strip() or s["username"]
#             }
#             for s in students
#         ]
#     })
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_datetime

from .models import TeacherAvailability
from accounts.models import Lesson, CustomUser

# Создание свободного слота
from django.utils.dateparse import parse_datetime
from datetime import datetime, timedelta
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from .models import TeacherAvailability

@csrf_exempt
@login_required
def create_free_slot(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)
    try:
        data = json.loads(request.body)
        # print("RAW DATA:", data)  # Для отладки

        slots_data = data.get("slots")
        if not slots_data:
            return JsonResponse({"success": False, "error": "Нет дат"})

        created_slots = []

        for slot in slots_data:
            start_str = slot.get("start")
            end_str = slot.get("end")

            if not start_str or not end_str:
                continue

            try:
                start = datetime.fromisoformat(start_str.replace("Z", "+00:00"))
                end = datetime.fromisoformat(end_str.replace("Z", "+00:00"))
            except Exception:
                start = parse_datetime(start_str)
                end = parse_datetime(end_str)

            if not start or not end:
                continue

            new_slot = TeacherAvailability.objects.create(
                teacher=request.user,
                date=start.date(),
                time=start.time(),
                duration_minutes=int((end - start).seconds / 60),
                is_booked=False
            )

            created_slots.append({
                "id": new_slot.id,
                "start": start.isoformat(),
                "end": end.isoformat()
            })

        if not created_slots:
            return JsonResponse({"success": False, "error": "Не удалось создать слоты"})

        return JsonResponse({"success": True, "slots": created_slots})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)



# Назначение ученика на слот
@csrf_exempt
@login_required
def assign_student_to_slot(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    try:
        data = json.loads(request.body)
        slot_id = data.get("slot_id")
        student_id = data.get("student_id")

        slot = get_object_or_404(TeacherAvailability, id=slot_id)
        student = get_object_or_404(CustomUser, id=student_id, role="student")

        # Проверка: только учитель слота может назначить ученика
        if request.user != slot.teacher:
            return JsonResponse({"success": False, "error": "Нет доступа"}, status=403)

        if slot.is_booked:
            return JsonResponse({"success": False, "error": "Слот уже занят"})

        subject = getattr(slot.teacher, "desired_subject", None)
        if not subject:
            return JsonResponse({"success": False, "error": "У преподавателя не назначен предмет"})

        lesson = Lesson.objects.create(
            subject=subject,
            teacher=slot.teacher,
            student=student,
            date=slot.date,
            time=slot.time,
            duration_minutes=slot.duration_minutes
        )

        slot.is_booked = True
        slot.save()

        return JsonResponse({
            "success": True,
            "lesson_id": lesson.id,
            "student_name": student.get_full_name() or student.username
        })

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)



# Удаление свободного слота
# ---------------------------------------------
# Удаление свободного слота
# ---------------------------------------------
@csrf_exempt
@login_required
def delete_free_slot(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    try:
        data = json.loads(request.body)
        slot_id = data.get("slot_id")

        slot = get_object_or_404(TeacherAvailability, id=slot_id)

        # Только владелец слота может удалять
        if request.user != slot.teacher:
            return JsonResponse({"success": False, "error": "Нет доступа"}, status=403)

        # Если слот был забронирован — удаляем урок
        if slot.is_booked:
            Lesson.objects.filter(
                teacher=slot.teacher,
                date=slot.date,
                time=slot.time
            ).delete()

        slot.delete()
        return JsonResponse({"success": True})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)

# Получение всех учеников
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required

@login_required
def get_students(request):
    if request.user.role != 'teacher':
        return JsonResponse({"success": False, "error": "Доступ запрещён"}, status=403)

    # Получаем только учеников, которые закреплены за текущим учителем
    students = request.user.students.all().values("id", "first_name", "last_name", "username")

    return JsonResponse({
        "success": True,
        "students": [
            {
                "id": s["id"],
                "name": (s["first_name"] + " " + s["last_name"]).strip() or s["username"]
            }
            for s in students
        ]
    })
# views.py
@login_required
def get_calendar_events(request):
    if request.user.role != "teacher":
        return JsonResponse([], safe=False)

    slots = TeacherAvailability.objects.filter(teacher=request.user)

    events = []
    for slot in slots:
        if slot.is_booked:
            # ищем урок
            lesson = Lesson.objects.filter(
                teacher=slot.teacher,
                date=slot.date,
                time=slot.time
            ).first()
            events.append({
                "id": f"lesson-{lesson.id}" if lesson else f"slot-{slot.id}",
                "title": f"Урок: {lesson.student.get_full_name() if lesson else 'занято'}",
                "start": f"{slot.date}T{slot.time}",
                "end": f"{slot.date}T{slot.time}",
                "color": "orange",
                "extendedProps": {
                    "type": "lesson",
                    "lesson_id": lesson.id if lesson else None,
                    "slot_id": slot.id
                }
            })
        else:
            events.append({
                "id": f"slot-{slot.id}",
                "title": "Свободно",
                "start": f"{slot.date}T{slot.time}",
                "end": f"{slot.date}T{slot.time}",
                "color": "green",
                "extendedProps": {
                    "type": "slot",
                    "slot_id": slot.id
                }
            })

    return JsonResponse(events, safe=False)



@csrf_exempt
@login_required
def delete_lesson(request):
    if request.method != "POST":
        return JsonResponse({"success": False}, status=400)

    try:
        data = json.loads(request.body)
        lesson_id = data.get("lesson_id")

        lesson = get_object_or_404(Lesson, id=lesson_id, teacher=request.user)

        # Найдём слот
        slot = TeacherAvailability.objects.filter(
            teacher=lesson.teacher,
            date=lesson.date,
            time=lesson.time
        ).first()

        # Если слот есть — освободим
        if slot:
            slot.is_booked = False
            slot.save()
        else:
            # если слота нет — создадим
            slot = TeacherAvailability.objects.create(
                teacher=lesson.teacher,
                date=lesson.date,
                time=lesson.time,
                duration_minutes=lesson.duration_minutes,
                is_booked=False
            )

        lesson.delete()

        return JsonResponse({"success": True, "slot_id": slot.id})

    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)}, status=500)
@login_required
def student_profile_view(request, student_id):
    from .models import CustomUser
    student = get_object_or_404(CustomUser, id=student_id, role='student')
    return render(request, 'accounts/student_profile.html', {'student': student})
