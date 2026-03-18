from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0020_lesson_price_and_finance'),
    ]

    operations = [
        migrations.AddField(
            model_name='subject',
            name='price_per_lesson',
            field=models.PositiveIntegerField(default=0),
        ),
    ]
