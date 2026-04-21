from django import forms
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import ModuloSistema, UserProfile


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


class UserProfileAdminForm(forms.ModelForm):
    """Admin: papel + módulos (JSON como checkboxes)."""

    modulos = forms.MultipleChoiceField(
        label=_('Módulos permitidos'),
        choices=ModuloSistema.choices,
        required=False,
        widget=forms.CheckboxSelectMultiple,
        help_text=_('Para Membro comum e Membro editor. Ignorado para Membro admin (acesso a todos).'),
    )

    class Meta:
        model = UserProfile
        fields = ('membro', 'papel', 'modulos')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if getattr(self.instance, 'pk', None):
            self.initial.setdefault('modulos', self.instance.modulos_normalizados())

    def clean_modulos(self):
        data = self.cleaned_data.get('modulos') or []
        allowed = {c for c, _ in ModuloSistema.choices}
        return [x for x in data if x in allowed]
