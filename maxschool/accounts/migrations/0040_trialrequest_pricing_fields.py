from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0039_customuser_teacher_profile_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='trialrequest',
            name='lead_form',
            field=models.CharField(blank=True, default='', max_length=64),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='pricing_discount_percent',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='pricing_lessons_count',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='pricing_old_price',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='pricing_subject_name',
            field=models.CharField(blank=True, default='', max_length=120),
        ),
        migrations.AddField(
            model_name='trialrequest',
            name='pricing_total_price',
            field=models.PositiveIntegerField(blank=True, null=True),
        ),
    ]

