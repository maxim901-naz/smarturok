from django.db import migrations, models
from django.db.models import Q


class Migration(migrations.Migration):

    dependencies = [
        ('lessons', '0006_lessonbooking_is_recurring'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='teacheravailability',
            unique_together=set(),
        ),
        migrations.AddConstraint(
            model_name='teacheravailability',
            constraint=models.UniqueConstraint(
                fields=('teacher', 'date', 'time'),
                condition=Q(is_recurring=False),
                name='unique_one_time_slot',
            ),
        ),
        migrations.AddConstraint(
            model_name='teacheravailability',
            constraint=models.UniqueConstraint(
                fields=('teacher', 'weekday', 'time'),
                condition=Q(is_recurring=True),
                name='unique_recurring_slot',
            ),
        ),
    ]
