from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0021_subject_price'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='subjects_taught',
            field=models.ManyToManyField(blank=True, related_name='teachers', to='accounts.subject', verbose_name='Преподаваемые предметы'),
        ),
    ]
