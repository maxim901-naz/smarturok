from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import CustomUser, Subject, TrialRequest


CRM_RESPONSE_SLA_MINUTES = 5
TRIAL_WORK_STATUSES = {value for value, _ in TrialRequest.WORK_STATUS_CHOICES}


def _has_crm_access(user):
    return bool(
        user.is_authenticated
        and user.is_active
        and (user.is_staff or getattr(user, 'role', None) == 'admin')
    )


def _safe_crm_redirect(next_url=''):
    if next_url and next_url.startswith('/crm/'):
        return next_url
    return reverse('crm_dashboard')


def _touch_response_fields(trial_request, user, *, close=False):
    now_value = timezone.now()
    update_fields = ['work_status']

    if not trial_request.assigned_admin_id and getattr(user, 'is_staff', False):
        trial_request.assigned_admin = user
        update_fields.append('assigned_admin')

    if not trial_request.first_response_at:
        trial_request.first_response_at = now_value
        update_fields.append('first_response_at')

    if close:
        trial_request.closed_at = now_value
        update_fields.append('closed_at')
    elif trial_request.closed_at:
        trial_request.closed_at = None
        update_fields.append('closed_at')

    return update_fields


def _handle_trial_action(request):
    request_id = request.POST.get('request_id')
    if not request_id or not str(request_id).isdigit():
        messages.error(request, 'Некорректная заявка.')
        return redirect(_safe_crm_redirect(request.POST.get('next', '')))

    trial_request = get_object_or_404(TrialRequest, pk=request_id)
    action = request.POST.get('action')

    if action == 'take':
        trial_request.work_status = 'in_progress'
        update_fields = _touch_response_fields(trial_request, request.user)
        trial_request.save(update_fields=update_fields)
        messages.success(request, 'Заявка взята в работу.')

    elif action == 'done':
        trial_request.work_status = 'done'
        update_fields = _touch_response_fields(trial_request, request.user, close=True)
        trial_request.save(update_fields=update_fields)
        messages.success(request, 'Заявка закрыта.')

    elif action == 'converted':
        trial_request.work_status = 'done'
        trial_request.is_converted = True
        update_fields = _touch_response_fields(trial_request, request.user, close=True)
        update_fields.append('is_converted')
        trial_request.save(update_fields=update_fields)
        messages.success(request, 'Заявка отмечена как ученик.')

    elif action == 'reject':
        trial_request.work_status = 'rejected'
        update_fields = _touch_response_fields(trial_request, request.user, close=True)
        trial_request.save(update_fields=update_fields)
        messages.success(request, 'Заявка отклонена.')

    elif action == 'reopen':
        trial_request.work_status = 'new'
        trial_request.closed_at = None
        trial_request.save(update_fields=['work_status', 'closed_at'])
        messages.success(request, 'Заявка возвращена в новые.')

    elif action == 'assign_teacher':
        teacher_id = request.POST.get('teacher_id')
        if not teacher_id:
            trial_request.assigned_teacher = None
            trial_request.save(update_fields=['assigned_teacher'])
            messages.success(request, 'Преподаватель снят с заявки.')
        elif not str(teacher_id).isdigit():
            messages.error(request, 'Некорректный преподаватель.')
        else:
            teacher = get_object_or_404(
                CustomUser,
                pk=teacher_id,
                role='teacher',
                is_active=True,
            )
            trial_request.assigned_teacher = teacher
            if trial_request.work_status == 'new':
                trial_request.work_status = 'in_progress'
            update_fields = _touch_response_fields(trial_request, request.user)
            update_fields.append('assigned_teacher')
            trial_request.save(update_fields=update_fields)
            messages.success(request, 'Преподаватель назначен.')

    else:
        messages.error(request, 'Неизвестное действие.')

    return redirect(_safe_crm_redirect(request.POST.get('next', '')))


@login_required
def crm_dashboard(request):
    if not _has_crm_access(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        return _handle_trial_action(request)

    now_value = timezone.now()
    overdue_cutoff = now_value - timedelta(minutes=CRM_RESPONSE_SLA_MINUTES)

    current_status = request.GET.get('status', 'new')
    current_subject = request.GET.get('subject', '')
    current_lead_form = request.GET.get('lead_form', '')
    search_query = (request.GET.get('q') or '').strip()
    if current_subject and not current_subject.isdigit():
        current_subject = ''

    requests_qs = (
        TrialRequest.objects
        .select_related('subject', 'assigned_admin', 'assigned_teacher')
        .order_by('-created_at')
    )

    if current_status in TRIAL_WORK_STATUSES:
        requests_qs = requests_qs.filter(work_status=current_status)
    elif current_status == 'converted':
        requests_qs = requests_qs.filter(is_converted=True)
    elif current_status == 'overdue':
        requests_qs = requests_qs.filter(
            work_status='new',
            created_at__lte=overdue_cutoff,
        )
    elif current_status != 'all':
        current_status = 'new'
        requests_qs = requests_qs.filter(work_status='new')

    if current_subject:
        requests_qs = requests_qs.filter(subject_id=current_subject)

    if current_lead_form:
        requests_qs = requests_qs.filter(lead_form=current_lead_form)

    if search_query:
        requests_qs = requests_qs.filter(
            Q(name__icontains=search_query)
            | Q(student_name__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(message__icontains=search_query)
            | Q(promo_interest__icontains=search_query)
        )

    requests_list = list(requests_qs[:120])

    base_qs = TrialRequest.objects.all()
    today = timezone.localdate()
    week_ago = now_value - timedelta(days=7)

    stats = {
        'new': base_qs.filter(work_status='new').count(),
        'in_progress': base_qs.filter(work_status='in_progress').count(),
        'done': base_qs.filter(work_status='done').count(),
        'rejected': base_qs.filter(work_status='rejected').count(),
        'converted': base_qs.filter(is_converted=True).count(),
        'overdue': base_qs.filter(work_status='new', created_at__lte=overdue_cutoff).count(),
        'today': base_qs.filter(created_at__date=today).count(),
        'week': base_qs.filter(created_at__gte=week_ago).count(),
    }

    status_tabs = [
        ('new', 'Новые', stats['new']),
        ('overdue', 'Просрочены', stats['overdue']),
        ('in_progress', 'В работе', stats['in_progress']),
        ('converted', 'Стали учениками', stats['converted']),
        ('done', 'Закрыты', stats['done']),
        ('rejected', 'Отказы', stats['rejected']),
        ('all', 'Все', base_qs.count()),
    ]

    lead_forms = (
        base_qs
        .exclude(lead_form='')
        .values('lead_form')
        .annotate(total=Count('id'))
        .order_by('-total', 'lead_form')
    )

    subject_stats = (
        base_qs
        .filter(created_at__gte=week_ago)
        .values('subject__name')
        .annotate(total=Count('id'))
        .order_by('-total')[:6]
    )

    context = {
        'requests_list': requests_list,
        'stats': stats,
        'status_tabs': status_tabs,
        'current_status': current_status,
        'current_subject': current_subject,
        'current_lead_form': current_lead_form,
        'search_query': search_query,
        'subjects': Subject.objects.order_by('name'),
        'lead_forms': lead_forms,
        'subject_stats': subject_stats,
        'teachers': CustomUser.objects.filter(role='teacher', is_active=True).order_by('last_name', 'first_name', 'username'),
        'sla_minutes': CRM_RESPONSE_SLA_MINUTES,
    }
    return render(request, 'accounts/crm_dashboard.html', context)
