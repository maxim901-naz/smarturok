from django.contrib import admin
from django.utils.html import format_html

from .models import (
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
        'content_type',
        'exam_type',
        'access_level',
        'status',
        'is_published',
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
    search_fields = ('title', 'slug', 'description', 'meta_description', 'article_markdown')
    readonly_fields = ('is_published', 'published_at', 'created_at', 'updated_at', 'image_workflow_note')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('status', 'access_level')

    fieldsets = (
        ('Main', {
            'fields': (
                'title',
                'slug',
                'category',
                'subject',
                'grade',
                'content_type',
                'exam_type',
            )
        }),
        ('SEO', {
            'fields': ('description', 'meta_description')
        }),
        ('Content', {
            'fields': ('video_url', 'article_markdown', 'file', 'external_url', 'test_payload', 'image_workflow_note')
        }),
        ('Publishing and access', {
            'fields': ('status', 'access_level', 'is_published', 'published_at')
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
