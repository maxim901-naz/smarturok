from django.urls import path

from .views import student_cancel_lesson_view, student_upcoming_lessons_view, student_balance_view, teacher_finance_view, update_lesson_status, balance_topup_request_view, student_vacation_request_view, teacher_homework_submissions_view, submit_homework_view, my_homeworks_view, lesson_feedback_view, teacher_lesson_history_view, register_view, dashboard_router_view, login_view, teacher_dashboard_view, logout_view, trial_lesson_view, my_schedule_view, teacher_application_view, student_dashboard_view, lesson_history_view, student_mark_notifications_read_view, teacher_mark_notifications_read_view, verify_email_view

urlpatterns = [
    path('student/lesson/<int:lesson_id>/cancel/', student_cancel_lesson_view, name='student_cancel_lesson'),
    path('student/upcoming/', student_upcoming_lessons_view, name='student_upcoming_lessons'),
    path('student/vacation/', student_vacation_request_view, name='student_vacation_request'),
    path('student/balance/', student_balance_view, name='student_balance'),
    path('teacher/finance/', teacher_finance_view, name='teacher_finance'),
    path('teacher/lesson/<int:lesson_id>/status/', update_lesson_status, name='update_lesson_status'),
    path('student/balance/topup/', balance_topup_request_view, name='balance_topup_request'),
    path('', register_view, name='accounts-home'),
    path('register/', register_view, name='register'),
    path('verify-email/<uidb64>/<token>/', verify_email_view, name='verify_email'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('trial/', trial_lesson_view, name='trial'),
    path('schedule/', my_schedule_view, name='my_schedule'),
     path('vacancy/', teacher_application_view, name='teacher_application'),
     path('student/dashboard/', student_dashboard_view, name='student_dashboard'),
     path('teacher/dashboard/', teacher_dashboard_view, name='teacher_dashboard'),
    path('dashboard/', dashboard_router_view, name='dashboard'),
     path('student/history/', lesson_history_view, name='lesson_history'),
     path('teacher/history/', teacher_lesson_history_view, name='teacher_lesson_history'),
     path('teacher/lesson/<int:lesson_id>/feedback/', lesson_feedback_view, name='lesson_feedback'),
    path('student/homeworks/', my_homeworks_view, name='my_homeworks'),
    path('student/homeworks/<int:lesson_id>/submit/', submit_homework_view, name='submit_homework'),
    path('student/notifications/read/', student_mark_notifications_read_view, name='student_notifications_read'),
    path('teacher/notifications/read/', teacher_mark_notifications_read_view, name='teacher_notifications_read'),


]
urlpatterns += [
    path('teacher/homeworks/', teacher_homework_submissions_view, name='teacher_homework_submissions'),
]
