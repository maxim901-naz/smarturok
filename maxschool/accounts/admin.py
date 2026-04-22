from typing import Literal
from django.contrib import admin
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.contrib.auth.admin import UserAdmin

from .forms import AdminUserCreationForm, AdminUserChangeForm
from .models import (
    Subject,
    Lesson,
    TrialRequest,
    CustomUser,
    BalanceTransaction,
    BalanceTopUpRequest,
    TeacherFinanceEntry,
    TeacherNotification,
    StudentNotification,
    StudentVacation,
    Vacancy,
    TeacherApplication,
)
from lessons.models import TeacherAvailability


class RequestSLAAdminMixin:
    response_sla_minutes = 5
    default_new_filter = True

    def changelist_view(self, request, extra_context=None):
        if self.default_new_filter and not request.GET:
            return HttpResponseRedirect(f'{request.path}?work_status__exact=new')
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description='SLA')
    def sla_badge(self, obj):
        if getattr(obj, 'work_status', '') == 'new':
            created_at = getattr(obj, 'created_at', None)
            if not created_at:
                return '—'

            elapsed_minutes = int((timezone.now() - created_at).total_seconds() // 60)
            if elapsed_minutes >= self.response_sla_minutes:
                return format_html(
                    "<span style='color:#dc2626;font-weight:700;'>Просрочено: {} мин</span>",
                    elapsed_minutes,
                )
            return format_html(
                "<span style='color:#d97706;font-weight:600;'>Новая: {} мин</span>",
                elapsed_minutes,
            )

        if getattr(obj, 'work_status', '') == 'in_progress':
            return format_html("<span style='color:#2563eb;font-weight:600;'>В работе</span>")
        if getattr(obj, 'work_status', '') == 'done':
            return format_html("<span style='color:#15803d;font-weight:600;'>Закрыта</span>")
        if getattr(obj, 'work_status', '') == 'rejected':
            return format_html("<span style='color:#6b7280;font-weight:600;'>Отклонена</span>")
        return '—'

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
class TrialRequestAdmin(RequestSLAAdminMixin, admin.ModelAdmin):
    list_display = (
        'name',
        'phone',
        'email',
        'subject',
        'promo_interest',
        'lead_form',
        'work_status',
        'assigned_admin',
        'first_response_at',
        'pricing_lessons_count',
        'pricing_discount_percent',
        'pricing_total_price',
        'personal_data_consent',
        'assigned_teacher',
        'is_converted',
        'sla_badge',
        'created_at',
    )
    list_filter = (
        'work_status',
        'assigned_admin',
        'subject',
        'lead_form',
        'personal_data_consent',
        'is_converted',
        'created_at',
    )
    search_fields = ('name', 'email', 'phone', 'promo_interest', 'pricing_subject_name')
    ordering = ('-created_at',)
    readonly_fields = (
        'created_at',
        'consent_at',
        'consent_ip',
        'consent_user_agent',
        'first_response_at',
        'closed_at',
        'sla_badge',
    )
    fields = (
        'name',
        'phone',
        'email',
        'subject',
        'promo_interest',
        'lead_form',
        'work_status',
        'assigned_admin',
        'first_response_at',
        'closed_at',
        'sla_badge',
        'pricing_subject_name',
        'pricing_lessons_count',
        'pricing_discount_percent',
        'pricing_total_price',
        'pricing_old_price',
        'preferred_time',
        'message',
        'personal_data_consent',
        'consent_at',
        'consent_ip',
        'consent_user_agent',
        'assigned_teacher',
        'is_converted',
        'created_at',
    )
    actions = ('take_in_work', 'mark_done', 'mark_rejected')

    def _touch_first_response(self, obj, now_value):
        if not obj.first_response_at:
            obj.first_response_at = now_value

    def save_model(self, request, obj, form, change):
        now_value = timezone.now()
        if obj.work_status in {'in_progress', 'done', 'rejected'}:
            if not obj.assigned_admin_id and request.user.is_staff:
                obj.assigned_admin = request.user
            self._touch_first_response(obj, now_value)
        if obj.work_status in {'done', 'rejected'} and not obj.closed_at:
            obj.closed_at = now_value
        if obj.work_status in {'new', 'in_progress'}:
            obj.closed_at = None
        super().save_model(request, obj, form, change)

    @admin.action(description='Take in work')
    def take_in_work(self, request, queryset):
        now_value = timezone.now()
        for obj in queryset:
            obj.work_status = 'in_progress'
            if not obj.assigned_admin_id and request.user.is_staff:
                obj.assigned_admin = request.user
            self._touch_first_response(obj, now_value)
            obj.closed_at = None
            obj.save(update_fields=['work_status', 'assigned_admin', 'first_response_at', 'closed_at'])

    @admin.action(description='Close request')
    def mark_done(self, request, queryset):
        now_value = timezone.now()
        for obj in queryset:
            obj.work_status = 'done'
            if not obj.assigned_admin_id and request.user.is_staff:
                obj.assigned_admin = request.user
            self._touch_first_response(obj, now_value)
            obj.closed_at = now_value
            obj.save(update_fields=['work_status', 'assigned_admin', 'first_response_at', 'closed_at'])

    @admin.action(description='Mark rejected')
    def mark_rejected(self, request, queryset):
        now_value = timezone.now()
        for obj in queryset:
            obj.work_status = 'rejected'
            if not obj.assigned_admin_id and request.user.is_staff:
                obj.assigned_admin = request.user
            self._touch_first_response(obj, now_value)
            obj.closed_at = now_value
            obj.save(update_fields=['work_status', 'assigned_admin', 'first_response_at', 'closed_at'])

# Админка для пользователей
@admin.register(Vacancy)
class VacancyAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_active', 'order', 'updated_at')
    list_filter = ('is_active',)
    list_editable = ('is_active', 'order')
    search_fields = ('title', 'short_description')
    ordering = ('order', 'title')


@admin.register(TeacherApplication)
class TeacherApplicationAdmin(admin.ModelAdmin):
    list_display = ('submitted_at', 'name', 'vacancy', 'phone', 'email', 'years_experience')
    list_filter = ('vacancy', 'submitted_at')
    search_fields = ('name', 'first_name', 'last_name', 'email', 'phone', 'specialization')
    readonly_fields = ('submitted_at',)
    ordering = ('-submitted_at',)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = AdminUserCreationForm
    form = AdminUserChangeForm
    model = CustomUser

    list_display = (
        'id', 'username', 'email', 'role', 'desired_subject', 'is_approved',
        'is_email_verified', 'is_active', 'balance',
        'teacher_payout_percent', 'teacher_payout_fixed'
    )
    list_editable = ('balance', 'teacher_payout_percent', 'teacher_payout_fixed')
    list_filter = ('role', 'is_approved', 'is_email_verified', 'is_active', 'desired_subject')
    readonly_fields = ('manual_credit_buttons',)

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
        ("Баланс ученика", {
            "fields": ("balance", "manual_credit_buttons")
        }),
        ("Дополнительно", {
            "fields": ("desired_subject", "subjects_taught", "teachers")
        }),
        ("Профиль преподавателя", {
            "fields": (
                "experience_years",
                "students_count",
                "success_rate",
                "rating",
                "reviews_count",
                "bio",
                "education",
                "methodology",
                "achievements",
            )
        }),
        ("Teacher payout", {
            "fields": ("teacher_payout_percent", "teacher_payout_fixed")
        }),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("username", "email", "password1", "password2",
                       "role", "is_approved", "is_email_verified", "desired_subject", "subjects_taught", "photo", "time_zone",
                       "experience_years", "students_count", "success_rate", "rating", "reviews_count",
                       "teacher_payout_percent", "teacher_payout_fixed"),
        }),
    )

    actions = ['approve_teachers']

    def approve_teachers(self, request, queryset):
        updated = queryset.filter(role='teacher').update(is_approved=True)
        self.message_user(request, f"Одобрено преподавателей: {updated}")

    approve_teachers.short_description = "Одобрить выбранных преподавателей"

    def get_urls(self):
        custom_urls = [
            path(
                '<int:user_id>/manual-credit/<int:lessons>/',
                self.admin_site.admin_view(self.manual_credit_view),
                name='accounts_customuser_manual_credit',
            ),
        ]
        return custom_urls + super().get_urls()

    @admin.display(description='Ручное начисление уроков')
    def manual_credit_buttons(self, obj):
        if not obj or obj.role != 'student':
            return '—'

        buttons = []
        for lessons in (1, 4, 8, 12):
            url = reverse('admin:accounts_customuser_manual_credit', args=[obj.pk, lessons])
            buttons.append(
                f"<a class='button' href='{url}' style='margin-right:8px;'>+{lessons}</a>"
            )
        return format_html(''.join(buttons))

    def manual_credit_view(self, request, user_id, lessons):
        user = get_object_or_404(CustomUser, pk=user_id)

        if not self.has_change_permission(request, user):
            return HttpResponseRedirect(reverse('admin:accounts_customuser_changelist'))

        if user.role != 'student':
            self.message_user(request, 'Ручное начисление доступно только для учеников.')
            return HttpResponseRedirect(reverse('admin:accounts_customuser_change', args=[user.pk]))

        allowed = {1, 4, 8, 12}
        if lessons not in allowed:
            self.message_user(request, 'Недопустимое количество уроков для начисления.')
            return HttpResponseRedirect(reverse('admin:accounts_customuser_change', args=[user.pk]))

        if request.method == 'POST':
            comment = (request.POST.get('comment') or '').strip() or 'Бонусный урок'
            user.balance += lessons
            user.save(update_fields=['balance'])

            BalanceTransaction.objects.create(
                user=user,
                direction='credit',
                amount=lessons,
                note=f'Ручное начисление: {comment} (админ: {request.user.username})',
            )
            self.message_user(
                request,
                f'Начислено {lessons} урок(ов) пользователю {user.username}. Комментарий: {comment}',
            )
            return HttpResponseRedirect(reverse('admin:accounts_customuser_change', args=[user.pk]))

        context = {
            **self.admin_site.each_context(request),
            'opts': self.model._meta,
            'title': f'Ручное начисление +{lessons} урок(ов)',
            'user_obj': user,
            'lessons': lessons,
            'default_comment': 'Бонусный урок',
            'cancel_url': reverse('admin:accounts_customuser_change', args=[user.pk]),
        }
        return TemplateResponse(
            request,
            'admin/accounts/manual_credit_form.html',
            context,
        )

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
class BalanceTopUpRequestAdmin(RequestSLAAdminMixin, admin.ModelAdmin):
    list_display = (
        'user',
        'package',
        'status',
        'work_status',
        'assigned_admin',
        'first_response_at',
        'sla_badge',
        'created_at',
    )
    list_filter = ('status', 'work_status', 'assigned_admin', 'created_at')
    search_fields = ('user__username',)
    ordering = ('-created_at',)
    readonly_fields = ('first_response_at', 'closed_at', 'sla_badge', 'created_at')
    fields = (
        'user',
        'package',
        'comment',
        'status',
        'work_status',
        'assigned_admin',
        'first_response_at',
        'closed_at',
        'sla_badge',
        'created_at',
    )
    actions = ['take_in_work', 'mark_approved', 'mark_rejected']

    def _topup_credit_note(self, req):
        return f'Top-up approved by admin (request #{req.pk})'

    def _credit_topup_if_needed(self, req):
        credit_note = self._topup_credit_note(req)
        already_credited = BalanceTransaction.objects.filter(
            user=req.user,
            direction='credit',
            note=credit_note,
        ).exists()
        if already_credited:
            return False

        req.user.balance += req.package
        req.user.save(update_fields=['balance'])
        BalanceTransaction.objects.create(
            user=req.user,
            direction='credit',
            amount=req.package,
            note=credit_note,
        )
        return True

    def _touch_first_response(self, obj, now_value):
        if not obj.first_response_at:
            obj.first_response_at = now_value

    def save_model(self, request, obj, form, change):
        now_value = timezone.now()
        previous_status = None
        if change and obj.pk:
            previous_status = (
                BalanceTopUpRequest.objects
                .filter(pk=obj.pk)
                .values_list('status', flat=True)
                .first()
            )

        if obj.work_status in {'in_progress', 'done', 'rejected'}:
            if not obj.assigned_admin_id and request.user.is_staff:
                obj.assigned_admin = request.user
            self._touch_first_response(obj, now_value)
        if obj.work_status in {'done', 'rejected'} and not obj.closed_at:
            obj.closed_at = now_value
        if obj.work_status in {'new', 'in_progress'}:
            obj.closed_at = None
        super().save_model(request, obj, form, change)

        # Credit balance on any transition to approved, not only via admin action.
        became_approved = obj.status == 'approved' and previous_status != 'approved'
        created_as_approved = not change and obj.status == 'approved'
        if became_approved or created_as_approved:
            self._credit_topup_if_needed(obj)

    @admin.action(description='Take in work')
    def take_in_work(self, request, queryset):
        now_value = timezone.now()
        for req in queryset:
            req.work_status = 'in_progress'
            if not req.assigned_admin_id and request.user.is_staff:
                req.assigned_admin = request.user
            self._touch_first_response(req, now_value)
            req.closed_at = None
            req.save(update_fields=['work_status', 'assigned_admin', 'first_response_at', 'closed_at'])

    @admin.action(description='Mark approved')
    def mark_approved(self, request, queryset):
        now_value = timezone.now()
        for req in queryset:
            should_credit = req.status != 'approved'
            req.status = 'approved'
            req.work_status = 'done'
            if not req.assigned_admin_id and request.user.is_staff:
                req.assigned_admin = request.user
            self._touch_first_response(req, now_value)
            req.closed_at = now_value
            req.save(update_fields=['status', 'work_status', 'assigned_admin', 'first_response_at', 'closed_at'])
            if should_credit:
                self._credit_topup_if_needed(req)

    @admin.action(description='Mark rejected')
    def mark_rejected(self, request, queryset):
        now_value = timezone.now()
        for req in queryset:
            req.status = 'rejected'
            req.work_status = 'rejected'
            if not req.assigned_admin_id and request.user.is_staff:
                req.assigned_admin = request.user
            self._touch_first_response(req, now_value)
            req.closed_at = now_value
            req.save(update_fields=['status', 'work_status', 'assigned_admin', 'first_response_at', 'closed_at'])


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
