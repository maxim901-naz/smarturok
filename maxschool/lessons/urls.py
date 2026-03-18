from django.urls import path
from .views import add_availability_view, book_lesson_view, booking_requests_view, confirm_booking_view
from . import views

urlpatterns = [
    path('teacher/bookings/', booking_requests_view, name='teacher_bookings'),
    path('teacher/bookings/confirm/<int:booking_id>/', confirm_booking_view, name='confirm_booking'),
    path('book/<int:teacher_id>/', book_lesson_view, name='book_lesson'),
    path('availability/add/', add_availability_view, name='add_availability'),
    path('availability/', views.teacher_availability_view, name='teacher_availability'),
    path('availability/delete/<int:slot_id>/', views.delete_availability_view, name='delete_availability'),
    path('lesson/<int:lesson_id>/session/', views.lesson_session, name='lesson_session'),
    path('lesson/<int:lesson_id>/board-state/', views.lesson_board_state, name='lesson_board_state'),
    path('lesson/<int:lesson_id>/reschedule/', views.reschedule_lesson_view, name='reschedule_lesson'),

    path('select-teacher/', views.select_teacher, name='schedule_lesson'),
    # path('available-slots_in_cabinet/<int:teacher_id>/', views.available_slots, name='available_slots'),
    path('slot/<int:slot_id>/book/', views.book_lesson, name='book_lesson_in_cabinet'),

    path('my-students/', views.my_students, name='my_students'),
    path('calendar/create-slot/', views.create_free_slot, name='create_free_slot'),
    path('calendar/assign-student/', views.assign_student_to_slot, name='assign_student_to_slot'),
    path('calendar/delete-slot/', views.delete_free_slot, name='delete_free_slot'),
    path('calendar/get-students/', views.get_students, name='get_students'),
    path('calendar/delete-lesson/', views.delete_lesson, name='delete_lesson'),
    path('students/<int:student_id>/', views.student_profile_view, name='student_profile'),
    path('calendar/events/', views.get_calendar_events, name='get_calendar_events'),
]
