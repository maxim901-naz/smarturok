from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0018_balancetopuprequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='lesson_status',
            field=models.CharField(choices=[('pending', 'Ожидает отметки'), ('conducted', 'Проведён'), ('missed_teacher', 'Пропущен преподавателем'), ('missed_student', 'Пропущен учеником')], default='pending', max_length=20),
        ),
    ]
