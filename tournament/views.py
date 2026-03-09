import json
import uuid
import logging
import requests

from django.conf import settings
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .models import TournamentInfo, Sponsor, SponsorshipPackage, Registration, RegistrationPlayer, AddOn, RegistrationAddOn
from .forms import RegistrationForm

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

    # Registrations with uploaded logos grouped by sponsor tier (exclude failed payments)
    registrant_logos_qs = (
        Registration.objects
        .exclude(payment_status='failed')
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
                    return redirect('tournament:confirmation', pk=registration.pk)
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
                return redirect('tournament:confirmation', pk=registration.pk)
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


def confirmation(request, pk):
    """Confirmation page after registration."""
    registration = get_object_or_404(Registration, pk=pk)
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
