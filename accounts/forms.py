from django import forms
from django.contrib.admin.forms import AdminAuthenticationForm


class EmailOrPhoneAdminAuthenticationForm(AdminAuthenticationForm):
    username = forms.CharField(
        label="Email ou telephone",
        widget=forms.TextInput(attrs={"autofocus": True}),
    )
