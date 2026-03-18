from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0016_lesson_is_completed'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceTransaction',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('direction', models.CharField(choices=[('credit', 'Пополнение'), ('debit', 'Списание')], max_length=10)),
                ('amount', models.PositiveIntegerField()),
                ('note', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('lesson', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='balance_transactions', to='accounts.lesson')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='balance_transactions', to='accounts.customuser')),
            ],
        ),
    ]
