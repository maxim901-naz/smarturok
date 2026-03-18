from django.db import models
from django.db.models import Q
from django.conf import settings
from accounts.models import Subject, CustomUser, Lesson

class LessonBooking(models.Model):
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='booked_lessons', verbose_name='Ученик')
    teacher = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='lessons_to_teach', verbose_name='Преподаватель')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, verbose_name='Предмет')
    date = models.DateField(verbose_name='Дата')
    time = models.TimeField(verbose_name='Время')
    is_recurring = models.BooleanField(default=False, verbose_name='Регулярный урок')
    is_confirmed = models.BooleanField(default=False, verbose_name='Подтверждено преподавателем')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Когда забронировали')

    def __str__(self):
        return f"{self.student} → {self.teacher} [{self.subject}] {self.date} {self.time}"

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

# 
class TeacherAvailability(models.Model):
    teacher = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'role': 'teacher'},
        related_name='available_slots'
    )
    date = models.DateField(null=True, blank=True)  # для разового слота
    weekday = models.IntegerField(
        choices=[(i, day) for i, day in enumerate(['Пн','Вт','Ср','Чт','Пт','Сб','Вс'])],
        null=True,
        blank=True
    )  # для регулярного слота
    time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    is_recurring = models.BooleanField(default=False)
    is_booked = models.BooleanField(default=False)

    class Meta:
        ordering = ['date', 'time']
        constraints = [
            models.UniqueConstraint(
                fields=['teacher', 'date', 'time'],
                condition=Q(is_recurring=False),
                name='unique_one_time_slot'
            ),
            models.UniqueConstraint(
                fields=['teacher', 'weekday', 'time'],
                condition=Q(is_recurring=True),
                name='unique_recurring_slot'
            ),
        ]

    def get_display_text(self, specific_date=None):
        """
        Возвращает читаемое представление слота.
        Для регулярных слотов можно указать конкретную дату.
        """
        from django.utils.formats import date_format
        
        if self.is_recurring:
            if specific_date:
                return f"{specific_date.strftime('%d.%m.%Y')} ({self.get_weekday_display()}) {self.time.strftime('%H:%M')}"
            return f"Каждый {self.get_weekday_display()} в {self.time.strftime('%H:%M')}"
        else:
            return f"{self.date.strftime('%d.%m.%Y')} {self.time.strftime('%H:%M')}"
    
    def __str__(self):
        return self.get_display_text()

    def clean(self):
        if self.is_recurring:
            if self.weekday is None:
                raise models.ValidationError('Для регулярного слота нужен день недели.')
            if self.date is not None:
                raise models.ValidationError('У регулярного слота дата должна быть пустой.')
        else:
            if self.date is None:
                raise models.ValidationError('Для разового слота нужна дата.')
            if self.weekday is not None:
                raise models.ValidationError('У разового слота weekday должен быть пустым.')
    def get_english_weekday(self):
        """Возвращает день недели на английском для совместимости с Lesson"""
        weekday_map = {
            0: 'Monday',
            1: 'Tuesday', 
            2: 'Wednesday',
            3: 'Thursday',
            4: 'Friday',
            5: 'Saturday',
            6: 'Sunday'
        }
        return weekday_map.get(self.weekday, 'Monday')

