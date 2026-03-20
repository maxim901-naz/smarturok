from decimal import Decimal

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0038_studentvacation'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='achievements',
            field=models.TextField(blank=True, default='', verbose_name='Достижения'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='bio',
            field=models.TextField(blank=True, default='', verbose_name='О преподавателе'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='education',
            field=models.TextField(blank=True, default='', verbose_name='Образование'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='experience_years',
            field=models.PositiveSmallIntegerField(default=5, verbose_name='Опыт (лет)'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='methodology',
            field=models.TextField(blank=True, default='', verbose_name='Методика преподавания'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='rating',
            field=models.DecimalField(decimal_places=1, default=Decimal('5.0'), max_digits=2, verbose_name='Рейтинг'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='reviews_count',
            field=models.PositiveIntegerField(default=24, verbose_name='Количество отзывов'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='students_count',
            field=models.PositiveIntegerField(default=50, verbose_name='Количество учеников'),
        ),
        migrations.AddField(
            model_name='customuser',
            name='success_rate',
            field=models.PositiveSmallIntegerField(default=95, verbose_name='Успешных работ (%)'),
        ),
    ]
