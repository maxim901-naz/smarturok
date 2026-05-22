from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0009_materialitem_navigation_and_views"),
    ]

    operations = [
        migrations.CreateModel(
            name="HomeSuccessStory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=120)),
                ("achievement", models.CharField(max_length=180)),
                ("story_text", models.TextField()),
                ("image", models.ImageField(blank=True, null=True, upload_to="home_success/")),
                ("cta_text", models.CharField(blank=True, default="Подробнее", max_length=80)),
                ("cta_url", models.CharField(blank=True, default="", max_length=300)),
                ("sort_order", models.PositiveIntegerField(db_index=True, default=0)),
                ("is_published", models.BooleanField(db_index=True, default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["sort_order", "-created_at"],
            },
        ),
    ]
