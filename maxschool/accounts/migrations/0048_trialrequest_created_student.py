from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('accounts', '0047_trialrequest_crm_followup'),
    ]

    operations = [
        migrations.AddField(
            model_name='trialrequest',
            name='created_student',
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={'role': 'student'},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='created_from_trial_requests',
                to=settings.AUTH_USER_MODEL,
                verbose_name='Созданный ученик',
            ),
        ),
    ]
