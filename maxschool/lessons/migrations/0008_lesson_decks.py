import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0048_trialrequest_created_student'),
        ('lessons', '0007_teacheravailability_constraints'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='LessonDeck',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('grade', models.PositiveSmallIntegerField(blank=True, null=True, verbose_name='Класс')),
                ('title', models.CharField(max_length=180, verbose_name='Название урока')),
                ('topic', models.CharField(blank=True, default='', max_length=180, verbose_name='Тема')),
                ('description', models.TextField(blank=True, default='', verbose_name='Краткое описание')),
                ('sort_order', models.PositiveIntegerField(default=0, verbose_name='Порядок')),
                ('is_active', models.BooleanField(default=True, verbose_name='Активный комплект')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('subject', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lesson_decks', to='accounts.subject', verbose_name='Предмет')),
            ],
            options={
                'verbose_name': 'Комплект карточек урока',
                'verbose_name_plural': 'Комплекты карточек уроков',
                'ordering': ['subject__name', 'grade', 'sort_order', 'title'],
            },
        ),
        migrations.CreateModel(
            name='LessonCard',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order', models.PositiveIntegerField(default=1, verbose_name='Номер карточки')),
                ('card_type', models.CharField(choices=[('title', 'Заставка'), ('theory', 'Теория'), ('example', 'Пример'), ('task', 'Задание'), ('hint', 'Подсказка'), ('answer', 'Ответ'), ('question', 'Вопрос'), ('homework', 'Домашнее задание'), ('image', 'Картинка'), ('video', 'Видео')], default='task', max_length=16, verbose_name='Тип')),
                ('title', models.CharField(blank=True, default='', max_length=180, verbose_name='Заголовок')),
                ('body', models.TextField(blank=True, default='', verbose_name='Текст карточки')),
                ('image', models.ImageField(blank=True, null=True, upload_to='lesson_cards/images/%Y/%m/', verbose_name='Изображение')),
                ('attachment', models.FileField(blank=True, null=True, upload_to='lesson_cards/files/%Y/%m/', verbose_name='Файл')),
                ('video_url', models.URLField(blank=True, default='', verbose_name='Ссылка на видео')),
                ('teacher_notes', models.TextField(blank=True, default='', verbose_name='Заметки для учителя')),
                ('is_active', models.BooleanField(default=True, verbose_name='Показывать в уроке')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('deck', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cards', to='lessons.lessondeck', verbose_name='Комплект')),
            ],
            options={
                'verbose_name': 'Карточка урока',
                'verbose_name_plural': 'Карточки урока',
                'ordering': ['deck', 'order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='LessonDeckSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('current_card', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='active_lesson_sessions', to='lessons.lessoncard', verbose_name='Текущая карточка')),
                ('deck', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='lesson_sessions', to='lessons.lessondeck', verbose_name='Выбранный комплект')),
                ('lesson', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='deck_session', to='accounts.lesson', verbose_name='Урок')),
                ('updated_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='updated_lesson_card_sessions', to=settings.AUTH_USER_MODEL, verbose_name='Кто изменил')),
            ],
            options={
                'verbose_name': 'Карточки в уроке',
                'verbose_name_plural': 'Карточки в уроках',
            },
        ),
        migrations.AddIndex(
            model_name='lessondeck',
            index=models.Index(fields=['is_active', 'subject', 'grade'], name='less_deck_active_subj_grade'),
        ),
        migrations.AddIndex(
            model_name='lessondeck',
            index=models.Index(fields=['sort_order', 'title'], name='less_deck_sort_title'),
        ),
        migrations.AddIndex(
            model_name='lessoncard',
            index=models.Index(fields=['deck', 'order'], name='less_card_deck_order'),
        ),
        migrations.AddIndex(
            model_name='lessoncard',
            index=models.Index(fields=['card_type', 'is_active'], name='less_card_type_active'),
        ),
    ]
