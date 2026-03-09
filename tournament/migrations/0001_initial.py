from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='SponsorshipPackage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('price', models.DecimalField(decimal_places=2, max_digits=10)),
                ('description', models.TextField()),
                ('max_players', models.IntegerField(default=0, help_text='Number of player entries included (0 = none)')),
                ('benefits', models.TextField(help_text='List of benefits, one per line')),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['sort_order', 'price'],
            },
        ),
        migrations.CreateModel(
            name='Sponsor',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('logo', models.ImageField(blank=True, null=True, upload_to='sponsor_logos/')),
                ('website_url', models.URLField(blank=True, null=True)),
                ('tier', models.CharField(
                    choices=[('gold', 'Gold'), ('silver', 'Silver'), ('bronze', 'Bronze'), ('other', 'Other')],
                    default='other',
                    max_length=20,
                )),
                ('is_active', models.BooleanField(default=True)),
                ('sort_order', models.IntegerField(default=0)),
            ],
            options={
                'ordering': ['tier', 'sort_order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='TournamentInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tournament_name', models.CharField(default='Clay Elementary School Golf Tournament', max_length=300)),
                ('date', models.DateField(blank=True, null=True)),
                ('location', models.CharField(blank=True, max_length=300)),
                ('description', models.TextField(blank=True)),
                ('entry_deadline', models.DateField(blank=True, null=True)),
                ('contact_email', models.EmailField(blank=True)),
                ('contact_phone', models.CharField(blank=True, max_length=20)),
            ],
            options={
                'verbose_name': 'Tournament Info',
                'verbose_name_plural': 'Tournament Info',
            },
        ),
        migrations.CreateModel(
            name='Registration',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=100)),
                ('last_name', models.CharField(max_length=100)),
                ('email', models.EmailField()),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('company_org', models.CharField(blank=True, max_length=200, verbose_name='Company / Organization')),
                ('payment_method', models.CharField(
                    choices=[('square', 'Credit Card (Square)'), ('check', 'Pay by Check')],
                    max_length=20,
                )),
                ('payment_status', models.CharField(
                    choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
                    default='pending',
                    max_length=20,
                )),
                ('square_payment_id', models.CharField(blank=True, max_length=200)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('notes', models.TextField(blank=True, help_text='Any additional notes or special requests')),
                ('sponsorship_package', models.ForeignKey(
                    on_delete=django.db.models.deletion.PROTECT,
                    related_name='registrations',
                    to='tournament.sponsorshippackage',
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
