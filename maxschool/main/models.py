import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.text import slugify


class Review(models.Model):
    name = models.CharField(max_length=120)
    text = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5)
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.rating}/5)"


class HomeSuccessStory(models.Model):
    name = models.CharField(max_length=120)
    achievement = models.CharField(max_length=180)
    story_text = models.TextField()
    image = models.ImageField(upload_to='home_success/', blank=True, null=True)
    cta_text = models.CharField(max_length=80, blank=True, default='Подробнее')
    cta_url = models.CharField(max_length=300, blank=True, default='')
    sort_order = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', '-created_at']

    def __str__(self):
        return self.name


class MaterialCategory(models.Model):
    title = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'title']

    def __str__(self):
        return self.title


class MaterialItem(models.Model):
    CONTENT_TYPE_CHOICES = (
        ('video', 'Видео'),
        ('article', 'Статья (Markdown)'),
        ('pdf', 'PDF/файл'),
        ('test', 'Тест'),
    )
    STATUS_CHOICES = (
        ('draft', 'Черновик'),
        ('review', 'На проверке'),
        ('published', 'Опубликовано'),
        ('archived', 'В архиве'),
    )
    ACCESS_LEVEL_CHOICES = (
        ('public', 'Доступно всем'),
        ('authenticated', 'Только авторизованным'),
        ('paid', 'Только оплатившим пакет'),
    )
    EXAM_TYPE_CHOICES = (
        ('general', 'Обычный материал'),
        ('oge', 'ОГЭ'),
        ('ege', 'ЕГЭ'),
        ('school', 'Школьная работа'),
        ('custom', 'Произвольный формат'),
    )

    category = models.ForeignKey(MaterialCategory, on_delete=models.CASCADE, related_name='materials')
    title = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True, null=True, allow_unicode=True)
    description = models.TextField(blank=True)
    seo_title = models.CharField(
        max_length=90,
        blank=True,
        default='',
        help_text='Search title. Leave empty to use the material title.',
    )
    seo_focus_query = models.CharField(
        max_length=160,
        blank=True,
        default='',
        help_text='Internal note: main search query for this material.',
    )
    meta_description = models.CharField(max_length=160, blank=True)
    faq_items = models.TextField(
        blank=True,
        default='',
        help_text='Optional FAQ. One question per line: Question | Answer.',
    )
    subject = models.ForeignKey('accounts.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=16, choices=CONTENT_TYPE_CHOICES, default='pdf', db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='published', db_index=True)
    access_level = models.CharField(max_length=16, choices=ACCESS_LEVEL_CHOICES, default='public', db_index=True)
    exam_type = models.CharField(max_length=16, choices=EXAM_TYPE_CHOICES, default='general', db_index=True)
    task_number = models.PositiveSmallIntegerField(null=True, blank=True, db_index=True)
    video_url = models.URLField(blank=True)
    article_markdown = models.TextField(blank=True)
    file = models.FileField(upload_to='materials/', blank=True, null=True)
    external_url = models.URLField(blank=True)
    test_payload = models.JSONField(blank=True, null=True)
    related_theory = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='practice_materials',
        limit_choices_to={'content_type__in': ('article', 'video', 'pdf')},
    )
    related_test = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='theory_materials',
        limit_choices_to={'content_type': 'test'},
    )
    views_count = models.PositiveIntegerField(default=0, db_index=True)
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'content_type']),
            models.Index(fields=['exam_type', 'created_at']),
            models.Index(fields=['published_at']),
        ]

    def __str__(self):
        return self.title

    def _build_unique_slug(self):
        base_slug = slugify(self.title, allow_unicode=True) or ''
        if not base_slug:
            base_slug = f'material-{self.pk}' if self.pk else f'material-{uuid.uuid4().hex[:8]}'

        slug_candidate = base_slug
        suffix = 2
        while type(self).objects.exclude(pk=self.pk).filter(slug=slug_candidate).exists():
            slug_candidate = f'{base_slug}-{suffix}'
            suffix += 1
        return slug_candidate

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._build_unique_slug()

        if self.status == 'published':
            self.is_published = True
            if not self.published_at:
                self.published_at = timezone.now()
        else:
            self.is_published = False

        super().save(*args, **kwargs)


class MaterialImage(models.Model):
    USAGE_CHOICES = (
        ('article', 'Article'),
        ('test', 'Test'),
        ('both', 'Article and test'),
    )

    material = models.ForeignKey(MaterialItem, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='materials/images/%Y/%m/')
    title = models.CharField(max_length=120, blank=True)
    alt_text = models.CharField(max_length=255, blank=True)
    usage = models.CharField(max_length=16, choices=USAGE_CHOICES, default='both', db_index=True)
    sort_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sort_order', 'id']

    def __str__(self):
        return self.title or self.image.name

    @property
    def markdown_snippet(self):
        if not self.image:
            return ''
        alt = self.alt_text or self.title or 'image'
        return f'![{alt}]({self.image.url})'

    @property
    def test_json_snippet(self):
        if not self.image:
            return ''
        alt = (self.alt_text or self.title or '').replace('"', '\\"')
        return f'"image_url": "{self.image.url}", "image_alt": "{alt}"'


class MaterialTestAttempt(models.Model):
    material = models.ForeignKey(
        MaterialItem,
        on_delete=models.CASCADE,
        related_name='test_attempts',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='material_test_attempts',
    )
    session_key = models.CharField(max_length=64, blank=True, default='')
    attempt_no = models.PositiveIntegerField(default=1)
    max_points = models.PositiveIntegerField(default=0)
    score_points = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    score_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    passed = models.BooleanField(default=False)
    duration_seconds = models.PositiveIntegerField(default=0)
    answers_payload = models.JSONField(default=dict, blank=True)
    result_payload = models.JSONField(default=dict, blank=True)
    started_at = models.DateTimeField(default=timezone.now)
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        indexes = [
            models.Index(fields=['material', 'submitted_at'], name='main_mtat_mat_sub_idx'),
            models.Index(fields=['user', 'submitted_at'], name='main_mtat_usr_sub_idx'),
            models.Index(fields=['material', 'user', 'attempt_no'], name='main_mtat_mat_usr_no_idx'),
        ]

    def __str__(self):
        user_part = self.user.username if self.user_id else 'guest'
        return f'{self.material.title} | {user_part} | attempt #{self.attempt_no}'


class MaterialTest(models.Model):
    material = models.OneToOneField(
        MaterialItem,
        on_delete=models.CASCADE,
        related_name='test_bank',
    )
    title = models.CharField(max_length=180, blank=True, default='')
    passing_score_percent = models.PositiveSmallIntegerField(default=70)
    duration_minutes = models.PositiveIntegerField(default=0)
    show_correct_after_submit = models.BooleanField(default=True)
    shuffle_questions = models.BooleanField(default=False)
    shuffle_options = models.BooleanField(default=False)
    max_attempts = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'Test for {self.material.title}'


class MaterialTestQuestion(models.Model):
    QUESTION_TYPE_CHOICES = (
        ('single', 'Single choice'),
        ('multiple', 'Multiple choice'),
        ('text', 'Text answer'),
        ('number', 'Number answer'),
    )

    test = models.ForeignKey(
        MaterialTest,
        on_delete=models.CASCADE,
        related_name='questions',
    )
    code = models.CharField(max_length=40, blank=True, default='')
    prompt = models.TextField()
    image = models.ImageField(upload_to='materials/tests/questions/', blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True, default='')
    question_type = models.CharField(max_length=12, choices=QUESTION_TYPE_CHOICES, default='text')
    points = models.PositiveIntegerField(default=1)
    required = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    explanation = models.TextField(blank=True, default='')
    placeholder = models.CharField(max_length=160, blank=True, default='')
    case_sensitive = models.BooleanField(default=False)
    correct_text = models.TextField(
        blank=True,
        default='',
        help_text='For text questions: one acceptable answer per line.',
    )
    correct_number = models.DecimalField(max_digits=12, decimal_places=4, null=True, blank=True)
    number_tolerance = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['test', 'code'], name='main_mtq_test_code_uniq'),
        ]
        indexes = [
            models.Index(fields=['test', 'order'], name='main_mtq_test_order_idx'),
            models.Index(fields=['question_type', 'is_active'], name='main_mtq_type_act_idx'),
        ]

    def __str__(self):
        code = self.code or f'q{self.pk}'
        return f'{self.test} · {code}'

    def save(self, *args, **kwargs):
        if not self.code:
            self.code = f'q-{uuid.uuid4().hex[:8]}'
        super().save(*args, **kwargs)


class MaterialTestOption(models.Model):
    question = models.ForeignKey(
        MaterialTestQuestion,
        on_delete=models.CASCADE,
        related_name='options',
    )
    value = models.CharField(max_length=140)
    label = models.CharField(max_length=255)
    image = models.ImageField(upload_to='materials/tests/options/', blank=True, null=True)
    image_alt = models.CharField(max_length=255, blank=True, default='')
    is_correct = models.BooleanField(default=False)
    order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['order', 'id']
        constraints = [
            models.UniqueConstraint(fields=['question', 'value'], name='main_mto_q_val_uniq'),
        ]
        indexes = [
            models.Index(fields=['question', 'order'], name='main_mto_q_order_idx'),
        ]

    def __str__(self):
        return f'{self.question} · {self.label}'
