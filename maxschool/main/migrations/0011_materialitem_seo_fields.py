from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0010_homesuccessstory'),
    ]

    operations = [
        migrations.AddField(
            model_name='materialitem',
            name='faq_items',
            field=models.TextField(blank=True, default='', help_text='Optional FAQ. One question per line: Question | Answer.'),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='seo_focus_query',
            field=models.CharField(blank=True, default='', help_text='Internal note: main search query for this material.', max_length=160),
        ),
        migrations.AddField(
            model_name='materialitem',
            name='seo_title',
            field=models.CharField(blank=True, default='', help_text='Search title. Leave empty to use the material title.', max_length=90),
        ),
    ]
