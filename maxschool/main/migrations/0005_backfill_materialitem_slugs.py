from django.db import migrations
from django.db.models import Q
from django.utils.text import slugify


def backfill_material_slugs(apps, schema_editor):
    MaterialItem = apps.get_model('main', 'MaterialItem')

    used_slugs = set(
        MaterialItem.objects.exclude(slug__isnull=True).exclude(slug='').values_list('slug', flat=True)
    )

    items = MaterialItem.objects.filter(Q(slug__isnull=True) | Q(slug=''))
    for item in items.order_by('id'):
        base_slug = slugify(item.title, allow_unicode=True) or f'material-{item.pk}'
        slug_candidate = base_slug
        suffix = 2
        while slug_candidate in used_slugs:
            slug_candidate = f'{base_slug}-{suffix}'
            suffix += 1

        item.slug = slug_candidate
        item.save(update_fields=['slug'])
        used_slugs.add(slug_candidate)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_materialitem_access_level_and_more'),
    ]

    operations = [
        migrations.RunPython(backfill_material_slugs, noop_reverse),
    ]
