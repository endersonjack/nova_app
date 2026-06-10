import re

from django import forms
from django.utils.translation import gettext_lazy as _

from membros.models import Membro

from .models import Visitante


def _widget_classes_visitante(form):
    for name, field in form.fields.items():
        w = field.widget
        if name in ('sexo', 'membro_acompanha', 'conheceu_por'):
            w.attrs.setdefault('class', 'form-select rounded-3')
        elif name in ('convertido', 'batizado'):
            w.attrs.setdefault('class', 'form-check-input')
        elif name in ('endereco', 'observacoes'):
            w.attrs.setdefault('class', 'form-control rounded-3')
        else:
            w.attrs.setdefault('class', 'form-control rounded-3')


class VisitanteForm(forms.ModelForm):
    telefone = forms.CharField(
        label=_('Telefone'),
        max_length=16,
        required=False,
        help_text=_('Ex.: (84) 99999-9999'),
    )

    class Meta:
        model = Visitante
        fields = (
            'nome_completo',
            'nome_conhecido',
            'sexo',
            'telefone',
            'endereco',
            'membro_acompanha',
            'conheceu_por',
            'convertido',
            'batizado',
            'denominacao',
            'observacoes',
        )
        widgets = {
            'endereco': forms.TextInput(),
            'observacoes': forms.TextInput(),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['nome_completo'].required = True
        self.fields['sexo'].required = True
        self.fields['membro_acompanha'].queryset = Membro.objects.order_by('nome_completo')
        self.fields['membro_acompanha'].empty_label = _('Selecione…')
        self.fields['conheceu_por'].empty_label = _('Selecione…')
        if self.instance.pk and self.instance.telefone:
            self.initial['telefone'] = self.instance.telefone_formatado
        for fname in ('nome_completo', 'sexo'):
            w = self.fields[fname].widget
            w.attrs.setdefault('aria-required', 'true')
            w.attrs['required'] = True
        _widget_classes_visitante(self)

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
