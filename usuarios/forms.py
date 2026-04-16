from django import forms
from django.contrib.auth.forms import AuthenticationForm


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        label='Usuário',
        widget=forms.TextInput(
            attrs={
                'class': 'form-control form-control-lg',
                'autocomplete': 'username',
                'autofocus': True,
            },
        ),
    )
    password = forms.CharField(
        label='Senha',
        strip=False,
        widget=forms.PasswordInput(
            attrs={
                'class': 'form-control form-control-lg',
                'autocomplete': 'current-password',
            },
        ),
    )
