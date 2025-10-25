from django.urls import path

from .views import teacher_homework_submissions_view, submit_homework_view,my_homeworks_view,lesson_feedback_view,teacher_lesson_history_view,register_view,dashboard_router_view, login_view,teacher_dashboard_view,logout_view,trial_lesson_view,my_schedule_view,teacher_application_view,student_dashboard_view,lesson_history_view

urlpatterns = [
    path('', register_view, name='accounts-home'),
    path('register/', register_view, name='register'),
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


]
urlpatterns += [
    path('teacher/homeworks/', teacher_homework_submissions_view, name='teacher_homework_submissions'),
]
