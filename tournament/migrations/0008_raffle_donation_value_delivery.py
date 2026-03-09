from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0007_add_raffle_donation'),
    ]

    operations = [
        migrations.AddField(
            model_name='raffledonation',
            name='estimated_value',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Approximate retail value of the donated item(s).',
                max_digits=8,
                null=True,
                verbose_name='Estimated Value ($)',
            ),
        ),
        migrations.AddField(
            model_name='raffledonation',
            name='delivery_method',
            field=models.CharField(
                choices=[
                    ('drop_off', 'I will drop it off at Clay Elementary School'),
                    ('pick_up', 'Please have the tournament chair pick it up'),
                ],
                default='drop_off',
                max_length=20,
                verbose_name='Delivery Method',
            ),
            preserve_default=False,
        ),
    ]
