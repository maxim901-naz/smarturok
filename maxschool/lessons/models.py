from django.db import models
from django.db.models import Q
from django.conf import settings
from django.core.exceptions import ValidationError
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


class LessonDeck(models.Model):
    """Готовый комплект карточек для правой панели урока."""

    subject = models.ForeignKey(
        Subject,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_decks',
        verbose_name='Предмет',
    )
    grade = models.PositiveSmallIntegerField(null=True, blank=True, verbose_name='Класс')
    title = models.CharField(max_length=180, verbose_name='Название урока')
    topic = models.CharField(max_length=180, blank=True, default='', verbose_name='Тема')
    description = models.TextField(blank=True, default='', verbose_name='Краткое описание')
    sort_order = models.PositiveIntegerField(default=0, verbose_name='Порядок')
    is_active = models.BooleanField(default=True, verbose_name='Активный комплект')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['subject__name', 'grade', 'sort_order', 'title']
        indexes = [
            models.Index(fields=['is_active', 'subject', 'grade'], name='less_deck_active_subj_grade'),
            models.Index(fields=['sort_order', 'title'], name='less_deck_sort_title'),
        ]
        verbose_name = 'Комплект карточек урока'
        verbose_name_plural = 'Комплекты карточек уроков'

    def __str__(self):
        parts = []
        if self.subject_id:
            parts.append(str(self.subject))
        if self.grade:
            parts.append(f'{self.grade} класс')
        parts.append(self.title)
        return ' · '.join(parts)


class LessonCard(models.Model):
    CARD_TYPE_CHOICES = (
        ('title', 'Заставка'),
        ('theory', 'Теория'),
        ('example', 'Пример'),
        ('task', 'Задание'),
        ('hint', 'Подсказка'),
        ('answer', 'Ответ'),
        ('question', 'Вопрос'),
        ('homework', 'Домашнее задание'),
        ('image', 'Картинка'),
        ('video', 'Видео'),
    )

    deck = models.ForeignKey(
        LessonDeck,
        on_delete=models.CASCADE,
        related_name='cards',
        verbose_name='Комплект',
    )
    order = models.PositiveIntegerField(default=1, verbose_name='Номер карточки')
    card_type = models.CharField(max_length=16, choices=CARD_TYPE_CHOICES, default='task', verbose_name='Тип')
    title = models.CharField(max_length=180, blank=True, default='', verbose_name='Заголовок')
    body = models.TextField(blank=True, default='', verbose_name='Текст карточки')
    image = models.ImageField(upload_to='lesson_cards/images/%Y/%m/', blank=True, null=True, verbose_name='Изображение')
    attachment = models.FileField(upload_to='lesson_cards/files/%Y/%m/', blank=True, null=True, verbose_name='Файл')
    video_url = models.URLField(blank=True, default='', verbose_name='Ссылка на видео')
    teacher_notes = models.TextField(blank=True, default='', verbose_name='Заметки для учителя')
    is_active = models.BooleanField(default=True, verbose_name='Показывать в уроке')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['deck', 'order', 'id']
        indexes = [
            models.Index(fields=['deck', 'order'], name='less_card_deck_order'),
            models.Index(fields=['card_type', 'is_active'], name='less_card_type_active'),
        ]
        verbose_name = 'Карточка урока'
        verbose_name_plural = 'Карточки урока'

    def __str__(self):
        return f'{self.deck} · {self.order}. {self.title or self.get_card_type_display()}'


class LessonDeckSession(models.Model):
    """Какой комплект и какая карточка сейчас открыты в конкретном уроке."""

    lesson = models.OneToOneField(
        Lesson,
        on_delete=models.CASCADE,
        related_name='deck_session',
        verbose_name='Урок',
    )
    deck = models.ForeignKey(
        LessonDeck,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lesson_sessions',
        verbose_name='Выбранный комплект',
    )
    current_card = models.ForeignKey(
        LessonCard,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='active_lesson_sessions',
        verbose_name='Текущая карточка',
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_lesson_card_sessions',
        verbose_name='Кто изменил',
    )
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Карточки в уроке'
        verbose_name_plural = 'Карточки в уроках'

    def clean(self):
        if self.current_card_id and self.deck_id and self.current_card.deck_id != self.deck_id:
            raise ValidationError('Текущая карточка должна относиться к выбранному комплекту.')

    def __str__(self):
        return f'{self.lesson} · {self.deck or "без комплекта"}'


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

