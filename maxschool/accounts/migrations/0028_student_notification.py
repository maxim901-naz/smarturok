from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0027_finance_lesson_status"),
    ]

    operations = [
        migrations.CreateModel(
            name="StudentNotification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("message", models.CharField(max_length=255)),
                ("is_read", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("student", models.ForeignKey(on_delete=models.deletion.CASCADE, related_name="student_notifications", to="accounts.customuser")),
            ],
        ),
    ]
