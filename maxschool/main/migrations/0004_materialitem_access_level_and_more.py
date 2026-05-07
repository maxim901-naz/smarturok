from django.db import migrations, models
from django.db.models import F


def sync_material_publication_state(apps, schema_editor):
    MaterialItem = apps.get_model('main', 'MaterialItem')
    MaterialItem.objects.filter(is_published=False).update(status='draft')
    MaterialItem.objects.filter(is_published=True, published_at__isnull=True).update(
        published_at=F('created_at')
    )


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0003_materials_subject_grade'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialitem',
            name='access_level',
            field=models.CharField(
                choices=[
                    ('public', 'Доступно всем'),
                    ('authenticated', 'Только авторизованным'),
                    ('paid', 'Только оплатившим пакет'),
                ],
                db_index=True,
                default='public',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='article_markdown',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='content_type',
            field=models.CharField(
                choices=[
                    ('video', 'Видео'),
                    ('article', 'Статья (Markdown)'),
                    ('pdf', 'PDF/файл'),
                    ('test', 'Тест'),
                ],
                db_index=True,
                default='pdf',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='exam_type',
            field=models.CharField(
                choices=[
                    ('general', 'Обычный материал'),
                    ('oge', 'ОГЭ'),
                    ('ege', 'ЕГЭ'),
                    ('school', 'Школьная работа'),
                    ('custom', 'Произвольный формат'),
                ],
                db_index=True,
                default='general',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='meta_description',
            field=models.CharField(blank=True, max_length=160),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='published_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='slug',
            field=models.SlugField(
                allow_unicode=True,
                blank=True,
                max_length=180,
                null=True,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Черновик'),
                    ('review', 'На проверке'),
                    ('published', 'Опубликовано'),
                    ('archived', 'В архиве'),
                ],
                db_index=True,
                default='published',
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='test_payload',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='video_url',
            field=models.URLField(blank=True),
        ),
        migrations.RunPython(sync_material_publication_state, noop_reverse),
        migrations.AddIndex(
            model_name='materialitem',
            index=models.Index(
                fields=['status', 'content_type'],
                name='main_materi_status_0c6a3c_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='materialitem',
            index=models.Index(
                fields=['exam_type', 'created_at'],
                name='main_materi_exam_ty_8addbf_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='materialitem',
            index=models.Index(
                fields=['published_at'],
                name='main_materi_publish_bb08ee_idx',
            ),
        ),
    ]
