from django.contrib import admin

from .models import MaterialCategory, MaterialItem, MaterialTestAttempt, Review


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
    readonly_fields = ('is_published', 'published_at', 'created_at', 'updated_at')
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
            'fields': ('video_url', 'article_markdown', 'file', 'external_url', 'test_payload')
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

    test_attempts_total.short_description = 'Test attempts'


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
