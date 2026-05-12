from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0008_material_images_for_content"),
    ]

    operations = [
        migrations.AddField(
            model_name="materialitem",
            name="related_test",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"content_type": "test"},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="theory_materials",
                to="main.materialitem",
            ),
        ),
        migrations.AddField(
            model_name="materialitem",
            name="related_theory",
            field=models.ForeignKey(
                blank=True,
                limit_choices_to={"content_type__in": ("article", "video", "pdf")},
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="practice_materials",
                to="main.materialitem",
            ),
        ),
        migrations.AddField(
            model_name="materialitem",
            name="task_number",
            field=models.PositiveSmallIntegerField(blank=True, db_index=True, null=True),
        ),
        migrations.AddField(
            model_name="materialitem",
            name="views_count",
            field=models.PositiveIntegerField(db_index=True, default=0),
        ),
    ]

