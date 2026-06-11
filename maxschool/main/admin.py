from django.contrib import admin
from django.utils.html import format_html, format_html_join, strip_tags

from .models import (
    HomeSuccessStory,
    MaterialCategory,
    MaterialImage,
    MaterialItem,
    MaterialTest,
    MaterialTestAttempt,
    MaterialTestOption,
    MaterialTestQuestion,
    Review,
)


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('name', 'rating', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating')
    search_fields = ('name', 'text')
    list_editable = ('is_published',)


@admin.register(HomeSuccessStory)
class HomeSuccessStoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'achievement', 'sort_order', 'is_published', 'created_at')
    list_filter = ('is_published',)
    search_fields = ('name', 'achievement', 'story_text')
    list_editable = ('sort_order', 'is_published')


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_active', 'sort_order')
    list_editable = ('is_active', 'sort_order')
    prepopulated_fields = {'slug': ('title',)}
    search_fields = ('title',)


@admin.register(MaterialItem)
class MaterialItemAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'slug',
        'category',
        'subject',
        'task_number',
        'content_type',
        'exam_type',
        'access_level',
        'status',
        'is_published',
        'views_count',
        'has_test_bank',
        'test_attempts_total',
        'updated_at',
    )
    list_filter = (
        'category',
        'subject',
        'grade',
        'content_type',
        'exam_type',
        'access_level',
        'status',
        'is_published',
    )
    search_fields = ('title', 'slug', 'description', 'seo_title', 'seo_focus_query', 'meta_description', 'article_markdown', 'faq_items')
    readonly_fields = (
        'is_published',
        'published_at',
        'views_count',
        'created_at',
        'updated_at',
        'seo_preview',
        'seo_checklist',
        'image_workflow_note',
    )
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'access_level')
    raw_id_fields = ('related_theory', 'related_test')

    fieldsets = (
        ('Main', {
            'fields': (
                'title',
                'slug',
                'category',
                'subject',
                'grade',
                'task_number',
                'content_type',
                'exam_type',
            )
        }),
        ('SEO', {
            'fields': (
                'seo_title',
                'seo_focus_query',
                'meta_description',
                'description',
                'faq_items',
                'seo_preview',
                'seo_checklist',
            )
        }),
        ('Content', {
            'fields': ('video_url', 'article_markdown', 'file', 'external_url', 'test_payload', 'image_workflow_note')
        }),
        ('Learning flow', {
            'fields': ('related_theory', 'related_test')
        }),
        ('Publishing and access', {
            'fields': ('status', 'access_level', 'is_published', 'published_at', 'views_count')
        }),
        ('Service', {
            'fields': ('created_at', 'updated_at')
        }),
    )

    def test_attempts_total(self, obj):
        return obj.test_attempts.count()

    def has_test_bank(self, obj):
        return MaterialTest.objects.filter(material=obj).exists()

    test_attempts_total.short_description = 'Test attempts'
    has_test_bank.short_description = 'Test bank'
    has_test_bank.boolean = True

    def _seo_title_value(self, obj):
        if not obj:
            return ''
        base_title = (obj.seo_title or obj.title or '').strip()
        if not base_title:
            return ''
        return base_title if 'SmartUrok' in base_title else f'{base_title} | SmartUrok'

    def _meta_description_value(self, obj):
        if not obj:
            return ''
        fallback = strip_tags(obj.description or '').strip()
        return (obj.meta_description or fallback or f'Материал SmartUrok: {obj.title}.').strip()[:160]

    def seo_preview(self, obj):
        if not obj:
            return 'Save the material to see SEO preview.'

        title = self._seo_title_value(obj)
        description = self._meta_description_value(obj)
        return format_html(
            '<div style="max-width: 720px; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px; background: #f8fafc;">'
            '<div style="font-size: 13px; color: #64748b; margin-bottom: 6px;">Search preview</div>'
            '<div style="font-size: 18px; color: #1a0dab; line-height: 1.25;">{}</div>'
            '<div style="font-size: 12px; color: #64748b; margin: 4px 0;">https://smarturok.ru/materials/item/{}/</div>'
            '<div style="font-size: 13px; color: #334155; line-height: 1.45;">{}</div>'
            '<div style="font-size: 12px; color: #64748b; margin-top: 8px;">Title: {} chars · Description: {} chars</div>'
            '</div>',
            title,
            obj.slug or '',
            description,
            len(title),
            len(description),
        )

    seo_preview.short_description = 'SEO preview'

    def seo_checklist(self, obj):
        if not obj:
            return 'Save the material to see SEO checklist.'

        title = self._seo_title_value(obj)
        description = self._meta_description_value(obj)
        has_content = bool(
            (obj.article_markdown or '').strip()
            or obj.file
            or obj.video_url
            or obj.external_url
            or obj.test_payload
            or MaterialTest.objects.filter(material=obj).exists()
        )
        faq_lines = [line for line in (obj.faq_items or '').splitlines() if '|' in line and line.strip()]
        checks = [
            ('URL/slug есть и не меняется после публикации', bool(obj.slug), 'Не меняйте slug у уже опубликованных материалов без необходимости.'),
            ('Материал публичный', obj.status == 'published' and obj.access_level == 'public', 'Для SEO нужны status=Опубликовано и access=Доступно всем.'),
            ('SEO title заполнен', bool((obj.seo_title or '').strip()), 'Лучше: тема + класс/экзамен + “правила/примеры/тест”.'),
            ('SEO title нормальной длины', 35 <= len(title) <= 75, 'Ориентир 35-75 символов вместе с SmartUrok.'),
            ('Meta description заполнен', bool((obj.meta_description or '').strip()), 'Кратко: что разберем, для кого, что получит ученик.'),
            ('Meta description нормальной длины', 100 <= len(description) <= 160, 'Ориентир 100-160 символов.'),
            ('Есть предмет и раздел', bool(obj.category_id and obj.subject_id), 'Помогает фильтрам, перелинковке и смыслу страницы.'),
            ('Есть класс или номер задания', bool(obj.grade or obj.task_number), 'Особенно полезно для запросов “6 класс”, “задание 1 ОГЭ”.'),
            ('Есть основной контент', has_content, 'Статья/тест/видео/PDF должны быть заполнены.'),
            ('Есть FAQ', len(faq_lines) >= 3, 'Добавьте 3-6 вопросов: вопрос | ответ.'),
            ('Есть связанный следующий шаг', bool(obj.related_test_id or obj.related_theory_id), 'Идеально: статья -> тест, тест -> теория.'),
        ]

        rows = format_html_join(
            '',
            '<li style="margin: 4px 0;"><span style="font-weight: 700; color: {};">{}</span> <strong>{}</strong><br><span style="color: #64748b;">{}</span></li>',
            (
                ('#15803d' if passed else '#b45309', 'OK' if passed else 'TODO', label, hint)
                for label, passed, hint in checks
            )
        )
        return format_html('<ul style="margin: 0; padding-left: 18px;">{}</ul>', rows)

    seo_checklist.short_description = 'SEO checklist'


    def image_workflow_note(self, obj):
        return format_html(
            "<b>How to use images:</b><br>"
            "1) Upload files in the <i>Material images</i> block below.<br>"
            "2) For article markdown use snippet <code>![alt](/media/...)</code>.<br>"
            "3) For tests in <code>test_payload</code> use <code>image_url</code> / <code>image_alt</code> "
            "for question and options.<br>"
            "4) For the test bank use image fields directly in question and option rows."
        )

    image_workflow_note.short_description = 'Image workflow'


class MaterialImageInline(admin.TabularInline):
    model = MaterialImage
    extra = 0
    fields = (
        'preview',
        'image',
        'title',
        'alt_text',
        'usage',
        'sort_order',
        'markdown_for_article',
        'snippet_for_test',
    )
    readonly_fields = ('preview', 'markdown_for_article', 'snippet_for_test')
    ordering = ('sort_order', 'id')

    def preview(self, obj):
        if not obj.pk or not obj.image:
            return '-'
        return format_html(
            '<img src="{}" alt="{}" style="max-width: 140px; max-height: 80px; border-radius: 6px;"/>',
            obj.image.url,
            obj.alt_text or obj.title or 'preview',
        )

    preview.short_description = 'Preview'

    def markdown_for_article(self, obj):
        return obj.markdown_snippet if obj.pk else ''

    markdown_for_article.short_description = 'Markdown for article'

    def snippet_for_test(self, obj):
        return obj.test_json_snippet if obj.pk else ''

    snippet_for_test.short_description = 'JSON for payload test'


MaterialItemAdmin.inlines = (MaterialImageInline,)


class MaterialTestOptionInline(admin.TabularInline):
    model = MaterialTestOption
    extra = 1
    fields = ('order', 'label', 'value', 'image', 'image_alt', 'is_correct', 'is_active')


@admin.register(MaterialTestQuestion)
class MaterialTestQuestionAdmin(admin.ModelAdmin):
    list_display = ('code', 'test', 'question_type', 'points', 'order', 'is_active', 'updated_at')
    list_filter = ('question_type', 'is_active', 'test__material__subject')
    search_fields = ('code', 'prompt', 'test__material__title')
    list_editable = ('points', 'order', 'is_active')
    inlines = [MaterialTestOptionInline]


class MaterialTestQuestionInline(admin.TabularInline):
    model = MaterialTestQuestion
    extra = 1
    fields = ('order', 'code', 'question_type', 'points', 'required', 'is_active', 'prompt', 'image', 'image_alt')
    show_change_link = True


@admin.register(MaterialTest)
class MaterialTestAdmin(admin.ModelAdmin):
    list_display = (
        'material',
        'title',
        'passing_score_percent',
        'duration_minutes',
        'max_attempts',
        'is_active',
        'questions_total',
        'updated_at',
    )
    list_filter = ('is_active', 'material__subject', 'material__exam_type')
    search_fields = ('title', 'material__title', 'material__slug')
    inlines = [MaterialTestQuestionInline]

    def questions_total(self, obj):
        return obj.questions.count()

    questions_total.short_description = 'Questions'


@admin.register(MaterialTestAttempt)
class MaterialTestAttemptAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'material',
        'user',
        'attempt_no',
        'score_points',
        'max_points',
        'score_percent',
        'passed',
        'submitted_at',
    )
    list_filter = ('passed', 'material', 'material__subject', 'submitted_at')
    search_fields = ('material__title', 'user__username', 'user__email', 'session_key')
    readonly_fields = (
        'material',
        'user',
        'session_key',
        'attempt_no',
        'max_points',
        'score_points',
        'score_percent',
        'passed',
        'duration_seconds',
        'answers_payload',
        'result_payload',
        'started_at',
        'submitted_at',
    )
