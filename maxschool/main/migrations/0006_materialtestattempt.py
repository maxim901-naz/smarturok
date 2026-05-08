from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0005_backfill_materialitem_slugs'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='MaterialTestAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_key', models.CharField(blank=True, default='', max_length=64)),
                ('attempt_no', models.PositiveIntegerField(default=1)),
                ('max_points', models.PositiveIntegerField(default=0)),
                ('score_points', models.DecimalField(decimal_places=2, default=0, max_digits=8)),
                ('score_percent', models.DecimalField(decimal_places=2, default=0, max_digits=5)),
                ('passed', models.BooleanField(default=False)),
                ('duration_seconds', models.PositiveIntegerField(default=0)),
                ('answers_payload', models.JSONField(blank=True, default=dict)),
                ('result_payload', models.JSONField(blank=True, default=dict)),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('material', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_attempts', to='main.materialitem')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='material_test_attempts', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-submitted_at'],
            },
        ),
        migrations.AddIndex(
            model_name='materialtestattempt',
            index=models.Index(fields=['material', 'submitted_at'], name='main_mtat_mat_sub_idx'),
        ),
        migrations.AddIndex(
            model_name='materialtestattempt',
            index=models.Index(fields=['user', 'submitted_at'], name='main_mtat_usr_sub_idx'),
        ),
        migrations.AddIndex(
            model_name='materialtestattempt',
            index=models.Index(fields=['material', 'user', 'attempt_no'], name='main_mtat_mat_usr_no_idx'),
        ),
    ]
