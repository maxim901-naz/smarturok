from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0046_trialrequest_student_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='trialrequest',
            name='work_status',
            field=models.CharField(
                choices=[
                    ('new', 'Новая'),
                    ('in_progress', 'В работе'),
                    ('no_answer', 'Не дозвонились'),
                    ('waiting', 'Ждём ответа'),
                    ('trial_scheduled', 'Пробный назначен'),
                    ('trial_done', 'Пробный проведён'),
                    ('paid', 'Оплатил'),
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
            name='next_contact_at',
            field=models.DateTimeField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='next_contact_note',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.CreateModel(
            name='TrialRequestNote',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('note', models.TextField(verbose_name='Комментарий')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='Создано')),
                (
                    'author',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='trial_request_notes',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Автор',
                    ),
                ),
                (
                    'trial_request',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='crm_notes',
                        to='accounts.trialrequest',
                        verbose_name='Заявка',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Комментарий к заявке',
                'verbose_name_plural': 'Комментарии к заявкам',
                'ordering': ('-created_at',),
            },
        ),
    ]
