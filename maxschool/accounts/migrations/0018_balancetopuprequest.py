from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0017_balancetransaction'),
    ]

    operations = [
        migrations.CreateModel(
            name='BalanceTopUpRequest',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('package', models.PositiveIntegerField(choices=[(4, '4 урока'), (8, '8 уроков'), (12, '12 уроков')])),
                ('comment', models.CharField(blank=True, max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Ожидает'), ('approved', 'Одобрено'), ('rejected', 'Отклонено')], default='pending', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='balance_topup_requests', to='accounts.customuser')),
            ],
        ),
    ]
