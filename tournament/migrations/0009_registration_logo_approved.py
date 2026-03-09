from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0008_raffle_donation_value_delivery'),
    ]

    operations = [
        migrations.AddField(
            model_name='registration',
            name='logo_approved',
            field=models.BooleanField(
                default=False,
                help_text='Approve this logo to display it on the tournament home page.',
            ),
        ),
    ]
