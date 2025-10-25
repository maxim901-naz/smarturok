from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Subject, Lesson, TrialRequest, CustomUser

# Регистрируем предметы и занятия
admin.site.register(Subject)
admin.site.register(Lesson)

# Админка для заявок на пробный урок
@admin.register(TrialRequest)
class TrialRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'assigned_teacher', 'is_converted', 'created_at')
    list_filter = ('subject', 'is_converted')
    search_fields = ('name', 'email')

# Админка для пользователей
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ('id',
        'username', 'email', 'first_name', 'last_name',
        'role', 'desired_subject', 'is_approved', 'is_active'
    )
    list_filter = ('role', 'is_approved', 'is_active', 'desired_subject')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    actions = ['approve_teachers']

    # Дополнительные поля при редактировании
    fieldsets = UserAdmin.fieldsets + (
        ('Дополнительные поля', {'fields': ('role', 'is_approved', 'desired_subject')}),
    )

    # Дополнительные поля при добавлении
    add_fieldsets = UserAdmin.add_fieldsets + (
        ('Дополнительные поля', {'fields': ('role', 'is_approved', 'desired_subject')}),
    )

    # Экшн: одобрить выбранных преподавателей
    def approve_teachers(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"Одобрено преподавателей: {updated}")
    approve_teachers.short_description = "Одобрить выбранных преподавателей"
