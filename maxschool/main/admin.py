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
    list_display = ('title', 'category', 'subject', 'grade', 'is_published', 'created_at')
    list_filter = ('category', 'subject', 'grade', 'is_published')
    search_fields = ('title', 'description')
    list_editable = ('is_published',)
