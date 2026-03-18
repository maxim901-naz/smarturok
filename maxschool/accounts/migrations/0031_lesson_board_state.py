from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0030_subject_discounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='board_state',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='lesson',
            name='board_state_updated_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
