from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0045_trialrequest_promo_interest"),
    ]

    operations = [
        migrations.AddField(
            model_name="trialrequest",
            name="student_name",
            field=models.CharField(blank=True, default="", max_length=100),
        ),
    ]
