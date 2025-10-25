from django.db import models
from django.conf import settings
from accounts.models import Subject, CustomUser

class LessonBooking(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='booked_lessons', verbose_name='Ученик')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lessons_to_teach', verbose_name='Преподаватель')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name='Предмет')
    date = models.DateField(verbose_name='Дата')
    time = models.TimeField(verbose_name='Время')
    is_confirmed = models.BooleanField(default=False, verbose_name='Подтверждено преподавателем')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Когда забронировали')

    def __str__(self):
        return f"{self.student} → {self.teacher} [{self.subject}] {self.date} {self.time}"
from django.db import models
from accounts.models import Lesson, CustomUser

class HomeworkSubmission(models.Model):
    lesson = models.ForeignKey(Lesson, on_delete=models.CASCADE, related_name='submissions')
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    file = models.FileField(upload_to='student_homeworks/')
    comment = models.TextField(blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)

    is_checked = models.BooleanField(default=False)  # ✅ учитель может отметить проверку

    def __str__(self):
        return f"Ответ {self.student.username} на {self.lesson.subject.name}"


# lessons/models.py

class TeacherAvailability(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='available_slots'
    )
    date = models.DateField()
    time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    is_booked = models.BooleanField(default=False)

    class Meta:
        unique_together = ('teacher', 'date', 'time')
        ordering = ['date', 'time']

    def __str__(self):
        status = "Занято" if self.is_booked else "Свободно"
        return f"{self.teacher} — {self.date} {self.time} ({status})"
