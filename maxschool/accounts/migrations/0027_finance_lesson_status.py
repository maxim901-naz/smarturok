from django.db import migrations, models


def backfill_lesson_status(apps, schema_editor):
    TeacherFinanceEntry = apps.get_model("accounts", "TeacherFinanceEntry")
    for entry in TeacherFinanceEntry.objects.select_related("lesson"):
        if not entry.lesson_status and entry.lesson_id and getattr(entry.lesson, "lesson_status", None):
            entry.lesson_status = entry.lesson.lesson_status or ""
            entry.save(update_fields=["lesson_status"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0026_finance_snapshot"),
    ]

    operations = [
        migrations.AddField(
            model_name="teacherfinanceentry",
            name="lesson_status",
            field=models.CharField(blank=True, default="", max_length=20),
        ),
        migrations.RunPython(backfill_lesson_status, migrations.RunPython.noop),
    ]
