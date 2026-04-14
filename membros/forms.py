import re

from django import forms
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _

from .models import ESTADOS_COM_CONJUGE, Membro
from .validators import only_digits_cpf

# <input type="date"> só aceita YYYY-MM-DD; com USE_I18N/pt-br o DateInput padrão usa dd/mm/aaaa.
_HTML5_DATE = '%Y-%m-%d'


def _configure_html5_date_inputs(form: forms.BaseForm, *field_names: str) -> None:
    for name in field_names:
        f = form.fields.get(name)
        if f is None:
            continue
        w = f.widget
        if not isinstance(w, forms.DateInput):
            continue
        w.format = _HTML5_DATE
        f.input_formats = [_HTML5_DATE]


class ClearableFileInputNomeTruncado(forms.ClearableFileInput):
    """Mesmo comportamento do widget padrão, com layout que trunca o nome do arquivo."""

    template_name = 'membros/widgets/clearable_file_input.html'


def _widget_classes_membro_public(form, exclude=('casado_com', 'filhos')):
    for name, field in form.fields.items():
        if name in exclude:
            continue
        w = field.widget
        if name == 'batizado':
            w.attrs.setdefault('class', 'form-check-input')
        elif name in ('sexo', 'locomocao', 'estado_civil'):
            w.attrs.setdefault('class', 'form-select rounded-3')
        elif name in ('endereco', 'observacoes', 'ministerios'):
            w.attrs.setdefault('class', 'form-control rounded-3')
        elif name in ('foto',):
            w.attrs.setdefault('class', 'form-control rounded-3')
        else:
            w.attrs.setdefault('class', 'form-control rounded-3')


class MembroNovoForm(forms.ModelForm):
    """Modal inicial: apenas nome e sexo."""

    class Meta:
        model = Membro
        fields = ('nome_completo', 'sexo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome_completo'].label = _('Nome')
        self.fields['nome_completo'].required = True
        self.fields['sexo'].required = True
        for fname in ('nome_completo', 'sexo'):
            w = self.fields[fname].widget
            w.attrs.setdefault('aria-required', 'true')
            w.attrs['required'] = True
        self.fields['nome_completo'].widget.attrs.setdefault('class', 'form-control rounded-3')
        self.fields['sexo'].widget.attrs.setdefault('class', 'form-select rounded-3')


class MembroCpfTelefoneCleanMixin:
    """clean_cpf / clean_telefone compartilhados (CPF opcional)."""

    def clean_cpf(self):
        raw = self.cleaned_data.get('cpf') or ''
        digits = only_digits_cpf(str(raw))
        if not digits:
            return None
        if len(digits) != 11:
            raise forms.ValidationError(_('O CPF deve conter 11 dígitos.'))
        return digits

    def clean_telefone(self):
        raw = self.cleaned_data.get('telefone') or ''
        digits = re.sub(r'\D', '', str(raw))
        if not digits:
            return ''
        if len(digits) not in (10, 11):
            raise forms.ValidationError(
                _('Informe o telefone com DDD e 8 ou 9 dígitos (fixo ou celular).'),
            )
        return digits


class MembroAdminForm(MembroCpfTelefoneCleanMixin, forms.ModelForm):
    """Admin Django: todos os campos; CPF e telefone com máscara no widget."""

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
        fields = '__all__'
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'data_casamento': forms.DateInput(attrs={'type': 'date'}),
            'data_batismo': forms.DateInput(attrs={'type': 'date'}),
            'foto': ClearableFileInputNomeTruncado(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_html5_date_inputs(
            self,
            'data_nascimento',
            'data_casamento',
            'data_batismo',
        )
        self.fields['nome_completo'].label = _('Nome')
        self.fields['nome_completo'].required = True
        self.fields['sexo'].required = True
        self.fields['cpf'].required = False
        for fname in ('nome_completo', 'sexo'):
            w = self.fields[fname].widget
            w.attrs.setdefault('aria-required', 'true')
            w.attrs['required'] = True
        if self.instance.pk:
            if self.instance.cpf:
                self.initial['cpf'] = self.instance.cpf_formatado
            if self.instance.telefone:
                self.initial['telefone'] = self.instance.telefone_formatado

    def clean_casado_com(self):
        c = self.cleaned_data.get('casado_com')
        inst = self.instance
        if c and inst.pk and c.pk == inst.pk:
            raise forms.ValidationError(_('Não é possível selecionar o próprio membro.'))
        return c

    def clean(self):
        cleaned = super().clean()
        inst = self.instance
        filhos = cleaned.get('filhos')
        if filhos is not None and inst.pk:
            if inst in filhos:
                raise forms.ValidationError(
                    {'filhos': _('Um membro não pode ser filho de si mesmo.')}
                )
        return cleaned


class MembroDadosPessoaisForm(MembroCpfTelefoneCleanMixin, forms.ModelForm):
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
            'endereco',
            'telefone',
            'email',
            'foto',
        )
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
            'endereco': Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control rounded-3',
                }
            ),
            'foto': ClearableFileInputNomeTruncado(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_html5_date_inputs(self, 'data_nascimento')
        self.fields['nome_completo'].label = _('Nome')
        self.fields['nome_completo'].required = True
        self.fields['cpf'].required = False
        if self.instance.pk:
            if self.instance.cpf:
                self.initial['cpf'] = self.instance.cpf_formatado
            if self.instance.telefone:
                self.initial['telefone'] = self.instance.telefone_formatado
        _widget_classes_membro_public(self)


class MembroFamiliaForm(forms.ModelForm):
    class Meta:
        model = Membro
        fields = ('estado_civil', 'casado_com', 'data_casamento')
        widgets = {
            'data_casamento': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_html5_date_inputs(self, 'data_casamento')
        self.fields['casado_com'].widget = forms.HiddenInput()
        self.fields['casado_com'].required = False
        self.fields['estado_civil'].required = False
        if self.instance.pk:
            q = Membro.objects.exclude(pk=self.instance.pk)
            self.fields['casado_com'].queryset = q
        else:
            self.fields['casado_com'].queryset = Membro.objects.all()
        _widget_classes_membro_public(self)

    def clean_casado_com(self):
        c = self.cleaned_data.get('casado_com')
        inst = self.instance
        if c and inst.pk and c.pk == inst.pk:
            raise forms.ValidationError(_('Não é possível selecionar o próprio membro.'))
        return c

    def clean(self):
        cleaned = super().clean()
        inst = self.instance
        ids = [int(x) for x in self.data.getlist('filhos') if str(x).isdigit()]
        qs = Membro.objects.filter(pk__in=ids)
        if inst.pk:
            qs = qs.exclude(pk=inst.pk)
        if inst.pk and inst.pk in ids:
            raise forms.ValidationError(
                _('Um membro não pode ser filho de si mesmo.'),
            )
        cleaned['filhos'] = qs
        est = cleaned.get('estado_civil') or ''
        if est not in ESTADOS_COM_CONJUGE:
            cleaned['casado_com'] = None
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit:
            obj.filhos.set(self.cleaned_data.get('filhos', []))
        return obj


class MembroBatismoForm(forms.ModelForm):
    class Meta:
        model = Membro
        fields = ('batizado', 'data_batismo')
        widgets = {
            'data_batismo': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _configure_html5_date_inputs(self, 'data_batismo')
        _widget_classes_membro_public(self)


class MembroInformacoesForm(forms.ModelForm):
    class Meta:
        model = Membro
        fields = ('locomocao', 'observacoes')
        widgets = {
            'observacoes': Textarea(attrs={'rows': 4, 'class': 'form-control rounded-3'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _widget_classes_membro_public(self)


class MembroMinisteriosForm(forms.ModelForm):
    class Meta:
        model = Membro
        fields = ('ministerios',)
        widgets = {
            'ministerios': Textarea(attrs={'rows': 6, 'class': 'form-control rounded-3'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _widget_classes_membro_public(self)
