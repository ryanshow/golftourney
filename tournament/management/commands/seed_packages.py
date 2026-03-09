from decimal import Decimal

from django.core.management.base import BaseCommand
from tournament.models import SponsorshipPackage, TournamentInfo, AddOn


PACKAGES = [
    {
        'name': 'Add-on Sponsor',
        'price': '0.00',
        'description': 'Select this package if you would like to like to become a food, cart, or individual hole sponsor without registering any players',
        'max_players': 0,
        'benefits': 'No direct benefits. Select an add-on package',
        'sort_order': 0,
    },
    {
        'name': 'Single Player',
        'price': '150.00',
        'description': 'Show your support with a single player sponsorship!',
        'max_players': 1,
        'benefits': (
            'Golf Entry and Box Lunch\r\n'
            '1 Mulligan\r\n'
            '5 Raffle Tickets\r\n'
            '1 Beverage Ticket'
        ),
        'sort_order': 1,
        'sponsor_tier': 'other',
    },
    {
        'name': 'Bronze Sponsor',
        'price': '500.00',
        'description': 'Elevate your visibility with a bronze sponsorship!',
        'max_players': 2,
        'benefits': (
            'Hole Sponsor Sign\r\n'
            '2 Golf Entries and Box Lunches\r\n'
            '4 Mulligans\r\n'
            '50 Raffle Tickets\r\n'
            '4 Beverage Tickets'
        ),
        'sort_order': 2,
        'logo_upload': True,
        'sponsor_tier': 'bronze',
    },
    {
        'name': 'Silver Sponsor',
        'price': '750.00',
        'description': 'Bring your whole team! This sponsorship level includes entries for all 4 players.',
        'max_players': 4,
        'benefits': (
            '2 Hole Sponsor Signs\r\n'
            '4 Golf Entries and Box Lunches\r\n'
            '8 Mulligans\r\n'
            '100 Raffle Tickets\r\n'
            '8 Beverage Tickets'
        ),
        'sort_order': 3,
        'logo_upload': True,
        'sponsor_tier': 'silver',
    },
    {
        'name': 'Gold Sponsor',
        'price': '1500.00',
        'description': 'Bring two teams!',
        'max_players': 8,
        'benefits': (
            '4 Hole Sponsor Signs\r\n'
            '8 Golf Entries and Boxed Lunches\r\n'
            '16 Mulligans\r\n'
            '200 Raffle Tickets\r\n'
            '16 Beverage Tickets'
        ),
        'sort_order': 4,
        'logo_upload': True,
        'sponsor_tier': 'gold',
    },
    {
        'name': '*NEW* Title Sponsor',
        'price': '1000.00',
        'description': "Premier sponsorship opportunity! Show your support even if you're unable to join us on the green.",
        'max_players': 0,
        'benefits': (
            '2 Large Tee Signs at Hole of Choice\r\n'
            'First Choice Placement of Any Other Signage\r\n'
            'Top Billing on Sponsor Poster\r\n'
            'Logo Added in Correspondences\r\n'
            'Opportunity to Speak at the Opening'
        ),
        'sort_order': 5,
        'logo_upload': True,
        'sponsor_tier': 'gold',
    },
]

ADDONS = [
    {
        'name': 'Player Package',
        'description': '15 Raffle Tickets\r\n2 Beverage Tickets',
        'price': Decimal('40.00'),
        'sort_order': 1,
    },
    {
        'name': 'Cart Sponsor',
        'description': 'Logo on a golf cart',
        'price': Decimal('250.00'),
        'sort_order': 2,
    },
    {
        'name': 'Food Sponsor',
        'description': 'Recognition on display with lunch',
        'price': Decimal('300.00'),
        'sort_order': 3,
    },
    {
        'name': 'Tee Sign Sponsor',
        'description': 'Have your logo displayed at a tee',
        'price': Decimal('200.00'),
        'sort_order': 4,
    },
]

TOURNAMENT_INFO = {
    'tournament_name': 'Clay Elementary School Golf Tournament',
    'date': '2026-05-01',
    'location': 'Ridge Creek Dinuba Golf Club',
    'description': (
        'Join us for a day of golf to support Clay Elementary School. '
        'All funds raised go directly towards funding Parent Club initiatives, '
        'including educational enrichment opportunities, classroom supplies, '
        'field trips, athletics, and a host of other needs of Clay School.'
    ),
    'entry_deadline': '2026-04-24'
}


class Command(BaseCommand):
    help = 'Seed the database with default sponsorship packages and tournament info'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Delete existing sponsorship packages and add-ons before seeding',
        )

    def handle(self, *args, **options):
        if options['reset']:
            count, _ = SponsorshipPackage.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing packages.'))
            count, _ = AddOn.objects.all().delete()
            self.stdout.write(self.style.WARNING(f'Deleted {count} existing add-ons.'))

        created_count = 0
        updated_count = 0

        for pkg_data in PACKAGES:
            obj, created = SponsorshipPackage.objects.update_or_create(
                name=pkg_data['name'],
                defaults=pkg_data,
            )
            if created:
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'  Created: {obj}'))
            else:
                updated_count += 1
                self.stdout.write(f'  Updated: {obj}')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nDone! Created {created_count}, updated {updated_count} sponsorship packages.'
            )
        )

        # Seed add-ons
        addon_created = 0
        addon_updated = 0
        for data in ADDONS:
            obj, created = AddOn.objects.update_or_create(name=data['name'], defaults=data)
            if created:
                addon_created += 1
                self.stdout.write(self.style.SUCCESS(f'  Created add-on: {obj.name}'))
            else:
                addon_updated += 1
                self.stdout.write(f'  Updated add-on: {obj.name}')
        self.stdout.write(
            self.style.SUCCESS(f'Add-ons done! Created {addon_created}, updated {addon_updated}.')
        )

        # Seed TournamentInfo singleton
        info = TournamentInfo.get_instance()
        for field, value in TOURNAMENT_INFO.items():
            setattr(info, field, value)
        info.save()
        self.stdout.write(self.style.SUCCESS('Tournament info seeded.'))
