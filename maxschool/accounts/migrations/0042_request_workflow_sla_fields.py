from django.conf import settings
from django.db import migrations, models
from django.db.models import F
import django.db.models.deletion


def backfill_request_workflow(apps, schema_editor):
    TrialRequest = apps.get_model('accounts', 'TrialRequest')
    BalanceTopUpRequest = apps.get_model('accounts', 'BalanceTopUpRequest')

    # Trial requests: converted -> done
    TrialRequest.objects.filter(is_converted=True).update(work_status='done')
    TrialRequest.objects.filter(
        is_converted=True,
        first_response_at__isnull=True,
    ).update(first_response_at=F('created_at'))
    TrialRequest.objects.filter(
        is_converted=True,
        closed_at__isnull=True,
    ).update(closed_at=F('created_at'))

    # Top-up requests: map moderation/payment status into workflow status.
    BalanceTopUpRequest.objects.filter(status='pending').update(work_status='new')
    BalanceTopUpRequest.objects.filter(status='approved').update(work_status='done')
    BalanceTopUpRequest.objects.filter(status='rejected').update(work_status='rejected')

    BalanceTopUpRequest.objects.filter(
        status__in=['approved', 'rejected'],
        first_response_at__isnull=True,
    ).update(first_response_at=F('created_at'))
    BalanceTopUpRequest.objects.filter(
        status__in=['approved', 'rejected'],
        closed_at__isnull=True,
    ).update(closed_at=F('created_at'))


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0041_customuser_teacher_payout_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='balancetopuprequest',
            name='assigned_admin',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'is_staff': True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_topup_requests',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='balancetopuprequest',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='balancetopuprequest',
            name='first_response_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='balancetopuprequest',
            name='work_status',
            field=models.CharField(
                choices=[
                    ('new', 'Новая'),
                    ('in_progress', 'В работе'),
                    ('done', 'Закрыта'),
                    ('rejected', 'Отклонена'),
                ],
                db_index=True,
                default='new',
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='assigned_admin',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'is_staff': True},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='assigned_trial_requests',
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='closed_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='first_response_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='work_status',
            field=models.CharField(
                choices=[
                    ('new', 'Новая'),
                    ('in_progress', 'В работе'),
                    ('done', 'Закрыта'),
                    ('rejected', 'Отклонена'),
                ],
                db_index=True,
                default='new',
                max_length=20,
            ),
        ),
        migrations.RunPython(backfill_request_workflow, noop),
    ]
