import io
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.utils.html import format_html

from .models import SponsorshipPackage, Sponsor, Registration, RegistrationPlayer, TournamentInfo, AddOn, RegistrationAddOn


@admin.register(TournamentInfo)
class TournamentInfoAdmin(admin.ModelAdmin):
    fieldsets = (
        ('Tournament Details', {
            'fields': ('tournament_name', 'date', 'location', 'description', 'entry_deadline'),
        }),
        ('Contact Information', {
            'fields': ('contact_name', 'contact_email', 'contact_phone'),
        }),
    )

    def has_add_permission(self, request):
        # Only allow adding if no instance exists
        if TournamentInfo.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SponsorshipPackage)
class SponsorshipPackageAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'max_players', 'sponsor_tier', 'logo_upload', 'is_active', 'sort_order']
    list_editable = ['sponsor_tier', 'logo_upload', 'is_active', 'sort_order']
    list_filter = ['is_active', 'logo_upload', 'sponsor_tier']
    ordering = ['sort_order', 'price']


@admin.register(Sponsor)
class SponsorAdmin(admin.ModelAdmin):
    list_display = ['name', 'tier', 'is_active', 'sort_order', 'logo_preview']
    list_editable = ['is_active', 'tier', 'sort_order']
    list_filter = ['tier', 'is_active']
    ordering = ['tier', 'sort_order', 'name']

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="height:40px; width:auto; object-fit:contain;" />',
                obj.logo.url
            )
        return "No logo"
    logo_preview.short_description = "Logo Preview"


@admin.register(AddOn)
class AddOnAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_active', 'sort_order']
    list_editable = ['price', 'is_active', 'sort_order']
    ordering = ['sort_order', 'name']


class RegistrationAddOnInline(admin.TabularInline):
    model = RegistrationAddOn
    extra = 0
    readonly_fields = ['addon', 'addon_price']
    can_delete = False

    def addon_price(self, obj):
        return f"${obj.addon.price}"
    addon_price.short_description = "Price"


class RegistrationPlayerInline(admin.TabularInline):
    model = RegistrationPlayer
    extra = 0
    fields = ['slot', 'name']
    readonly_fields = ['slot']
    can_delete = False
    verbose_name = "Player"
    verbose_name_plural = "Players in Group"


@admin.register(Registration)
class RegistrationAdmin(admin.ModelAdmin):
    change_list_template = 'admin/tournament/registration/change_list.html'

    list_display = [
        'full_name', 'email', 'sponsorship_package', 'payment_method',
        'payment_status', 'order_total', 'has_logo', 'created_at'
    ]
    list_filter = ['payment_method', 'payment_status', 'sponsorship_package', 'created_at']
    search_fields = ['first_name', 'last_name', 'email', 'company_org', 'square_payment_id']
    readonly_fields = ['created_at', 'square_payment_id', 'logo_preview']
    date_hierarchy = 'created_at'

    inlines = [RegistrationPlayerInline, RegistrationAddOnInline]
    fieldsets = (
        ('Registrant Information', {
            'fields': ('first_name', 'last_name', 'email', 'phone', 'company_org'),
        }),
        ('Sponsorship', {
            'fields': ('sponsorship_package',),
        }),
        ('Payment', {
            'fields': ('payment_method', 'payment_status', 'square_payment_id'),
        }),
        ('Logo', {
            'fields': ('company_logo', 'logo_preview'),
        }),
        ('Additional', {
            'fields': ('notes', 'created_at'),
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path('export-excel/', self.admin_site.admin_view(self.export_excel), name='registration_export_excel'),
        ]
        return custom + urls

    def export_excel(self, request):
        registrations = (
            Registration.objects
            .select_related('sponsorship_package')
            .prefetch_related('players', 'addons__addon')
            .order_by('sponsorship_package__sort_order', 'last_name', 'first_name')
        )

        # Determine max player count across all registrations
        max_players = max(
            (reg.sponsorship_package.max_players for reg in registrations),
            default=0
        )

        wb = Workbook()
        ws = wb.active
        ws.title = "Registrations"

        # Styles
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="1D4582")
        center = Alignment(horizontal="center", vertical="center", wrap_text=True)

        # Build header row
        headers = [
            'First Name', 'Last Name', 'Email', 'Phone',
            'Company / Organization', 'Sponsorship Package',
            'Add-Ons', 'Add-On Total', 'Package Price', 'Order Total',
            'Payment Method', 'Paid?',
        ]
        for i in range(1, max_players + 1):
            headers.append(f'Player {i}')

        for col, header in enumerate(headers, start=1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = center

        # Data rows
        for row_idx, reg in enumerate(registrations, start=2):
            addon_qs = reg.addons.select_related('addon').all()
            addon_names = ', '.join(ra.addon.name for ra in addon_qs)
            addon_total = sum(ra.addon.price for ra in addon_qs)
            order_total = reg.sponsorship_package.price + addon_total

            players_by_slot = {p.slot: p.name for p in reg.players.all()}

            row = [
                reg.first_name,
                reg.last_name,
                reg.email,
                reg.phone,
                reg.company_org,
                reg.sponsorship_package.name,
                addon_names,
                float(addon_total),
                float(reg.sponsorship_package.price),
                float(order_total),
                reg.get_payment_method_display(),
                'Yes' if reg.payment_status == 'paid' else 'No',
            ]
            for slot in range(1, max_players + 1):
                row.append(players_by_slot.get(slot, ''))

            for col, value in enumerate(row, start=1):
                cell = ws.cell(row=row_idx, column=col, value=value)
                cell.alignment = Alignment(vertical="center", wrap_text=True)

            # Alternate row shading
            if row_idx % 2 == 0:
                fill = PatternFill("solid", fgColor="EEF2F9")
                for col in range(1, len(headers) + 1):
                    ws.cell(row=row_idx, column=col).fill = fill

        # Format currency columns
        money_cols = [headers.index('Add-On Total') + 1, headers.index('Package Price') + 1, headers.index('Order Total') + 1]
        for col in money_cols:
            for row_idx in range(2, ws.max_row + 1):
                ws.cell(row=row_idx, column=col).number_format = '"$"#,##0.00'

        # Auto-fit column widths
        for col in ws.columns:
            max_len = max((len(str(cell.value or '')) for cell in col), default=10)
            ws.column_dimensions[get_column_letter(col[0].column)].width = min(max_len + 4, 40)

        ws.freeze_panes = 'A2'

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)

        response = HttpResponse(
            buf,
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )
        response['Content-Disposition'] = 'attachment; filename="registrations.xlsx"'
        return response

    def full_name(self, obj):
        return obj.full_name
    full_name.short_description = "Name"
    full_name.admin_order_field = 'last_name'

    def order_total(self, obj):
        addon_total = sum(ra.addon.price for ra in obj.addons.select_related('addon').all())
        total = obj.sponsorship_package.price + addon_total
        return f"${total:,.2f}"
    order_total.short_description = "Order Total"

    def has_logo(self, obj):
        return bool(obj.company_logo)
    has_logo.short_description = "Logo"
    has_logo.boolean = True

    def logo_preview(self, obj):
        if obj.company_logo:
            return format_html(
                '<img src="{}" style="max-height:80px; max-width:200px; object-fit:contain;" />',
                obj.company_logo.url
            )
        return "No logo uploaded"
    logo_preview.short_description = "Logo Preview"
