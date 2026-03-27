import logging

from django.conf import settings
from django.core.mail import send_mail
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse

from .finance import get_teacher_payout_amount_for_lesson
from .models import BalanceTopUpRequest, BalanceTransaction, Lesson, TeacherFinanceEntry, TrialRequest

logger = logging.getLogger(__name__)


def _admin_recipients():
    raw_value = getattr(settings, 'ADMIN_EMAIL', '')
    if not raw_value:
        return []
    if isinstance(raw_value, (list, tuple)):
        return [str(email).strip() for email in raw_value if str(email).strip()]
    return [email.strip() for email in str(raw_value).split(',') if email.strip()]


def _site_base_url():
    hosts = getattr(settings, 'ALLOWED_HOSTS', []) or []
    for host in hosts:
        host = (host or '').strip()
        if not host or host in {'*', 'localhost', '127.0.0.1'}:
            continue
        if host.startswith('.'):
            host = host.lstrip('.')
        return f'https://{host}'
    return ''


def _send_admin_notification(subject, body):
    recipients = _admin_recipients()
    if not recipients:
        return
    try:
        send_mail(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            recipients,
            fail_silently=False,
        )
    except Exception:
        logger.exception('Failed to send admin notification email')


@receiver(post_save, sender=Lesson)
def deduct_balance_on_complete(sender, instance, created, **kwargs):
    if instance.lesson_status not in {'conducted', 'missed_student'}:
        return

    # Prevent duplicate debit/accrual for the same lesson.
    if BalanceTransaction.objects.filter(lesson=instance, direction='debit').exists():
        return

    student = instance.student
    if not student:
        return

    if student.balance > 0:
        student.balance -= 1
        student.save(update_fields=['balance'])

    note = 'Списание за завершенный урок'
    if instance.lesson_status == 'missed_student':
        note = 'Списание за пропуск учеником'

    BalanceTransaction.objects.create(
        user=student,
        lesson=instance,
        direction='debit',
        amount=1,
        note=note,
    )

    amount_value = get_teacher_payout_amount_for_lesson(
        instance.teacher,
        instance,
        subject=instance.subject,
    )
    subject_name = instance.subject.name if getattr(instance, 'subject', None) else ''
    if getattr(instance, 'student', None):
        student_name = instance.student.get_full_name() or instance.student.username
    else:
        student_name = ''

    TeacherFinanceEntry.objects.create(
        teacher=instance.teacher,
        lesson=instance,
        subject_name=subject_name,
        student_name=student_name,
        lesson_date=instance.date,
        lesson_time=instance.time,
        lesson_status=getattr(instance, 'lesson_status', '') or '',
        amount=amount_value,
    )


@receiver(post_save, sender=TrialRequest)
def notify_admin_on_new_trial_request(sender, instance, created, **kwargs):
    if not created:
        return

    admin_path = reverse('admin:accounts_trialrequest_change', args=[instance.pk])
    base_url = _site_base_url()
    admin_url = f'{base_url}{admin_path}' if base_url else admin_path
    subject_name = instance.subject.name if getattr(instance, 'subject', None) else 'не указан'
    body = (
        'Новая заявка на пробный урок.\n\n'
        f'Имя: {instance.name}\n'
        f'Телефон: {instance.phone}\n'
        f'Email: {instance.email}\n'
        f'Предмет: {subject_name}\n'
        f'Форма: {instance.lead_form or "trial"}\n'
        f'Время: {instance.created_at:%Y-%m-%d %H:%M:%S}\n\n'
        f'Открыть в админке: {admin_url}'
    )
    _send_admin_notification('SmartUrok: новая заявка на пробный урок', body)


@receiver(post_save, sender=BalanceTopUpRequest)
def notify_admin_on_new_topup_request(sender, instance, created, **kwargs):
    if not created:
        return

    admin_path = reverse('admin:accounts_balancetopuprequest_change', args=[instance.pk])
    base_url = _site_base_url()
    admin_url = f'{base_url}{admin_path}' if base_url else admin_path
    student_name = instance.user.get_full_name() or instance.user.username
    body = (
        'Новая заявка на пополнение баланса.\n\n'
        f'Ученик: {student_name}\n'
        f'Email: {instance.user.email}\n'
        f'Пакет: {instance.package} уроков\n'
        f'Комментарий: {instance.comment or "—"}\n'
        f'Время: {instance.created_at:%Y-%m-%d %H:%M:%S}\n\n'
        f'Открыть в админке: {admin_url}'
    )
    _send_admin_notification('SmartUrok: новая заявка на пополнение', body)
