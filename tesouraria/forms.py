from calendar import monthrange
from datetime import date

from django import forms
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.translation import gettext_lazy as _

from usuarios.familia import membros_visiveis_queryset

from .fields import BRLDecimalField
from .money_format import format_brl
from .models import (
    CategoriaFinanceira,
    CompetenciaTesouraria,
    ContaFinanceira,
    EventoFinanceiro,
    LancamentoFinanceiro,
    TipoCategoriaFinanceira,
    TipoContaFinanceira,
)


class CompetenciaTesourariaForm(forms.ModelForm):
    class Meta:
        model = CompetenciaTesouraria
        fields = (
            'mes',
            'ano',
            'descricao',
            'fechada',
            'data_fechamento',
            'competencia_continua',
        )
        widgets = {
            'mes': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1,
                    'max': 12,
                    'required': True,
                }
            ),
            'ano': forms.NumberInput(
                attrs={
                    'class': 'form-control',
                    'min': 1900,
                    'max': 2100,
                    'required': True,
                }
            ),
            'descricao': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': 30}
            ),
            'fechada': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'competencia_continua': forms.CheckboxInput(
                attrs={'class': 'form-check-input'}
            ),
            'data_fechamento': forms.DateTimeInput(
                attrs={
                    'class': 'form-control',
                    'type': 'datetime-local',
                },
                format='%Y-%m-%dT%H:%M',
            ),
        }
        labels = {
            'mes': _('Mês'),
            'ano': _('Ano'),
            'descricao': _('Descrição'),
            'fechada': _('Fechada'),
            'data_fechamento': _('Data de fechamento'),
            'competencia_continua': _('Competência contínua'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = False
        self.fields['data_fechamento'].required = False
        self.fields['competencia_continua'].help_text = _(
            'Inclui no saldo geral o acumulado da competência anterior (e da cadeia de meses anteriores que também forem contínuos).'
        )
        self.fields['data_fechamento'].input_formats = [
            '%Y-%m-%dT%H:%M',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%d %H:%M',
            '%d/%m/%Y %H:%M',
        ]
        if self.instance and self.instance.pk and self.instance.data_fechamento:
            dt = self.instance.data_fechamento
            if timezone.is_aware(dt):
                dt = timezone.localtime(dt)
            self.initial['data_fechamento'] = dt.strftime('%Y-%m-%dT%H:%M')

    def clean(self):
        cleaned = super().clean()
        mes = cleaned.get('mes')
        ano = cleaned.get('ano')
        if mes is not None and ano is not None:
            qs = CompetenciaTesouraria.objects.filter(mes=mes, ano=ano)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    _('Já existe uma competência para este mês e ano.')
                )
        return cleaned


class ContaFinanceiraForm(forms.ModelForm):
    class Meta:
        model = ContaFinanceira
        fields = ('nome', 'tipo', 'descricao', 'ativa')
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'tipo': forms.HiddenInput(),
            'descricao': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2}
            ),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome': _('Nome'),
            'descricao': _('Descrição'),
            'ativa': _('Ativa'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['descricao'].required = False

    def clean_tipo(self):
        tipo = self.cleaned_data.get('tipo')
        valid = {c.value for c in TipoContaFinanceira}
        if tipo not in valid:
            raise forms.ValidationError(_('Tipo de conta inválido.'))
        return tipo


class _LancamentoFinanceiroBaseForm(forms.ModelForm):
    """Campos e validações comuns a entrada e saída."""

    def __init__(self, *args, competencia=None, **kwargs):
        self._competencia = competencia
        super().__init__(*args, **kwargs)
        self.fields['numero_documento'].required = False
        self.fields['descricao'].required = False
        self.fields['observacao'].required = False
        if competencia:
            _weekday_first, last = monthrange(competencia.ano, competencia.mes)
            self.fields['data'].required = False
            self.fields['data'].widget = forms.HiddenInput()
            self.fields['dia'] = forms.IntegerField(
                label=_('Dia'),
                min_value=1,
                max_value=last,
                widget=forms.NumberInput(
                    attrs={
                        'class': 'form-control',
                        'min': 1,
                        'max': last,
                        'inputmode': 'numeric',
                    }
                ),
            )
            if not self.is_bound:
                if self.instance.pk and self.instance.data:
                    d = self.instance.data
                    if d.year == competencia.ano and d.month == competencia.mes:
                        self.initial['dia'] = d.day
                    else:
                        self.initial['dia'] = 1
                else:
                    hoje = date.today()
                    if hoje.year == competencia.ano and hoje.month == competencia.mes:
                        self.initial['dia'] = min(hoje.day, last)
                    else:
                        self.initial['dia'] = 1
        else:
            self.fields['data'].input_formats = ['%Y-%m-%d', '%d/%m/%Y']
        vlab = self.fields['valor'].label
        vreq = self.fields['valor'].required
        self.fields['valor'] = BRLDecimalField(
            label=vlab,
            required=vreq,
            max_digits=12,
            decimal_places=2,
            widget=forms.TextInput(
                attrs={
                    'class': 'form-control js-tesouraria-valor-brl',
                    'placeholder': '0,00',
                    'autocomplete': 'off',
                }
            ),
        )
        if (
            self.instance
            and self.instance.pk
            and self.instance.valor is not None
            and not self.is_bound
        ):
            self.initial['valor'] = format_brl(self.instance.valor)
        if 'evento' in self.fields:
            self.fields['evento'].required = False
            self.fields['evento'].queryset = EventoFinanceiro.objects.filter(
                ativa=True,
            ).order_by('nome')
            self.fields['evento'].empty_label = _('— Nenhum —')

    def clean_valor(self):
        valor = self.cleaned_data.get('valor')
        if valor is not None and valor <= 0:
            raise forms.ValidationError(_('O valor deve ser maior que zero.'))
        return valor

    def clean(self):
        cleaned = super().clean()
        comp = self._competencia
        if not (comp and 'dia' in self.fields):
            return cleaned
        dia = cleaned.get('dia')
        if dia is None:
            legacy = self.data.get('data')
            if legacy:
                d = parse_date(str(legacy))
                if d and d.year == comp.ano and d.month == comp.mes:
                    dia = d.day
        if dia is None:
            self.add_error('dia', _('Informe o dia.'))
            return cleaned
        _weekday_first, last = monthrange(comp.ano, comp.mes)
        if dia < 1 or dia > last:
            self.add_error('dia', _('Dia inválido para este mês.'))
            return cleaned
        cleaned['data'] = date(comp.ano, comp.mes, dia)
        return cleaned


class LancamentoEntradaForm(_LancamentoFinanceiroBaseForm):
    class Meta:
        model = LancamentoFinanceiro
        fields = (
            'membro',
            'categoria',
            'data',
            'valor',
            'numero_documento',
            'descricao',
            'observacao',
            'evento',
        )
        widgets = {
            'membro': forms.HiddenInput(),
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'data': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'numero_documento': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': 50}
            ),
            'descricao': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': 255}
            ),
            'observacao': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2}
            ),
            'evento': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'categoria': _('Categoria de entrada'),
            'membro': _('Membro'),
            'data': _('Data'),
            'valor': _('Valor (R$)'),
            'numero_documento': _('Nº do documento'),
            'descricao': _('Descrição'),
            'observacao': _('Obs.'),
            'evento': _('Eventos'),
        }

    def __init__(self, *args, competencia=None, **kwargs):
        super().__init__(*args, competencia=competencia, **kwargs)
        self.fields['categoria'].queryset = CategoriaFinanceira.objects.filter(
            ativa=True,
            tipo=TipoCategoriaFinanceira.ENTRADA,
        ).order_by('nome')
        self.fields['membro'].required = False


class LancamentoSaidaForm(_LancamentoFinanceiroBaseForm):
    class Meta:
        model = LancamentoFinanceiro
        fields = (
            'categoria',
            'data',
            'valor',
            'numero_documento',
            'descricao',
            'observacao',
            'evento',
        )
        widgets = {
            'categoria': forms.Select(attrs={'class': 'form-select'}),
            'data': forms.DateInput(
                attrs={'class': 'form-control', 'type': 'date'},
                format='%Y-%m-%d',
            ),
            'numero_documento': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': 50}
            ),
            'descricao': forms.TextInput(
                attrs={'class': 'form-control', 'maxlength': 255}
            ),
            'observacao': forms.Textarea(
                attrs={'class': 'form-control', 'rows': 2}
            ),
            'evento': forms.Select(attrs={'class': 'form-select'}),
        }
        labels = {
            'categoria': _('Categoria de saída'),
            'data': _('Data'),
            'valor': _('Valor (R$)'),
            'numero_documento': _('Nº do documento'),
            'descricao': _('Descrição'),
            'observacao': _('Obs.'),
            'evento': _('Eventos'),
        }

    def __init__(self, *args, competencia=None, **kwargs):
        super().__init__(*args, competencia=competencia, **kwargs)
        self.fields['categoria'].queryset = CategoriaFinanceira.objects.filter(
            ativa=True,
            tipo=TipoCategoriaFinanceira.SAIDA,
        ).order_by('nome')


class EventoFinanceiroForm(forms.ModelForm):
    class Meta:
        model = EventoFinanceiro
        fields = ('nome', 'ativa')
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome': _('Nome'),
            'ativa': _('Ativa'),
        }


class CategoriaFinanceiraForm(forms.ModelForm):
    class Meta:
        model = CategoriaFinanceira
        fields = ('nome', 'tipo', 'ativa')
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control', 'maxlength': 100}),
            'tipo': forms.Select(attrs={'class': 'form-select'}),
            'ativa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'nome': _('Nome'),
            'tipo': _('Tipo'),
            'ativa': _('Ativa'),
        }
