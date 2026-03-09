from django import forms
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Row, Column, Field, Submit, Div, HTML
from .models import Registration, SponsorshipPackage


class RegistrationForm(forms.ModelForm):
    # Hidden field for Square payment nonce/source ID
    square_source_id = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'id': 'square-source-id'})
    )

    class Meta:
        model = Registration
        fields = [
            'first_name', 'last_name', 'email', 'phone',
            'company_org', 'sponsorship_package', 'payment_method', 'company_logo', 'notes',
        ]
        widgets = {
            'notes': forms.Textarea(attrs={'rows': 3}),
            'phone': forms.TextInput(attrs={'placeholder': '(559) 555-1234'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show active packages
        self.fields['sponsorship_package'].queryset = SponsorshipPackage.objects.filter(is_active=True)
        self.fields['sponsorship_package'].empty_label = "-- Select a Sponsorship Package --"
        self.fields['first_name'].widget.attrs.update({'autofocus': 'autofocus'})
        self.fields['company_logo'].required = False
        self.fields['company_logo'].label = "Company / Organization Logo"
        self.fields['company_logo'].help_text = (
            "Upload your logo to have it displayed on our tournament website. "
            "PNG or JPG recommended. Max 5 MB."
        )

        self.helper = FormHelper()
        self.helper.form_id = 'registration-form'
        self.helper.form_method = 'post'
        self.helper.attrs = {'enctype': 'multipart/form-data'}
        self.helper.layout = Layout(
            HTML('<h4 class="section-title mt-2 mb-3">Contact Information</h4>'),
            Row(
                Column('first_name', css_class='col-md-6'),
                Column('last_name', css_class='col-md-6'),
            ),
            Row(
                Column('email', css_class='col-md-6'),
                Column('phone', css_class='col-md-6'),
            ),
            Field('company_org'),
            HTML('<h4 class="section-title mt-4 mb-3">Sponsorship Package</h4>'),
            Field('sponsorship_package', css_class='package-select'),
            HTML('<div id="package-details" class="package-details-box d-none"></div>'),
            HTML('''
    <div id="addons-section">
        <h4 class="section-title mt-4 mb-3">Add-On Packages</h4>
        <p class="text-muted small mb-3">
            Enhance your sponsorship with optional add-on packages below.
        </p>
        <div id="addon-fields"></div>
    </div>
'''),
            HTML('<h4 class="section-title mt-4 mb-3">Payment Method</h4>'),
            Field('payment_method'),
            HTML('''
                <div id="square-card-container" class="mt-3 d-none">
                    <label class="form-label fw-semibold">Credit Card Details</label>
                    <div id="card-container" class="square-card-element"></div>
                    <div id="payment-status-container" class="mt-2"></div>
                </div>
            '''),
            HTML('''
                <div id="player-names-section" class="d-none">
                    <h4 class="section-title mt-4 mb-3">Player Names</h4>
                    <p class="text-muted small mb-3">
                        Enter the name of each player in your group. If you do not yet know the names of all players,
                        you leave the field blank and the Tournament Chair will follow up with you.
                    </p>
                    <div id="player-names-fields"></div>
                </div>
            '''),
            Div(
                HTML('<h4 class="section-title mt-4 mb-3">Company Logo</h4>'),
                HTML('''<p class="text-muted small mb-3">
                    Your sponsorship package includes logo display on our tournament website.
                    Upload your logo below &mdash; it will appear on our home page once your registration is confirmed.
                </p>'''),
                Field('company_logo'),
                css_id='logo-upload-section',
                css_class='d-none',
            ),
            HTML('<h4 class="section-title mt-4 mb-3">Additional Information</h4>'),
            Field('notes'),
            Field('square_source_id'),
            HTML('''
                <div class="mt-4">
                    <button type="submit" id="submit-btn" class="btn btn-gold btn-lg px-5">
                        <span id="submit-text">Complete Registration</span>
                        <span id="submit-spinner" class="spinner-border spinner-border-sm ms-2 d-none" role="status"></span>
                    </button>
                </div>
            '''),
        )

    def clean(self):
        cleaned_data = super().clean()
        payment_method = cleaned_data.get('payment_method')
        square_source_id = cleaned_data.get('square_source_id')

        if payment_method == 'square' and not square_source_id:
            raise forms.ValidationError(
                "Please complete the credit card information before submitting."
            )
        return cleaned_data
