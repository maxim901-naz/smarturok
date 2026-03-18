from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0029_subject_image"),
    ]

    operations = [
        migrations.AddField(
            model_name="subject",
            name="discount_4",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subject",
            name="discount_8",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subject",
            name="discount_12",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subject",
            name="discount_28",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subject",
            name="discount_64",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="subject",
            name="discount_128",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
