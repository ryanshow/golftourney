from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tournament', '0006_add_package_sponsor_tier'),
    ]

    operations = [
        migrations.CreateModel(
            name='RaffleDonation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField(max_length=254)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('company_name', models.CharField(blank=True, max_length=200, verbose_name='Company / Organization')),
                ('donation_description', models.TextField(
                    help_text='Describe the item(s) you would like to donate for the raffle.',
                    verbose_name='Donation Description',
                )),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'verbose_name': 'Raffle Donation',
                'verbose_name_plural': 'Raffle Donations',
                'ordering': ['-created_at'],
            },
        ),
    ]
