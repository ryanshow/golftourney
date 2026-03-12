import json
import uuid
import logging
import requests

from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.shortcuts import render, redirect, get_object_or_404

from .models import TournamentInfo, Sponsor, SponsorshipPackage, Registration, RegistrationPlayer, AddOn, RegistrationAddOn, RaffleDonation
from .forms import RegistrationForm, RaffleDonationForm

logger = logging.getLogger(__name__)


def get_square_api_url():
    """Return the correct Square API base URL based on environment."""
    if settings.SQUARE_ENVIRONMENT == 'production':
        return 'https://connect.squareup.com'
    return 'https://connect.squareupstaging.com'


def charge_square_payment(source_id, amount_cents, note="Golf Tournament Registration"):
    """
    Charge a card via the Square Payments API.
    Returns (success: bool, payment_id_or_error: str)
    """
    api_url = get_square_api_url()
    endpoint = f"{api_url}/v2/payments"

    headers = {
        'Authorization': f"Bearer {settings.SQUARE_ACCESS_TOKEN}",
        'Content-Type': 'application/json',
        'Square-Version': '2024-01-18',
    }

    payload = {
        'idempotency_key': str(uuid.uuid4()),
        'source_id': source_id,
        'amount_money': {
            'amount': amount_cents,
            'currency': 'USD',
        },
        'location_id': settings.SQUARE_LOCATION_ID,
        'note': note,
    }

    try:
        response = requests.post(endpoint, json=payload, headers=headers, timeout=30)
        data = response.json()

        if response.status_code == 200 and data.get('payment', {}).get('status') == 'COMPLETED':
            payment_id = data['payment']['id']
            return True, payment_id
        else:
            errors = data.get('errors', [])
            error_msg = errors[0].get('detail', 'Payment failed') if errors else 'Payment failed'
            logger.error("Square payment error: %s | Response: %s", error_msg, data)
            return False, error_msg

    except requests.RequestException as exc:
        logger.exception("Square API request failed: %s", exc)
        return False, "Unable to connect to payment processor. Please try again."


def _save_addons(registration, post_data):
    """Save selected add-ons from POST data for the given registration."""
    addon_ids = post_data.getlist('addon_ids')
    if addon_ids:
        addons = AddOn.objects.filter(id__in=addon_ids, is_active=True)
        for addon in addons:
            RegistrationAddOn.objects.create(registration=registration, addon=addon)


def _save_players(registration, post_data):
    """Save submitted player names from POST data for the given registration."""
    max_players = registration.sponsorship_package.max_players
    for slot in range(1, max_players + 1):
        name = post_data.get(f'player_name_{slot}', '').strip()
        RegistrationPlayer.objects.create(registration=registration, slot=slot, name=name)


def index(request):
    """Landing page: tournament info + sponsor grid."""
    tournament = TournamentInfo.get_instance()
    sponsors = Sponsor.objects.filter(is_active=True)

    # Group sponsors by tier for display
    gold_sponsors = sponsors.filter(tier='gold')
    silver_sponsors = sponsors.filter(tier='silver')
    bronze_sponsors = sponsors.filter(tier='bronze')
    other_sponsors = sponsors.filter(tier='other')

    packages = SponsorshipPackage.objects.filter(is_active=True)

    # Registrations with approved logos grouped by sponsor tier
    registrant_logos_qs = (
        Registration.objects
        .filter(logo_approved=True)
        .filter(company_logo__isnull=False)
        .exclude(company_logo='')
        .select_related('sponsorship_package')
        .order_by('last_name')
    )
    reg_logos_by_tier = {}
    for reg in registrant_logos_qs:
        tier = reg.sponsorship_package.sponsor_tier
        if tier:
            reg_logos_by_tier.setdefault(tier, []).append(reg)

    context = {
        'tournament': tournament,
        'gold_sponsors': gold_sponsors,
        'silver_sponsors': silver_sponsors,
        'bronze_sponsors': bronze_sponsors,
        'other_sponsors': other_sponsors,
        'all_sponsors': sponsors,
        'reg_logos_gold': reg_logos_by_tier.get('gold', []),
        'reg_logos_silver': reg_logos_by_tier.get('silver', []),
        'reg_logos_bronze': reg_logos_by_tier.get('bronze', []),
        'reg_logos_other': reg_logos_by_tier.get('other', []),
        'packages': packages,
        'any_registrant_logos': bool(reg_logos_by_tier),
    }
    return render(request, 'tournament/index.html', context)


def register(request):
    """Registration form with Square payment."""
    tournament = TournamentInfo.get_instance()
    packages = SponsorshipPackage.objects.filter(is_active=True)
    addons = AddOn.objects.filter(is_active=True)

    # Build package data for JS (prices, player counts, descriptions)
    package_data = {
        str(pkg.pk): {
            'name': pkg.name,
            'price': str(pkg.price),
            'price_cents': int(pkg.price * 100),
            'description': pkg.description,
            'max_players': pkg.max_players,
            'benefits': pkg.benefits_list(),
            'logo_upload': pkg.logo_upload,
        }
        for pkg in packages
    }

    addon_data = {
        str(a.pk): {
            'name': a.name,
            'description': a.description,
            'price': str(a.price),
            'price_cents': int(a.price * 100),
        }
        for a in addons
    }

    package_data_json = json.dumps(package_data)
    addon_data_json = json.dumps(addon_data)

    square_js_url = (
        'https://web.squarecdn.com/v1/square.js'
        if settings.SQUARE_ENVIRONMENT == 'production'
        else 'https://sandbox.web.squarecdn.com/v1/square.js'
    )

    if request.method == 'POST':
        form = RegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            registration = form.save(commit=False)
            payment_method = form.cleaned_data['payment_method']

            if payment_method == 'square':
                source_id = form.cleaned_data['square_source_id']
                addon_ids = request.POST.getlist('addon_ids')
                selected_addons = list(AddOn.objects.filter(id__in=addon_ids, is_active=True))
                addon_total = sum(a.price for a in selected_addons)
                amount_cents = int((registration.sponsorship_package.price + addon_total) * 100)
                note = (
                    f"Golf Tournament - {registration.sponsorship_package.name} - "
                    f"{registration.first_name} {registration.last_name}"
                )

                success, result = charge_square_payment(source_id, amount_cents, note)

                if success:
                    registration.payment_status = 'paid'
                    registration.square_payment_id = result
                    registration.save()
                    _save_players(registration, request.POST)
                    _save_addons(registration, request.POST)
                    _send_registration_notification_email(registration, tournament)
                    return redirect('tournament:confirmation', token=registration.token)
                else:
                    messages.error(
                        request,
                        f"Payment failed: {result}. Please check your card details and try again."
                    )
                    # Re-render form with error; the nonce is single-use so user must re-enter card
                    context = {
                        'form': form,
                        'tournament': tournament,
                        'packages': packages,
                        'package_data': package_data_json,
                        'addon_data': addon_data_json,
                        'addons': addons,
                        'square_js_url': square_js_url,
                        'square_app_id': getattr(settings, 'SQUARE_APPLICATION_ID', ''),
                        'square_location_id': settings.SQUARE_LOCATION_ID,
                    }
                    return render(request, 'tournament/register.html', context)

            else:
                # Pay by check
                registration.payment_status = 'pending'
                registration.save()
                _save_players(registration, request.POST)
                _save_addons(registration, request.POST)
                _send_registration_notification_email(registration, tournament)
                return redirect('tournament:confirmation', token=registration.token)
        # Form invalid — fall through to re-render below
    else:
        form = RegistrationForm()

    square_app_id = getattr(settings, 'SQUARE_APPLICATION_ID', '')

    context = {
        'form': form,
        'tournament': tournament,
        'packages': packages,
        'package_data': package_data_json,
        'addon_data': addon_data_json,
        'addons': addons,
        'square_js_url': square_js_url,
        'square_app_id': square_app_id,
        'square_location_id': settings.SQUARE_LOCATION_ID,
    }
    return render(request, 'tournament/register.html', context)


def confirmation(request, token):
    """Confirmation page after registration."""
    registration = get_object_or_404(Registration, token=token)
    tournament = TournamentInfo.get_instance()
    reg_addons = registration.addons.select_related('addon').all()
    addon_total = sum(ra.addon.price for ra in reg_addons)
    total_amount = registration.sponsorship_package.price + addon_total
    context = {
        'registration': registration,
        'tournament': tournament,
        'total_amount': total_amount,
        'has_addons': reg_addons.exists(),
    }
    return render(request, 'tournament/confirmation.html', context)


def raffle_donate(request):
    """Raffle item donation form."""
    tournament = TournamentInfo.get_instance()

    if request.method == 'POST':
        form = RaffleDonationForm(request.POST)
        if form.is_valid():
            donation = form.save()
            _send_raffle_donation_email(donation, tournament)
            return redirect('tournament:raffle_donate_thanks')
    else:
        form = RaffleDonationForm()

    return render(request, 'tournament/raffle_donate.html', {'form': form, 'tournament': tournament})


def raffle_donate_thanks(request):
    """Thank-you page after a raffle donation is submitted."""
    tournament = TournamentInfo.get_instance()
    return render(request, 'tournament/raffle_donate_thanks.html', {'tournament': tournament})


def _send_registration_notification_email(registration, tournament):
    """Notify the admin when a new tournament registration is submitted."""
    admin_email = getattr(settings, 'ADMIN_EMAIL', None) or tournament.contact_email
    if not admin_email:
        logger.warning("No admin email configured — registration notification not sent.")
        return

    addons = list(registration.addons.select_related('addon').all())
    addon_total = sum(ra.addon.price for ra in addons)
    order_total = registration.sponsorship_package.price + addon_total

    subject = (
        f"New Registration: {registration.full_name} — {registration.sponsorship_package.name}"
    )

    lines = [
        f"A new registration has been received for the {tournament.tournament_name}.",
        "",
        f"Name:     {registration.full_name}",
        f"Email:    {registration.email}",
    ]
    if registration.phone:
        lines.append(f"Phone:    {registration.phone}")
    if registration.company_org:
        lines.append(f"Company:  {registration.company_org}")
    lines += [
        "",
        f"Package:  {registration.sponsorship_package.name} (${registration.sponsorship_package.price:,.2f})",
    ]
    if addons:
        addon_names = ", ".join(ra.addon.name for ra in addons)
        lines.append(f"Add-Ons:  {addon_names} (${addon_total:,.2f})")
    lines.append(f"Total:    ${order_total:,.2f}")
    lines += [
        "",
        f"Payment:  {registration.get_payment_method_display()}",
        f"Status:   {registration.get_payment_status_display()}",
    ]

    players = list(registration.players.all())
    if players:
        lines += ["", "Players:"]
        for p in players:
            lines.append(f"  {p.slot}. {p.name or '(TBD)'}")

    if registration.company_logo:
        lines += [
            "",
            "Logo uploaded — review and approve in the admin before it appears on the site.",
        ]
    if registration.notes:
        lines += ["", f"Notes: {registration.notes}"]

    try:
        send_mail(
            subject=subject,
            message="\n".join(lines),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', admin_email),
            recipient_list=[admin_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send registration notification email.")


def _send_raffle_donation_email(donation, tournament):
    """Send an admin notification email when a raffle donation is submitted."""
    admin_email = getattr(settings, 'ADMIN_EMAIL', None) or tournament.contact_email
    if not admin_email:
        logger.warning("No admin email configured — raffle donation notification not sent.")
        return

    subject = f"New Raffle Donation: {donation.full_name}"
    body_lines = [
        f"A new raffle item donation has been submitted for the {tournament.tournament_name}.",
        "",
        f"Name:    {donation.full_name}",
        f"Email:   {donation.email}",
    ]
    if donation.phone:
        body_lines.append(f"Phone:   {donation.phone}")
    if donation.company_name:
        body_lines.append(f"Company: {donation.company_name}")
    body_lines += [
        "",
        "Donation Description:",
        donation.donation_description,
        "",
    ]
    if donation.estimated_value:
        body_lines.append(f"Estimated Value: ${donation.estimated_value:,.2f}")
    body_lines.append(f"Delivery Method: {donation.get_delivery_method_display()}")

    try:
        send_mail(
            subject=subject,
            message="\n".join(body_lines),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', admin_email),
            recipient_list=[admin_email],
            fail_silently=False,
        )
    except Exception:
        logger.exception("Failed to send raffle donation notification email.")
