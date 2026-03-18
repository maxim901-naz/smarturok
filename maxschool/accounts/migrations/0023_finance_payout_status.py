from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0022_subjects_taught'),
    ]

    operations = [
        migrations.AddField(
            model_name='teacherfinanceentry',
            name='payout_status',
            field=models.CharField(choices=[('accrued', 'Начислено'), ('paid', 'Выплачено')], default='accrued', max_length=10),
        ),
    ]
