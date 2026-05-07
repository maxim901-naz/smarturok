import uuid

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
    meta_description = models.CharField(max_length=160, blank=True)
    subject = models.ForeignKey('accounts.Subject', on_delete=models.SET_NULL, null=True, blank=True)
    grade = models.PositiveSmallIntegerField(null=True, blank=True)
    content_type = models.CharField(max_length=16, choices=CONTENT_TYPE_CHOICES, default='pdf', db_index=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default='published', db_index=True)
    access_level = models.CharField(max_length=16, choices=ACCESS_LEVEL_CHOICES, default='public', db_index=True)
    exam_type = models.CharField(max_length=16, choices=EXAM_TYPE_CHOICES, default='general', db_index=True)
    video_url = models.URLField(blank=True)
    article_markdown = models.TextField(blank=True)
    file = models.FileField(upload_to='materials/', blank=True, null=True)
    external_url = models.URLField(blank=True)
    test_payload = models.JSONField(blank=True, null=True)
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
