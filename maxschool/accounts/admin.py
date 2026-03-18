# from typing import Literal
# from django.contrib import admin
# from django.contrib.auth.admin import UserAdmin
# from .models import Subject, Lesson, TrialRequest, CustomUser, BalanceTransaction, BalanceTopUpRequest, TeacherFinanceEntry, TeacherNotification
# from lessons.models import TeacherAvailability


# from .forms import AdminUserCreationForm, AdminUserChangeForm

# # Регистрируем предметы и занятия
# 
# admin.site.register(Lesson)
# class LessonAdmin(admin.ModelAdmin):
#     list_display = (
#         'date', 'time', 'subject', 'teacher', 'student', 'duration_minutes'
#     )
#     list_filter = (
#         'teacher', 'student', 'subject', 'date',
#     )
#     search_fields = (
#         'teacher__username', 'student__username', 'subject__name'
#     )
#     ordering = ('date', 'time')
#     list_editable = ('is_completed',)
# # Админка для заявок на пробный урок
# @admin.register(TrialRequest)
# class TrialRequestAdmin(admin.ModelAdmin):
#     list_display = ('name', 'email', 'subject', 'assigned_teacher', 'is_converted', 'created_at')
#     list_filter = ('subject', 'is_converted')
#     search_fields = ('name', 'email')

# # Админка для пользователей
# @admin.register(CustomUser)
# class CustomUserAdmin(UserAdmin):
#     add_form = AdminUserCreationForm
#     form = AdminUserChangeForm
#     model = CustomUser

#     list_display = (
#         'id', 'username', 'email', 'role', 'desired_subject', 'is_approved', 'is_active','balance'
#     )
#     list_editable = ('balance',)

#     list_filter = ('role', 'is_approved', 'is_active', 'desired_subject')

#     # --- ВАЖНО: НЕ НАСЛЕДУЕМ UserAdmin.fieldsets ---
#     fieldsets = (
#         (None, {
#             "fields": ("username", "password")
#         }),
#         ("Персональная информация", {
#             "fields": ("first_name", "last_name", "email", "photo")
#         }),
#         ("Роли и доступ", {
#             "fields": ("role", "is_approved", "is_active", "is_staff",
#                        "is_superuser", "groups", "user_permissions")
#         }),
#         ("Дополнительно", {
#             "fields": ("desired_subject", "subjects_taught", "teachers")
#         }),
#     )

#     add_fieldsets = (
#         (None, {
#             "classes": ("wide",),
#             "fields": ("username", "email", "password1", "password2",
#                        "role", "is_approved", "desired_subject", "photo"),
#         }),
#     )

#     actions = ['approve_teachers']

#     def approve_teachers(self, request, queryset):
#         updated = queryset.filter(role='teacher').update(is_approved=True)
#         self.message_user(request, f"Одобрено преподавателей: {updated}")

#     approve_teachers.short_description = "Одобрить выбранных преподавателей"

# @admin.register(TeacherAvailability)
# class TeacherAvailabilityAdmin(admin.ModelAdmin):
#     list_display = (
#         'teacher', 'get_display_text', 'time', 'duration_minutes', 'is_recurring', 'is_booked'
#     )
#     list_filter = (
#         'teacher', 'is_recurring', 'is_booked',
#     )
#     search_fields = ('teacher__username',)
#     ordering = ('date', 'time')
from typing import Literal
from django.contrib import admin
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin
from .models import Subject, Lesson, TrialRequest, CustomUser, BalanceTransaction, BalanceTopUpRequest, TeacherFinanceEntry, TeacherNotification, StudentNotification, StudentVacation
from lessons.models import TeacherAvailability
from .forms import AdminUserCreationForm, AdminUserChangeForm

# Регистрируем предметы


# Админка для уроков
@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = (
        'date', 'time', 'subject', 'teacher', 'student', 'duration_minutes', 'price_per_lesson', 'is_completed'
    )
    list_filter = (
        'teacher', 'student', 'subject', 'date', 'is_completed'
    )
    search_fields = (
        'teacher__username', 'student__username', 'subject__name'
    )
    ordering = ('date', 'time')
    # убираем list_editable для is_completed, чтобы save_model срабатывал корректно
    # list_editable = ('is_completed',)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)


# Админка для заявок на пробный урок
@admin.register(TrialRequest)
class TrialRequestAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'subject', 'personal_data_consent', 'assigned_teacher', 'is_converted', 'created_at')
    list_filter = ('subject', 'personal_data_consent', 'is_converted')
    search_fields = ('name', 'email')

# Админка для пользователей
@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    model = CustomUser

    list_display = (
        'id', 'username', 'email', 'role', 'desired_subject', 'is_approved', 'is_email_verified', 'is_active', 'balance'
    )
    list_editable = ('balance',)
    list_filter = ('role', 'is_approved', 'is_email_verified', 'is_active', 'desired_subject')

    # --- ВАЖНО: НЕ НАСЛЕДУЕМ UserAdmin.fieldsets ---
    fieldsets = (
        (None, {
            "fields": ("username", "password")
        }),
        ("Персональная информация", {
            "fields": ("first_name", "last_name", "email", "photo", "time_zone")
        }),
        ("Роли и доступ", {
            "fields": ("role", "is_approved", "is_email_verified", "is_active", "is_staff",
                       "is_superuser", "groups", "user_permissions")
        }),
        ("Дополнительно", {
            "fields": ("desired_subject", "subjects_taught", "teachers")
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2",
                       "role", "is_approved", "is_email_verified", "desired_subject", "subjects_taught", "photo", "time_zone"),
        }),
    )

    actions = ['approve_teachers']

    def approve_teachers(self, request, queryset):
        updated = queryset.filter(role='teacher').update(is_approved=True)
        self.message_user(request, f"Одобрено преподавателей: {updated}")

    approve_teachers.short_description = "Одобрить выбранных преподавателей"

# Админка для доступности учителей
@admin.register(TeacherAvailability)
class TeacherAvailabilityAdmin(admin.ModelAdmin):
    list_display = (
        'teacher', 'get_display_text', 'time', 'duration_minutes', 'is_recurring', 'is_booked'
    )
    list_filter = (
        'teacher', 'is_recurring', 'is_booked',
    )
    search_fields = ('teacher__username',)
    ordering = ('date', 'time')


@admin.register(BalanceTransaction)
class BalanceTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'direction', 'amount', 'lesson', 'created_at')
    list_filter = ('direction', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)


@admin.register(BalanceTopUpRequest)
class BalanceTopUpRequestAdmin(admin.ModelAdmin):
    list_display = ('user', 'package', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)
    actions = ['mark_approved', 'mark_rejected']

    def mark_approved(self, request, queryset):
        for req in queryset:
            if req.status == 'approved':
                continue
            req.status = 'approved'
            req.save(update_fields=['status'])
            req.user.balance += req.package
            req.user.save(update_fields=['balance'])
            BalanceTransaction.objects.create(
                user=req.user,
                direction='credit',
                amount=req.package,
                note='Пополнение по заявке',
            )
    mark_approved.short_description = 'Отметить как одобрено'

    def mark_rejected(self, request, queryset):
        queryset.update(status='rejected')
    mark_rejected.short_description = 'Отметить как отклонено'


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'slug',
        'price_per_lesson',
        'discount_4',
        'discount_8',
        'discount_12',
        'discount_28',
        'discount_64',
        'discount_128',
        'image_preview'
    )
    list_editable = (
        'price_per_lesson',
        'discount_4',
        'discount_8',
        'discount_12',
        'discount_28',
        'discount_64',
        'discount_128',
    )
    readonly_fields = ('image_preview',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')
    fieldsets = (
        ('Основное', {
            'fields': ('name', 'slug', 'price_per_lesson', 'image', 'landing_image', 'image_preview'),
        }),
        ('Контент страницы предмета', {
            'fields': (
                'hero_title',
                'hero_subtitle',
                'landing_description',
                'metrics',
                'results_title',
                'result_points',
                'include_items_title',
                'include_items',
                'benefits_title',
                'benefits',
                'program_title',
                'program',
                'progress_title',
                'progress_subtitle',
                'progress_cards',
            ),
        }),
        ('SEO', {
            'classes': ('collapse',),
            'fields': ('seo_title', 'seo_description'),
        }),
        ('Скидки по пакетам', {
            'fields': (
                'discount_4',
                'discount_8',
                'discount_12',
                'discount_28',
                'discount_64',
                'discount_128',
            ),
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return mark_safe(f"<img src='{obj.image.url}' style='height:50px;border-radius:6px;' />")
        return "—"
    image_preview.short_description = "Картинка"


@admin.register(TeacherFinanceEntry)
class TeacherFinanceEntryAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'lesson', 'amount', 'payout_status', 'created_at')
    list_filter = ('payout_status', 'created_at')
    search_fields = ('teacher__username',)
    ordering = ('-created_at',)
    actions = ['mark_paid']

    def mark_paid(self, request, queryset):
        queryset.update(payout_status='paid')
    mark_paid.short_description = 'Отметить как выплачено'


@admin.register(TeacherNotification)
class TeacherNotificationAdmin(admin.ModelAdmin):
    list_display = ('teacher', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('teacher__username', 'message')
    ordering = ('-created_at',)


@admin.register(StudentNotification)
class StudentNotificationAdmin(admin.ModelAdmin):
    list_display = ('student', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('student__username', 'message')
    ordering = ('-created_at',)


@admin.register(StudentVacation)
class StudentVacationAdmin(admin.ModelAdmin):
    list_display = ('student', 'start_date', 'end_date', 'affected_lessons_count', 'applied_at', 'created_at')
    list_filter = ('start_date', 'end_date', 'applied_at', 'created_at')
    search_fields = ('student__username', 'student__first_name', 'student__last_name', 'student__email')
    readonly_fields = ('applied_at', 'affected_lessons_count', 'created_at')
    fields = (
        'student',
        'start_date',
        'end_date',
        'comment',
        'created_by',
        'applied_at',
        'affected_lessons_count',
        'created_at',
    )

    def get_readonly_fields(self, request, obj=None):
        readonly = list(self.readonly_fields)
        if obj and obj.applied_at:
            readonly.extend(['student', 'start_date', 'end_date', 'comment', 'created_by'])
        return readonly

    def save_model(self, request, obj, form, change):
        if not obj.created_by_id and getattr(request, 'user', None) and request.user.is_authenticated:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
        if not obj.applied_at:
            affected = obj.apply_vacation()
            self.message_user(request, f'Отпуск применён. Снято уроков: {affected}.')
