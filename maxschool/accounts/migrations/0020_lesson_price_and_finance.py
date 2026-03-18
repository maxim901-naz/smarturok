from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0019_lesson_status'),
    ]

    operations = [
        migrations.AddField(
            model_name='lesson',
            name='price_per_lesson',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.CreateModel(
            name='TeacherFinanceEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('amount', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='finance_entries', to='accounts.lesson')),
                ('teacher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='finance_entries', to='accounts.customuser')),
            ],
        ),
    ]
