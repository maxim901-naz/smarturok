from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0031_lesson_board_state'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='time_zone',
            field=models.CharField(default='Europe/Moscow', max_length=64, verbose_name='Часовой пояс'),
        ),
    ]
