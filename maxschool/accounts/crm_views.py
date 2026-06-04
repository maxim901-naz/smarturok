from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Count, Prefetch, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .models import CustomUser, Subject, TrialRequest, TrialRequestNote


CRM_RESPONSE_SLA_MINUTES = 5
CRM_OPEN_STATUSES = {'new', 'in_progress', 'no_answer', 'waiting', 'trial_scheduled', 'trial_done'}
CRM_CLOSED_STATUSES = {'paid', 'done', 'rejected'}
TRIAL_WORK_STATUSES = {value for value, _ in TrialRequest.WORK_STATUS_CHOICES}
TRIAL_STATUS_LABELS = dict(TrialRequest.WORK_STATUS_CHOICES)
TRIAL_STATUS_BADGES = {
    'new': 'bg-sky-100 text-sky-700',
    'in_progress': 'bg-amber-100 text-amber-700',
    'no_answer': 'bg-orange-100 text-orange-700',
    'waiting': 'bg-yellow-100 text-yellow-800',
    'trial_scheduled': 'bg-violet-100 text-violet-700',
    'trial_done': 'bg-cyan-100 text-cyan-700',
    'paid': 'bg-emerald-600 text-white',
    'done': 'bg-emerald-100 text-emerald-700',
    'rejected': 'bg-slate-200 text-slate-600',
}
CRM_STATUS_TABS = (
    ('new', 'Новые'),
    ('overdue', 'SLA'),
    ('due_contact', 'Нужен контакт'),
    ('in_progress', 'В работе'),
    ('no_answer', 'Не дозвонились'),
    ('waiting', 'Ждём ответа'),
    ('trial_scheduled', 'Пробный назначен'),
    ('trial_done', 'Пробный проведён'),
    ('paid', 'Оплатили'),
    ('rejected', 'Отказы'),
    ('all', 'Все'),
)


def _display_user_name(user):
    if not user:
        return 'Не назначен'
    full_name = (user.get_full_name() or '').strip()
    return full_name or user.username or 'Не назначен'


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


def _parse_next_contact(value):
    value = (value or '').strip()
    if not value:
        return None

    parsed = parse_datetime(value)
    if not parsed:
        return None
    if timezone.is_naive(parsed):
        parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
    return parsed


def _add_crm_note(trial_request, user, note_text):
    note_text = (note_text or '').strip()
    if not note_text:
        return None
    return TrialRequestNote.objects.create(
        trial_request=trial_request,
        author=user if user.is_authenticated else None,
        note=note_text,
    )


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
        trial_request.work_status = 'paid'
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

    elif action == 'set_status':
        new_status = request.POST.get('new_status')
        if new_status not in TRIAL_WORK_STATUSES:
            messages.error(request, 'Некорректный статус.')
        else:
            trial_request.work_status = new_status
            if new_status == 'paid':
                trial_request.is_converted = True
            update_fields = _touch_response_fields(
                trial_request,
                request.user,
                close=new_status in CRM_CLOSED_STATUSES,
            )
            if new_status == 'paid':
                update_fields.append('is_converted')
            trial_request.save(update_fields=update_fields)
            _add_crm_note(trial_request, request.user, request.POST.get('status_note'))
            messages.success(request, f'Статус изменён: {TRIAL_STATUS_LABELS.get(new_status, new_status)}.')

    elif action == 'update_followup':
        raw_next_contact = request.POST.get('next_contact_at')
        next_contact_at = _parse_next_contact(raw_next_contact)
        if raw_next_contact and not next_contact_at:
            messages.error(request, 'Не удалось распознать дату следующего контакта.')
        else:
            trial_request.next_contact_at = next_contact_at
            trial_request.next_contact_note = (request.POST.get('next_contact_note') or '').strip()[:255]
            update_fields = ['next_contact_at', 'next_contact_note']
            if trial_request.work_status == 'new':
                trial_request.work_status = 'in_progress'
                update_fields.extend(_touch_response_fields(trial_request, request.user))
            trial_request.save(update_fields=sorted(set(update_fields)))
            _add_crm_note(trial_request, request.user, request.POST.get('followup_note'))
            messages.success(request, 'Следующий контакт сохранён.')

    elif action == 'add_note':
        note = _add_crm_note(trial_request, request.user, request.POST.get('note'))
        if note:
            if trial_request.work_status == 'new':
                trial_request.work_status = 'in_progress'
                update_fields = _touch_response_fields(trial_request, request.user)
                trial_request.save(update_fields=update_fields)
            messages.success(request, 'Комментарий добавлен.')
        else:
            messages.error(request, 'Комментарий не может быть пустым.')

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
    current_subject_id = int(current_subject) if current_subject else None

    requests_qs = (
        TrialRequest.objects
        .select_related('subject', 'assigned_admin', 'assigned_teacher')
        .prefetch_related(
            Prefetch(
                'crm_notes',
                queryset=TrialRequestNote.objects.select_related('author').order_by('-created_at'),
                to_attr='crm_recent_notes',
            )
        )
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
    elif current_status == 'due_contact':
        requests_qs = requests_qs.filter(
            work_status__in=CRM_OPEN_STATUSES,
            next_contact_at__isnull=False,
            next_contact_at__lte=now_value,
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
    for item in requests_list:
        item.crm_admin_name = _display_user_name(item.assigned_admin)
        item.crm_teacher_name = _display_user_name(item.assigned_teacher)
        item.crm_is_overdue = (
            item.work_status == 'new'
            and bool(item.created_at)
            and item.created_at <= overdue_cutoff
        )
        item.crm_status_label = TRIAL_STATUS_LABELS.get(item.work_status, item.work_status)
        item.crm_status_class = TRIAL_STATUS_BADGES.get(item.work_status, 'bg-slate-100 text-slate-700')
        item.crm_next_contact_overdue = (
            item.work_status in CRM_OPEN_STATUSES
            and bool(item.next_contact_at)
            and item.next_contact_at <= now_value
        )
        item.crm_next_contact_label = ''
        item.crm_next_contact_value = ''
        if item.next_contact_at:
            local_next_contact = timezone.localtime(item.next_contact_at)
            item.crm_next_contact_label = local_next_contact.strftime('%d.%m.%Y %H:%M')
            item.crm_next_contact_value = local_next_contact.strftime('%Y-%m-%dT%H:%M')
        for note in getattr(item, 'crm_recent_notes', []):
            note.crm_author_name = _display_user_name(note.author)

    base_qs = TrialRequest.objects.all()
    today = timezone.localdate()
    week_ago = now_value - timedelta(days=7)

    stats = {
        'all': base_qs.count(),
        'converted': base_qs.filter(is_converted=True).count(),
        'overdue': base_qs.filter(work_status='new', created_at__lte=overdue_cutoff).count(),
        'due_contact': base_qs.filter(
            work_status__in=CRM_OPEN_STATUSES,
            next_contact_at__isnull=False,
            next_contact_at__lte=now_value,
        ).count(),
        'today': base_qs.filter(created_at__date=today).count(),
        'week': base_qs.filter(created_at__gte=week_ago).count(),
    }
    for status_value in TRIAL_WORK_STATUSES:
        stats[status_value] = base_qs.filter(work_status=status_value).count()

    status_tabs = [
        (status_key, status_label, stats.get(status_key, 0))
        for status_key, status_label in CRM_STATUS_TABS
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

    teacher_options = [
        {'id': teacher.id, 'name': _display_user_name(teacher)}
        for teacher in CustomUser.objects.filter(role='teacher', is_active=True).order_by('last_name', 'first_name', 'username')
    ]

    context = {
        'requests_list': requests_list,
        'stats': stats,
        'status_tabs': status_tabs,
        'current_status': current_status,
        'current_subject': current_subject,
        'current_subject_id': current_subject_id,
        'current_lead_form': current_lead_form,
        'search_query': search_query,
        'subjects': Subject.objects.order_by('name'),
        'lead_forms': lead_forms,
        'subject_stats': subject_stats,
        'teachers': teacher_options,
        'work_status_choices': TrialRequest.WORK_STATUS_CHOICES,
        'sla_minutes': CRM_RESPONSE_SLA_MINUTES,
    }
    return render(request, 'accounts/crm_dashboard.html', context)
