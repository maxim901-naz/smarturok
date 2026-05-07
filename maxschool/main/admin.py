from django.contrib import admin
from .models import Review, MaterialCategory, MaterialItem


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
        ('Основное', {
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
        ('Контент', {
            'fields': ('video_url', 'article_markdown', 'file', 'external_url', 'test_payload')
        }),
        ('Публикация и доступ', {
            'fields': ('status', 'access_level', 'is_published', 'published_at')
        }),
        ('Служебное', {
            'fields': ('created_at', 'updated_at')
        }),
    )
