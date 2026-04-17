from django import forms
from .models import Expense, UserProfile


class ExpenseForm(forms.ModelForm):
    """Form for creating / editing an expense."""

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
            'currency': forms.Select(attrs={'class': 'form-select'}),
            'date': forms.DateInput(attrs={
                'class': 'form-input',
                'type': 'date',
            }),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'receipt': forms.FileInput(attrs={'class': 'form-input'}),
        }

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
