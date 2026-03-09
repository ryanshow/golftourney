from django.db import models
from django.core.exceptions import ValidationError


class SponsorshipPackage(models.Model):
    name = models.CharField(max_length=200)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    max_players = models.IntegerField(default=0, help_text="Number of player entries included (0 = none)")
    benefits = models.TextField(help_text="List of benefits, one per line")
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    logo_upload = models.BooleanField(
        default=False,
        help_text="Allow registrants to upload a company logo with this package"
    )
    SPONSOR_TIER_CHOICES = [
        ('', 'None (no logo display)'),
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('other', 'Community Supporters'),
    ]
    sponsor_tier = models.CharField(
        max_length=20,
        choices=SPONSOR_TIER_CHOICES,
        blank=True,
        default='',
        help_text="Tier under which registrant logos are displayed on the home page"
    )

    class Meta:
        ordering = ['sort_order', 'price']

    def __str__(self):
        return f"{self.name} (${self.price})"

    def benefits_list(self):
        """Return benefits as a list of strings."""
        return [b.strip() for b in self.benefits.split('\n') if b.strip()]


class Sponsor(models.Model):
    TIER_CHOICES = [
        ('gold', 'Gold'),
        ('silver', 'Silver'),
        ('bronze', 'Bronze'),
        ('other', 'Other'),
    ]

    name = models.CharField(max_length=200)
    logo = models.ImageField(upload_to='sponsor_logos/', blank=True, null=True)
    website_url = models.URLField(blank=True, null=True)
    tier = models.CharField(max_length=20, choices=TIER_CHOICES, default='other')
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['tier', 'sort_order', 'name']

    def __str__(self):
        return f"{self.name} ({self.get_tier_display()})"


class RegistrationPlayer(models.Model):
    """An individual player slot within a registration."""
    registration = models.ForeignKey(
        'Registration',
        on_delete=models.CASCADE,
        related_name='players'
    )
    slot = models.PositiveSmallIntegerField(help_text="Player position (1-based)")
    name = models.CharField(max_length=200, blank=True, help_text="Leave blank if unknown")

    class Meta:
        ordering = ['slot']
        unique_together = [['registration', 'slot']]

    def __str__(self):
        return self.name or f"Player {self.slot} (TBD)"


class AddOn(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)

    class Meta:
        ordering = ['sort_order', 'name']

    def __str__(self):
        return f"{self.name} (${self.price})"


class RegistrationAddOn(models.Model):
    registration = models.ForeignKey('Registration', on_delete=models.CASCADE, related_name='addons')
    addon = models.ForeignKey(AddOn, on_delete=models.PROTECT, related_name='registrations')

    class Meta:
        unique_together = [['registration', 'addon']]

    def __str__(self):
        return f"{self.addon.name}"


class Registration(models.Model):
    PAYMENT_METHOD_CHOICES = [
        ('square', 'Credit Card (Square)'),
        ('check', 'Pay by Check'),
    ]
    PAYMENT_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('paid', 'Paid'),
        ('failed', 'Failed'),
    ]

    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company_org = models.CharField(max_length=200, blank=True, verbose_name="Company / Organization")
    sponsorship_package = models.ForeignKey(
        SponsorshipPackage,
        on_delete=models.PROTECT,
        related_name='registrations'
    )
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHOD_CHOICES)
    payment_status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default='pending')
    square_payment_id = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    company_logo = models.ImageField(
        upload_to='registration_logos/',
        blank=True,
        null=True,
        help_text="Optional company logo (displayed on the tournament website)"
    )
    logo_approved = models.BooleanField(
        default=False,
        help_text="Approve this logo to display it on the tournament home page."
    )
    notes = models.TextField(blank=True, help_text="Any additional notes or special requests")

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.first_name} {self.last_name} - {self.sponsorship_package.name}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class RaffleDonation(models.Model):
    """A raffle item donation pledge submitted via the homepage callout form."""
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    company_name = models.CharField(max_length=200, blank=True, verbose_name="Company / Organization")
    donation_description = models.TextField(
        verbose_name="Donation Description",
        help_text="Describe the item(s) you would like to donate for the raffle."
    )
    estimated_value = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="Estimated Value ($)",
        help_text="Approximate retail value of the donated item(s)."
    )
    DELIVERY_CHOICES = [
        ('drop_off', 'I will drop it off at Clay Elementary School'),
        ('pick_up', 'Please have the tournament chair pick it up'),
    ]
    delivery_method = models.CharField(
        max_length=20,
        choices=DELIVERY_CHOICES,
        verbose_name="Delivery Method",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = "Raffle Donation"
        verbose_name_plural = "Raffle Donations"

    def __str__(self):
        return f"{self.first_name} {self.last_name} — {self.donation_description[:60]}"

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"


class TournamentInfo(models.Model):
    """Singleton model for tournament configuration."""
    tournament_name = models.CharField(max_length=300, default="Clay Elementary School Golf Tournament")
    date = models.DateField(null=True, blank=True)
    location = models.CharField(max_length=300, blank=True)
    description = models.TextField(blank=True)
    entry_deadline = models.DateField(null=True, blank=True)
    contact_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField(blank=True)
    contact_phone = models.CharField(max_length=20, blank=True)

    class Meta:
        verbose_name = "Tournament Info"
        verbose_name_plural = "Tournament Info"

    def __str__(self):
        return self.tournament_name

    def save(self, *args, **kwargs):
        # Enforce singleton: only allow one instance
        if not self.pk and TournamentInfo.objects.exists():
            raise ValidationError("Only one TournamentInfo instance is allowed.")
        super().save(*args, **kwargs)

    @classmethod
    def get_instance(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
