from django.db import models

from django.contrib.auth.models import AbstractUser
from django.db import models
import uuid

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Ученик'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    is_approved = models.BooleanField(default=False)
    desired_subject = models.ForeignKey('Subject', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Желаемый предмет')

    teachers = models.ManyToManyField(
        'self',
        limit_choices_to={'role': 'teacher'},
        symmetrical=False,
        related_name='students',
        blank=True,
        verbose_name="Закреплённые учителя"
    )

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

def is_active_for_login(self):
    if self.role == 'teacher':
        return self.is_approved
    return True


class Subject(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class Lesson(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    teacher = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='lessons_as_teacher')
    student = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='lessons_as_student')
    date = models.DateField()
    time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)

    # 💬 Новое поле для ссылки на видеозвонок
    video_url = models.URLField(blank=True, null=True, verbose_name="Ссылка на видеосвязь")
    
    # 🆕 Новые поля
    topic = models.CharField(max_length=255, blank=True, null=True, verbose_name="Тема урока")
    homework = models.TextField(blank=True, null=True, verbose_name="Домашнее задание")
    teacher_notes = models.TextField(blank=True, null=True, verbose_name="Комментарии преподавателя")
    homework_file = models.FileField(upload_to='homework_files/', blank=True, null=True, verbose_name="Файл для ДЗ")

    # ответ ученика
    

    def save(self, *args, **kwargs):
        if not self.video_url:
            self.video_url = f"https://meet.jit.si/maxschool-{uuid.uuid4()}"
        super().save(*args, **kwargs)


    def __str__(self):
        return f"{self.subject} | {self.student.username} с {self.teacher.username} — {self.date} {self.time}"
class TrialRequest(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    preferred_time = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    assigned_teacher = models.ForeignKey(
        CustomUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        limit_choices_to={'role': 'teacher'}
    )

    is_converted = models.BooleanField(default=False)  # назначен ли урок

    def __str__(self):
        return f"{self.name} ({self.subject})"
class TeacherApplication(models.Model):
    name = models.CharField("ФИО", max_length=100)
    email = models.EmailField("Email")
    phone = models.CharField("Телефон", max_length=20)
    specialization = models.CharField("Предмет/Специализация", max_length=100)
    experience = models.TextField("Опыт работы")
    motivation = models.TextField("Почему хотите работать у нас?")
    submitted_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.specialization})"