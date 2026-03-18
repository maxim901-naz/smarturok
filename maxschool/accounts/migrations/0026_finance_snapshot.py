from django.db import migrations, models


def backfill_finance_snapshot(apps, schema_editor):
    TeacherFinanceEntry = apps.get_model("accounts", "TeacherFinanceEntry")
    for entry in TeacherFinanceEntry.objects.select_related("lesson", "lesson__subject", "lesson__student"):
        if entry.lesson_id:
            lesson = entry.lesson
            if not entry.subject_name and getattr(lesson, "subject", None):
                entry.subject_name = lesson.subject.name or ""
            if not entry.student_name and getattr(lesson, "student", None):
                student = lesson.student
                full_name = getattr(student, "get_full_name", None)
                if callable(full_name):
                    entry.student_name = full_name() or student.username
                else:
                    entry.student_name = student.username
            if not entry.lesson_date:
                entry.lesson_date = lesson.date
            if not entry.lesson_time:
                entry.lesson_time = lesson.time
            entry.save(update_fields=["subject_name", "student_name", "lesson_date", "lesson_time"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0025_teacher_notification"),
    ]

    operations = [
        migrations.AddField(
            model_name="teacherfinanceentry",
            name="lesson_date",
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="teacherfinanceentry",
            name="lesson_time",
            field=models.TimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="teacherfinanceentry",
            name="student_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.AddField(
            model_name="teacherfinanceentry",
            name="subject_name",
            field=models.CharField(blank=True, default="", max_length=255),
        ),
        migrations.RunPython(backfill_finance_snapshot, migrations.RunPython.noop),
    ]
