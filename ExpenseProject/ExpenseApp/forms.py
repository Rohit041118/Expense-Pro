from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from .models import Expense, Category, UserProfile, Company


# All ISO 4217 world currencies
WORLD_CURRENCIES = [
    ('', '— Select Currency —'),
    ('INR', 'INR — Indian Rupee'),
    ('USD', 'USD — US Dollar'),
    ('EUR', 'EUR — Euro'),
    ('GBP', 'GBP — British Pound'),
    ('AED', 'AED — UAE Dirham'),
    ('AUD', 'AUD — Australian Dollar'),
    ('CAD', 'CAD — Canadian Dollar'),
    ('CHF', 'CHF — Swiss Franc'),
    ('CNY', 'CNY — Chinese Yuan'),
    ('HKD', 'HKD — Hong Kong Dollar'),
    ('JPY', 'JPY — Japanese Yen'),
    ('KRW', 'KRW — South Korean Won'),
    ('MYR', 'MYR — Malaysian Ringgit'),
    ('NZD', 'NZD — New Zealand Dollar'),
    ('SGD', 'SGD — Singapore Dollar'),
    ('ZAR', 'ZAR — South African Rand'),
    ('BRL', 'BRL — Brazilian Real'),
    ('MXN', 'MXN — Mexican Peso'),
    ('SAR', 'SAR — Saudi Riyal'),
    ('QAR', 'QAR — Qatari Riyal'),
    ('KWD', 'KWD — Kuwaiti Dinar'),
    ('BHD', 'BHD — Bahraini Dinar'),
    ('OMR', 'OMR — Omani Rial'),
    ('IDR', 'IDR — Indonesian Rupiah'),
    ('THB', 'THB — Thai Baht'),
    ('VND', 'VND — Vietnamese Dong'),
    ('PKR', 'PKR — Pakistani Rupee'),
    ('BDT', 'BDT — Bangladeshi Taka'),
    ('LKR', 'LKR — Sri Lankan Rupee'),
    ('NPR', 'NPR — Nepalese Rupee'),
    ('SEK', 'SEK — Swedish Krona'),
    ('NOK', 'NOK — Norwegian Krone'),
    ('DKK', 'DKK — Danish Krone'),
    ('PLN', 'PLN — Polish Zloty'),
    ('TRY', 'TRY — Turkish Lira'),
    ('RUB', 'RUB — Russian Ruble'),
    ('EGP', 'EGP — Egyptian Pound'),
    ('NGN', 'NGN — Nigerian Naira'),
    ('KES', 'KES — Kenyan Shilling'),
    ('GHS', 'GHS — Ghanaian Cedi'),
    ('MAD', 'MAD — Moroccan Dirham'),
    ('CLP', 'CLP — Chilean Peso'),
    ('COP', 'COP — Colombian Peso'),
    ('ARS', 'ARS — Argentine Peso'),
    ('PEN', 'PEN — Peruvian Sol'),
    ('TWD', 'TWD — Taiwan Dollar'),
    ('PHP', 'PHP — Philippine Peso'),
    ('HUF', 'HUF — Hungarian Forint'),
    ('CZK', 'CZK — Czech Koruna'),
    ('ILS', 'ILS — Israeli Shekel'),
    ('RON', 'RON — Romanian Leu'),
    ('BGN', 'BGN — Bulgarian Lev'),
    ('HRK', 'HRK — Croatian Kuna'),
    ('ISK', 'ISK — Icelandic Krona'),
    ('UAH', 'UAH — Ukrainian Hryvnia'),
]


class AdminSignupForm(UserCreationForm):
    """Styled signup form for Admin registration."""
    first_name = forms.CharField(
        max_length=40, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Jane', 'autocomplete': 'off'})
    )
    last_name = forms.CharField(
        max_length=40, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Smith', 'autocomplete': 'off'})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-input', 'placeholder': 'you@company.com', 'autocomplete': 'off'})
    )

    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'username', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Choose a username', 'autocomplete': 'off'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget = forms.PasswordInput(attrs={
            'class': 'form-input', 'placeholder': 'Create a strong password',
            'autocomplete': 'new-password', 'id': 'id_password1'
        })
        self.fields['password2'].widget = forms.PasswordInput(attrs={
            'class': 'form-input', 'placeholder': 'Confirm your password',
            'autocomplete': 'new-password', 'id': 'id_password2'
        })
        self.fields['username'].help_text = None
        self.fields['password1'].help_text = None
        self.fields['password2'].help_text = None


class ExpenseForm(forms.ModelForm):
    """Form for creating / editing an expense."""

    # Optional custom category — shown when user picks "Other"
    custom_category = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-input',
            'placeholder': 'Type your custom category...',
            'id': 'id_custom_category',
            'style': 'display:none;',
        }),
        label='Custom Category',
    )

    class Meta:
        model   = Expense
        fields  = ['title', 'description', 'amount', 'currency', 'date', 'category', 'receipt']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-input',
                'placeholder': 'e.g. Flight to Delhi — Q1 Review',
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-textarea',
                'placeholder': 'Brief description of the expense...',
                'rows': 3,
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-input',
                'placeholder': '0.00',
                'step': '0.01',
                'min': '0',
            }),
            'currency': forms.Select(
                choices=WORLD_CURRENCIES,
                attrs={'class': 'form-select'},
            ),
            'date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'category': forms.Select(attrs={'class': 'form-select', 'id': 'id_category'}),
            'receipt': forms.FileInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.all().order_by('name')
        self.fields['category'].empty_label = '— Select Category —'
        self.fields['category'].required = False

    def clean(self):
        cleaned = super().clean()
        category   = cleaned.get('category')
        custom_cat = cleaned.get('custom_category', '').strip()

        # If no category selected and user typed a custom one, create/get it
        if not category and custom_cat:
            cat_obj, _ = Category.objects.get_or_create(
                name=custom_cat,
                defaults={'icon': 'fa-tag'},
            )
            cleaned['category'] = cat_obj
        return cleaned

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount is not None and amount <= 0:
            raise forms.ValidationError("Amount must be greater than zero.")
        return amount


class ReviewForm(forms.Form):
    """Form for manager to approve/reject an expense."""
    manager_note = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Optional note to the employee...',
        }),
        label='Note to Employee',
    )
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-textarea',
            'rows': 3,
            'placeholder': 'Reason for rejection (required when rejecting)...',
        }),
        label='Rejection Reason',
    )

    def clean(self):
        cleaned = super().clean()
        action = self.data.get('action')
        if action == 'reject' and not cleaned.get('rejection_reason'):
            raise forms.ValidationError("Rejection reason is required when rejecting.")
        return cleaned


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile."""
    first_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input'}),
    )
    last_name = forms.CharField(
        max_length=150, required=False,
        widget=forms.TextInput(attrs={'class': 'form-input'}),
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={'class': 'form-input'}),
    )

    class Meta:
        model   = UserProfile
        fields  = ['department', 'phone']
        widgets = {
            'department': forms.TextInput(attrs={'class': 'form-input'}),
            'phone':      forms.TextInput(attrs={'class': 'form-input'}),
        }

class CompanySetupForm(forms.ModelForm):
    """Admin onboarding form for setting up a company and default currency."""
    class Meta:
        model = Company
        fields = ['name', 'country', 'base_currency_code', 'base_currency_symbol']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'e.g. Acme Corp'}),
            'country': forms.HiddenInput(attrs={'id': 'id_country'}),
            'base_currency_code': forms.HiddenInput(attrs={'id': 'id_currency_code'}),
            'base_currency_symbol': forms.HiddenInput(attrs={'id': 'id_currency_symbol'})
        }

class AdminUserCreateForm(forms.ModelForm):
    """Form for Admins to create new Employees/Managers."""
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-input', 'required': 'true'}),
            'first_name': forms.TextInput(attrs={'class': 'form-input'}),
            'last_name': forms.TextInput(attrs={'class': 'form-input'}),
            'email': forms.EmailInput(attrs={'class': 'form-input'}),
        }

class AdminUserProfileForm(forms.ModelForm):
    """Form for assigning roles and managers."""
    class Meta:
        model = UserProfile
        fields = ['role', 'manager', 'department', 'phone']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'manager': forms.Select(attrs={'class': 'form-select'}),
            'department': forms.TextInput(attrs={'class': 'form-input'}),
            'phone': forms.TextInput(attrs={'class': 'form-input'}),
        }

    def __init__(self, *args, **kwargs):
        company = kwargs.pop('company', None)
        super().__init__(*args, **kwargs)
        if company:
            self.fields['manager'].queryset = UserProfile.objects.filter(
                company=company, role__in=['manager', 'admin']
            )
