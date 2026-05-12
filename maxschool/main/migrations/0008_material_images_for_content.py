from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0007_materialtest_materialtestquestion_materialtestoption_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaterialImage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('image', models.ImageField(upload_to='materials/images/%Y/%m/')),
                ('title', models.CharField(blank=True, max_length=120)),
                ('alt_text', models.CharField(blank=True, max_length=255)),
                ('usage', models.CharField(choices=[('article', 'Article'), ('test', 'Test'), ('both', 'Article and test')], db_index=True, default='both', max_length=16)),
                ('sort_order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='images', to='main.materialitem')),
            ],
            options={
                'ordering': ['sort_order', 'id'],
            },
        ),
        migrations.AddField(
            model_name='materialtestquestion',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='materials/tests/questions/'),
        ),
        migrations.AddField(
            model_name='materialtestquestion',
            name='image_alt',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
        migrations.AddField(
            model_name='materialtestoption',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='materials/tests/options/'),
        ),
        migrations.AddField(
            model_name='materialtestoption',
            name='image_alt',
            field=models.CharField(blank=True, default='', max_length=255),
        ),
    ]
