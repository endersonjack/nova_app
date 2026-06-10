from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from membros.forms import MembroCpfTelefoneCleanMixin, _configure_html5_date_inputs
from membros.models import Membro
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


class MeuPerfilMembroForm(MembroCpfTelefoneCleanMixin, forms.ModelForm):
    cpf = forms.CharField(
        label=_('CPF'),
        max_length=14,
        required=False,
    )
    telefone = forms.CharField(
        label=_('Telefone'),
        max_length=16,
        required=False,
        help_text=_('Ex.: (84) 99999-9999'),
    )

    class Meta:
        model = Membro
        fields = (
            'nome_completo',
            'nome_conhecido',
            'cpf',
            'data_nascimento',
            'telefone',
            'email',
            'foto',
            'endereco',
            'maps_embed',
            'estado_civil',
            'data_casamento',
            'batizado',
            'data_batismo',
            'locomocao',
            'tamanho_camisa',
            'observacoes',
        )
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'data_casamento': forms.DateInput(attrs={'type': 'date'}),
            'data_batismo': forms.DateInput(attrs={'type': 'date'}),
            'endereco': forms.Textarea(attrs={'rows': 1}),
            'maps_embed': forms.Textarea(attrs={'rows': 1}),
            'observacoes': forms.Textarea(attrs={'rows': 1}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_html5_date_inputs(self, 'data_nascimento', 'data_casamento', 'data_batismo')
        self.fields['nome_completo'].label = _('Nome')
        self.fields['endereco'].label = _('Endereço')
        self.fields['maps_embed'].label = _('Mapa')
        self.fields['estado_civil'].label = _('Estado civil')
        self.fields['data_casamento'].label = _('Data de casamento')
        self.fields['locomocao'].label = _('Locomoção')
        self.fields['tamanho_camisa'].label = _('Tamanho da camisa')
        self.fields['observacoes'].label = _('Observações')
        self.fields['nome_completo'].required = True
        self.fields['cpf'].required = False
        for name, field in self.fields.items():
            widget = field.widget
            if name == 'batizado':
                widget.attrs.setdefault('class', 'form-check-input')
            elif isinstance(widget, forms.Select):
                widget.attrs.setdefault('class', 'form-select rounded-3')
            else:
                widget.attrs.setdefault('class', 'form-control rounded-3')
            if name in ('endereco', 'maps_embed', 'observacoes'):
                current_class = widget.attrs.get('class', 'form-control rounded-3')
                if 'app-modal-form__input-one-line' not in current_class:
                    widget.attrs['class'] = f'{current_class} app-modal-form__input-one-line'
        if self.instance.pk:
            if self.instance.cpf:
                self.initial['cpf'] = self.instance.cpf_formatado
            if self.instance.telefone:
                self.initial['telefone'] = self.instance.telefone_formatado


class MeuPerfilAcessoForm(forms.ModelForm):
    class Meta:
        model = get_user_model()
        fields = ('username',)
        labels = {
            'username': _('Login'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault('class', 'form-control rounded-3')
        self.fields['username'].widget.attrs.setdefault('autocomplete', 'username')

    def clean_username(self):
        username = (self.cleaned_data.get('username') or '').strip()
        if not username:
            raise forms.ValidationError(_('Informe um login.'))
        qs = get_user_model().objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_('Este login já está em uso.'))
        return username
