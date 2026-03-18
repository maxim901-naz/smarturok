from django.db import migrations, models


def create_default_categories(apps, schema_editor):
    MaterialCategory = apps.get_model('main', 'MaterialCategory')
    defaults = [
        ('Учебники', 'uchebniki', 'Электронные учебники и пособия', 10),
        ('ОГЭ', 'oge', 'Материалы для подготовки к ОГЭ', 20),
        ('ЕГЭ', 'ege', 'Материалы для подготовки к ЕГЭ', 30),
        ('МЦКО', 'mcko', 'Диагностики и тесты МЦКО', 40),
        ('ВПР', 'vpr', 'Материалы для подготовки к ВПР', 50),
    ]
    for title, slug, desc, order in defaults:
        MaterialCategory.objects.get_or_create(
            slug=slug,
            defaults={'title': title, 'description': desc, 'sort_order': order, 'is_active': True},
        )


def delete_default_categories(apps, schema_editor):
    MaterialCategory = apps.get_model('main', 'MaterialCategory')
    MaterialCategory.objects.filter(slug__in=['uchebniki', 'oge', 'ege', 'mcko', 'vpr']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0001_review'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaterialCategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=120)),
                ('slug', models.SlugField(max_length=120, unique=True)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.PositiveIntegerField(default=0)),
            ],
            options={
                'ordering': ['sort_order', 'title'],
            },
        ),
        migrations.CreateModel(
            name='MaterialItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=160)),
                ('description', models.TextField(blank=True)),
                ('file', models.FileField(blank=True, null=True, upload_to='materials/')),
                ('external_url', models.URLField(blank=True)),
                ('is_published', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('category', models.ForeignKey(on_delete=models.deletion.CASCADE, related_name='materials', to='main.materialcategory')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.RunPython(create_default_categories, delete_default_categories),
    ]
