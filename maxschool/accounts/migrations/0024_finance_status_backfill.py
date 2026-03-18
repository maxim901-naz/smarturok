from django.db import migrations


def backfill_status(apps, schema_editor):
    TeacherFinanceEntry = apps.get_model('accounts', 'TeacherFinanceEntry')
    TeacherFinanceEntry.objects.filter(payout_status__isnull=True).update(payout_status='accrued')
    TeacherFinanceEntry.objects.filter(payout_status='').update(payout_status='accrued')


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0023_finance_payout_status'),
    ]

    operations = [
        migrations.RunPython(backfill_status, migrations.RunPython.noop),
    ]
