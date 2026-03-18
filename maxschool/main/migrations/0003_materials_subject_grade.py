from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0002_materials'),
        ('accounts', '0030_subject_discounts'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialitem',
            name='subject',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='accounts.subject'),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='grade',
            field=models.PositiveSmallIntegerField(blank=True, null=True),
        ),
    ]
