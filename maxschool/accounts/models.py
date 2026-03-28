from django.conf import settings
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.text import slugify
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import uuid

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('student', 'Ученик'),
        ('teacher', 'Преподаватель'),
        ('admin', 'Администратор'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='student')
    email = models.EmailField('email address', unique=True, blank=False)
    is_email_verified = models.BooleanField(default=True, verbose_name='Email подтвержден')
    is_approved = models.BooleanField(default=False)
    desired_subject = models.ForeignKey('Subject', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Желаемый предмет')
    subjects_taught = models.ManyToManyField('Subject', blank=True, related_name='teachers', verbose_name='Преподаваемые предметы')
    photo = models.ImageField(upload_to='photos/', blank=True, null=True)
    balance = models.IntegerField(default=0)
    time_zone = models.CharField(max_length=64, default='Europe/Moscow', verbose_name='Часовой пояс')
    teacher_payout_percent = models.PositiveSmallIntegerField(
        default=50,
        verbose_name='Teacher payout percent, %',
        help_text='Teacher payout as percent of student lesson price if fixed payout is empty.',
    )
    teacher_payout_fixed = models.PositiveIntegerField(
        null=True,
        blank=True,
        verbose_name='Teacher fixed payout per lesson',
        help_text='If set, this value is used instead of payout percent.',
    )
    # Публичный профиль преподавателя (редактируется из админки).
    experience_years = models.PositiveSmallIntegerField(default=5, verbose_name='Опыт (лет)')
    students_count = models.PositiveIntegerField(default=50, verbose_name='Количество учеников')
    success_rate = models.PositiveSmallIntegerField(default=95, verbose_name='Успешных работ (%)')
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=5.0, verbose_name='Рейтинг')
    reviews_count = models.PositiveIntegerField(default=24, verbose_name='Количество отзывов')
    bio = models.TextField(blank=True, default='', verbose_name='О преподавателе')
    education = models.TextField(blank=True, default='', verbose_name='Образование')
    methodology = models.TextField(blank=True, default='', verbose_name='Методика преподавания')
    achievements = models.TextField(blank=True, default='', verbose_name='Достижения')

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

    def save(self, *args, **kwargs):
        if self.email:
            self.email = self.email.strip().lower()
        super().save(*args, **kwargs)


    def get_primary_subject(self):
        subj = self.subjects_taught.first()
        return subj or self.desired_subject

    def get_subjects_display(self):
        subjects = list(self.subjects_taught.all())
        if subjects:
            return ', '.join(s.name for s in subjects)
        return self.desired_subject.name if self.desired_subject else ''

    def get_tz_name(self):
        if self.role == 'teacher':
            return 'Europe/Moscow'
        return self.time_zone or 'Europe/Moscow'

    def calculate_lesson_payout(self, lesson_price):
        base_price = int(lesson_price or 0)
        fixed_payout = int(self.teacher_payout_fixed or 0)
        if fixed_payout > 0:
            return fixed_payout

        payout_percent = int(self.teacher_payout_percent or 0)
        payout_percent = max(0, min(100, payout_percent))
        return int(round(base_price * payout_percent / 100))

class BalanceTransaction(models.Model):
    DIRECTION_CHOICES = (
        ('credit', 'Пополнение'),
        ('debit', 'Списание'),
    )
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='balance_transactions')
    lesson = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='balance_transactions')
    direction = models.CharField(max_length=10, choices=DIRECTION_CHOICES)
    amount = models.PositiveIntegerField()
    note = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} {self.direction} {self.amount}"

class BalanceTopUpRequest(models.Model):
    PACKAGE_CHOICES = (
        (4, '4 урока'),
        (8, '8 уроков'),
        (12, '12 уроков'),
    )
    STATUS_CHOICES = (
        ('pending', 'Ожидает'),
        ('approved', 'Одобрено'),
        ('rejected', 'Отклонено'),
    )
    WORK_STATUS_CHOICES = (
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('done', 'Закрыта'),
        ('rejected', 'Отклонена'),
    )

    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='balance_topup_requests')
    package = models.PositiveIntegerField(choices=PACKAGE_CHOICES)
    comment = models.CharField(max_length=255, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')
    work_status = models.CharField(max_length=20, choices=WORK_STATUS_CHOICES, default='new', db_index=True)
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_topup_requests',
        limit_choices_to={'is_staff': True},
    )
    first_response_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user} → {self.package} ({self.get_status_display()})"

    def is_sla_overdue(self, response_minutes=5):
        if self.work_status != 'new':
            return False
        if not self.created_at:
            return False
        return timezone.now() >= (self.created_at + timedelta(minutes=response_minutes))


class TeacherFinanceEntry(models.Model):
    STATUS_CHOICES = (
        ('accrued', 'Начислено'),
        ('paid', 'Выплачено'),
    )
    teacher = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='finance_entries')
    lesson = models.ForeignKey('Lesson', on_delete=models.SET_NULL, null=True, blank=True, related_name='finance_entries')
    subject_name = models.CharField(max_length=255, blank=True, default="")
    student_name = models.CharField(max_length=255, blank=True, default="")
    lesson_date = models.DateField(null=True, blank=True)
    lesson_time = models.TimeField(null=True, blank=True)
    lesson_status = models.CharField(max_length=20, blank=True, default="")
    amount = models.PositiveIntegerField(default=0)
    payout_status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='accrued')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher} {self.amount}"

class TeacherNotification(models.Model):
    teacher = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.teacher} — {self.message[:30]}"


class StudentNotification(models.Model):
    student = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='student_notifications')
    message = models.CharField(max_length=255)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.student} — {self.message[:30]}"


class StudentVacation(models.Model):
    student = models.ForeignKey(
        'CustomUser',
        on_delete=models.CASCADE,
        related_name='vacations',
        limit_choices_to={'role': 'student'},
        verbose_name='Ученик',
    )
    start_date = models.DateField(verbose_name='Дата начала')
    end_date = models.DateField(verbose_name='Дата окончания')
    comment = models.CharField(max_length=255, blank=True, verbose_name='Комментарий')
    created_by = models.ForeignKey(
        'CustomUser',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_vacations',
        verbose_name='Кто создал',
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Создано')
    applied_at = models.DateTimeField(null=True, blank=True, verbose_name='Применено')
    affected_lessons_count = models.PositiveIntegerField(default=0, verbose_name='Снято уроков')

    class Meta:
        ordering = ('-created_at',)
        verbose_name = 'Отпуск ученика'
        verbose_name_plural = 'Отпуска учеников'

    def __str__(self):
        return f"{self.student} ({self.start_date} — {self.end_date})"

    def clean(self):
        super().clean()
        if self.start_date and self.end_date and self.start_date > self.end_date:
            raise ValidationError({'end_date': 'Дата окончания не может быть раньше даты начала.'})

        if self.start_date and not self.applied_at:
            tomorrow = timezone.localdate() + timedelta(days=1)
            if self.start_date < tomorrow:
                raise ValidationError({'start_date': 'Отпуск можно поставить только со следующего дня.'})

    def apply_vacation(self):
        if self.applied_at:
            return self.affected_lessons_count

        from lessons.models import TeacherAvailability, LessonBooking

        lessons = list(
            Lesson.objects
            .filter(
                student=self.student,
                date__gte=self.start_date,
                date__lte=self.end_date,
            )
            .select_related('teacher', 'subject')
        )

        teacher_counts = {}
        lesson_ids = []
        for lesson in lessons:
            lesson_ids.append(lesson.id)
            teacher_counts[lesson.teacher_id] = {
                'teacher': lesson.teacher,
                'count': teacher_counts.get(lesson.teacher_id, {}).get('count', 0) + 1,
            }
            slot, created = TeacherAvailability.objects.get_or_create(
                teacher=lesson.teacher,
                date=lesson.date,
                time=lesson.time,
                defaults={
                    'duration_minutes': lesson.duration_minutes or 30,
                    'is_booked': False,
                    'is_recurring': False,
                }
            )
            if not created and slot.is_booked:
                slot.is_booked = False
                slot.save(update_fields=['is_booked'])

        if lesson_ids:
            Lesson.objects.filter(id__in=lesson_ids).delete()
            LessonBooking.objects.filter(
                student=self.student,
                date__gte=self.start_date,
                date__lte=self.end_date,
                is_recurring=False,
            ).delete()

            StudentNotification.objects.create(
                student=self.student,
                message=(
                    f"Отпуск оформлен на период {self.start_date:%d.%m.%Y} — {self.end_date:%d.%m.%Y}. "
                    f"Снято уроков: {len(lesson_ids)}."
                ),
            )

            student_name = self.student.get_full_name() or self.student.username
            for item in teacher_counts.values():
                teacher = item['teacher']
                TeacherNotification.objects.create(
                    teacher=teacher,
                    message=(
                        f"У ученика {student_name} отпуск "
                        f"{self.start_date:%d.%m.%Y} — {self.end_date:%d.%m.%Y}. "
                        f"Снято уроков: {item['count']}."
                    ),
                )

        self.applied_at = timezone.now()
        self.affected_lessons_count = len(lesson_ids)
        self.save(update_fields=['applied_at', 'affected_lessons_count'])
        return self.affected_lessons_count




def is_active_for_login(self):
    if self.role == 'teacher':
        return self.is_approved
    return True


class Subject(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=150, unique=True, blank=True, null=True, allow_unicode=True)
    price_per_lesson = models.PositiveIntegerField(default=0)
    image = models.ImageField(upload_to='subjects/', blank=True, null=True)
    landing_image = models.ImageField(upload_to='subjects/landing/', blank=True, null=True)
    hero_title = models.CharField(max_length=160, blank=True)
    hero_subtitle = models.TextField(blank=True)
    landing_description = models.TextField(blank=True)
    metrics = models.TextField(
        blank=True,
        help_text='Каждая строка: Заголовок|Значение. Пример: Формат|Индивидуально 1:1',
    )
    results_title = models.CharField(max_length=160, blank=True, default='Почему этот курс дает результат')
    result_points = models.TextField(
        blank=True,
        help_text='Каждая строка: Заголовок|Описание.',
    )
    include_items_title = models.CharField(max_length=160, blank=True, default='Что входит в обучение')
    include_items = models.TextField(blank=True, help_text='Каждый пункт с новой строки.')
    benefits_title = models.CharField(max_length=160, blank=True, default='Чему научится ученик')
    benefits = models.TextField(blank=True, help_text='Каждый пункт с новой строки.')
    program_title = models.CharField(max_length=160, blank=True, default='Программа обучения')
    program = models.TextField(blank=True, help_text='Каждый модуль с новой строки.')
    progress_title = models.CharField(max_length=160, blank=True, default='Что меняется уже в первые 2-4 недели')
    progress_subtitle = models.TextField(blank=True)
    progress_cards = models.TextField(
        blank=True,
        help_text='Каждая строка: Заголовок|Акцент|Описание.',
    )
    seo_title = models.CharField(max_length=160, blank=True)
    seo_description = models.CharField(max_length=255, blank=True)
    discount_4 = models.PositiveIntegerField(default=0)
    discount_8 = models.PositiveIntegerField(default=0)
    discount_12 = models.PositiveIntegerField(default=0)
    discount_28 = models.PositiveIntegerField(default=0)
    discount_64 = models.PositiveIntegerField(default=0)
    discount_128 = models.PositiveIntegerField(default=0)

    def _build_unique_slug(self):
        base_slug = slugify(self.name, allow_unicode=True) or ''
        if not base_slug:
            base_slug = f'subject-{self.pk}' if self.pk else f'subject-{uuid.uuid4().hex[:8]}'

        slug_candidate = base_slug
        suffix = 2
        while type(self).objects.exclude(pk=self.pk).filter(slug=slug_candidate).exists():
            slug_candidate = f'{base_slug}-{suffix}'
            suffix += 1
        return slug_candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name



from django.db import models
from django.contrib.auth.models import AbstractUser
import uuid


LESSON_STATUS_CHOICES = (
    ('pending', 'Ожидает отметки'),
    ('conducted', 'Проведён'),
    ('missed_teacher', 'Пропущен преподавателем'),
    ('missed_student', 'Пропущен учеником'),
)

DAYS_OF_WEEK = (
    ('Monday', 'Понедельник'),
    ('Tuesday', 'Вторник'),
    ('Wednesday', 'Среда'),
    ('Thursday', 'Четверг'),
    ('Friday', 'Пятница'),
    ('Saturday', 'Суббота'),
    ('Sunday', 'Воскресенье'),
)

class Lesson(models.Model):
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='lessons_as_teacher')
    student = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='lessons_as_student')
    date = models.DateField()
    time = models.TimeField()
    duration_minutes = models.PositiveIntegerField(default=30)
    price_per_lesson = models.PositiveIntegerField(default=0)
    
    # Регулярность
    is_recurring = models.BooleanField(default=False)
    days_of_week = models.CharField(max_length=50, blank=True, null=True,
                                    help_text="Если урок регулярный, указываем дни недели через запятую, например: Monday,Wednesday")
    end_date = models.DateField(blank=True, null=True)

    video_url = models.URLField(blank=True, null=True)
    topic = models.CharField(max_length=255, blank=True, null=True)
    homework = models.TextField(blank=True, null=True)
    teacher_notes = models.TextField(blank=True, null=True)
    homework_file = models.FileField(upload_to='homework_files/', blank=True, null=True)
    lesson_status = models.CharField(max_length=20, choices=LESSON_STATUS_CHOICES, default='pending')
    is_completed = models.BooleanField(default=False)
    board_state = models.JSONField(default=dict, blank=True)
    board_state_updated_at = models.DateTimeField(null=True, blank=True)
    def save(self, *args, **kwargs):
        if not self.price_per_lesson and self.subject and getattr(self.subject, 'price_per_lesson', 0):
            self.price_per_lesson = self.subject.price_per_lesson
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.subject} | {self.student.username} с {self.teacher.username} — {self.date} {self.time}"


class TrialRequest(models.Model):
    WORK_STATUS_CHOICES = (
        ('new', 'Новая'),
        ('in_progress', 'В работе'),
        ('done', 'Закрыта'),
        ('rejected', 'Отклонена'),
    )

    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    subject = models.ForeignKey(Subject, on_delete=models.SET_NULL, null=True)
    preferred_time = models.CharField(max_length=100, blank=True)
    message = models.TextField(blank=True)
    lead_form = models.CharField(max_length=64, blank=True, default='')
    promo_interest = models.CharField(max_length=120, blank=True, default='')
    pricing_subject_name = models.CharField(max_length=120, blank=True, default='')
    pricing_lessons_count = models.PositiveIntegerField(null=True, blank=True)
    pricing_discount_percent = models.PositiveIntegerField(null=True, blank=True)
    pricing_total_price = models.PositiveIntegerField(null=True, blank=True)
    pricing_old_price = models.PositiveIntegerField(null=True, blank=True)
    personal_data_consent = models.BooleanField(default=False)
    consent_at = models.DateTimeField(null=True, blank=True)
    consent_ip = models.GenericIPAddressField(null=True, blank=True)
    consent_user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    work_status = models.CharField(max_length=20, choices=WORK_STATUS_CHOICES, default='new', db_index=True)
    assigned_admin = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_trial_requests',
        limit_choices_to={'is_staff': True},
    )
    first_response_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

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

    def is_sla_overdue(self, response_minutes=5):
        if self.work_status != 'new':
            return False
        if not self.created_at:
            return False
        return timezone.now() >= (self.created_at + timedelta(minutes=response_minutes))

class Vacancy(models.Model):
    title = models.CharField("Название вакансии", max_length=150)
    short_description = models.CharField("Краткое описание", max_length=255, blank=True)
    responsibilities = models.TextField("Обязанности", blank=True)
    requirements = models.TextField("Требования", blank=True)
    conditions = models.TextField("Условия", blank=True)
    is_active = models.BooleanField("Активна", default=True)
    order = models.PositiveSmallIntegerField("Порядок", default=0)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        ordering = ("order", "title")
        verbose_name = "Вакансия"
        verbose_name_plural = "Вакансии"

    def __str__(self):
        return self.title


class TeacherApplication(models.Model):
    vacancy = models.ForeignKey(
        Vacancy,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="applications",
        verbose_name="Вакансия",
    )
    name = models.CharField("ФИО", max_length=100)
    first_name = models.CharField("Имя", max_length=60, blank=True, default="")
    last_name = models.CharField("Фамилия", max_length=80, blank=True, default="")
    email = models.EmailField("Email")
    phone = models.CharField("Телефон", max_length=20)
    specialization = models.CharField("Предмет/специализация", max_length=100)
    years_experience = models.PositiveSmallIntegerField("Опыт (лет)", null=True, blank=True)
    experience = models.TextField("Опыт работы")
    motivation = models.TextField("Мотивация")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-submitted_at",)
        verbose_name = "Заявка преподавателя"
        verbose_name_plural = "Заявки преподавателей"

    def __str__(self):
        vacancy_title = self.vacancy.title if self.vacancy_id else self.specialization
        return f"{self.name} ({vacancy_title})"
