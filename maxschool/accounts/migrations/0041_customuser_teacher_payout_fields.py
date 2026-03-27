from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0040_trialrequest_pricing_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='customuser',
            name='teacher_payout_fixed',
            field=models.PositiveIntegerField(
                blank=True,
                help_text='If set, this value is used instead of payout percent.',
                null=True,
                verbose_name='Teacher fixed payout per lesson',
            ),
        ),
        migrations.AddField(
            model_name='customuser',
            name='teacher_payout_percent',
            field=models.PositiveSmallIntegerField(
                default=50,
                help_text='Teacher payout as percent of student lesson price if fixed payout is empty.',
                verbose_name='Teacher payout percent, %',
            ),
        ),
    ]
