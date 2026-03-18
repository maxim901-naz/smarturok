from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0028_student_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="image",
            field=models.ImageField(blank=True, null=True, upload_to="subjects/"),
        ),
    ]
