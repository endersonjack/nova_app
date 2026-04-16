import re

from django import forms
from django.forms import Textarea
from django.utils.translation import gettext_lazy as _

from .models import ESTADOS_COM_CONJUGE, EstadoCivil, Membro, Sexo
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


def _widget_classes_membro_public(form, exclude=('filhos',)):
    for name, field in form.fields.items():
        if name in exclude:
            continue
        w = field.widget
        if name == 'batizado':
            w.attrs.setdefault('class', 'form-check-input')
        elif name in ('sexo', 'locomocao', 'estado_civil'):
            w.attrs.setdefault('class', 'form-select rounded-3')
        elif name == 'casado_com':
            w.attrs.setdefault('class', 'form-select rounded-3')
        elif name in ('endereco', 'observacoes', 'ministerios', 'maps_embed'):
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
            'maps_embed': Textarea(
                attrs={
                    'rows': 3,
                    'class': 'form-control',
                    'placeholder': 'https://maps.google.com/... ou <iframe ...>',
                }
            ),
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
            'telefone',
            'email',
            'foto',
        )
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}),
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


class MembroLocalidadeForm(forms.ModelForm):
    class Meta:
        model = Membro
        fields = ('endereco', 'maps_embed')
        widgets = {
            'endereco': Textarea(
                attrs={
                    'rows': 4,
                    'class': 'form-control rounded-3',
                }
            ),
            'maps_embed': Textarea(
                attrs={
                    'rows': 4,
                    'class': 'form-control rounded-3',
                    'placeholder': 'https://maps.google.com/... ou <iframe ...>',
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['endereco'].required = False
        self.fields['maps_embed'].required = False
        self.fields['espelhar_endereco_conjuge'] = forms.BooleanField(
            label=_('Adicionar o mesmo endereço: cônjuge'),
            required=False,
            initial=False,
            help_text=_(
                'Inclui endereço, mapa embed e coordenadas no cadastro do cônjuge.'
            ),
            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        )
        self.fields['espelhar_endereco_filhos'] = forms.BooleanField(
            label=_('Adicionar o mesmo endereço: filhos'),
            required=False,
            initial=False,
            help_text=_(
                'Inclui endereço, mapa embed e coordenadas em todos os filhos '
                'vinculados.'
            ),
            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        )
        if not (self.instance.pk and self.instance.casado_com_id):
            self.fields['espelhar_endereco_conjuge'].widget.attrs['disabled'] = True
        if not (self.instance.pk and self.instance.filhos.exists()):
            self.fields['espelhar_endereco_filhos'].widget.attrs['disabled'] = True
        _widget_classes_membro_public(
            self,
            exclude=('espelhar_endereco_conjuge', 'espelhar_endereco_filhos'),
        )

    def clean(self):
        cleaned = super().clean()
        inst = self.instance
        conj = bool(cleaned.get('espelhar_endereco_conjuge'))
        filh = bool(cleaned.get('espelhar_endereco_filhos'))
        if not (inst.pk and inst.casado_com_id):
            conj = False
        if not (inst.pk and inst.filhos.exists()):
            filh = False
        cleaned['espelhar_endereco_conjuge'] = conj
        cleaned['espelhar_endereco_filhos'] = filh
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit:
            payload = {
                'endereco': obj.endereco,
                'maps_embed': obj.maps_embed,
                'latitude': obj.latitude,
                'longitude': obj.longitude,
            }
            if self.cleaned_data.get('espelhar_endereco_conjuge') and obj.casado_com_id:
                Membro.objects.filter(pk=obj.casado_com_id).update(**payload)
            if self.cleaned_data.get('espelhar_endereco_filhos'):
                ids = list(obj.filhos.values_list('pk', flat=True))
                if ids:
                    Membro.objects.filter(pk__in=ids).update(**payload)
        return obj


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
        self.fields['casado_com'].required = False
        self.fields['casado_com'].empty_label = _('Selecione…')
        self.fields['estado_civil'].required = False
        if self.is_bound:
            est_now = (self.data.get('estado_civil') or '').strip()
        else:
            est_now = (self.instance.estado_civil or '').strip()
        conjuge_ok = est_now == EstadoCivil.CASADO.value
        if not conjuge_ok and not self.is_bound:
            self.initial = dict(self.initial)
            self.initial['casado_com'] = None
        if not conjuge_ok:
            self.fields['data_casamento'].widget.attrs['readonly'] = True
        self.fields['adicionar_filhos_conjuge'] = forms.BooleanField(
            label=_('Adicionar filhos ao cônjuge'),
            required=False,
            initial=True,
            help_text=_(
                'Se marcado e houver cônjuge, a mesma lista de filhos será '
                'salva também para o cônjuge.'
            ),
            widget=forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        )
        if not conjuge_ok:
            self.fields['adicionar_filhos_conjuge'].widget.attrs['disabled'] = True
        if self.instance.pk:
            q = Membro.objects.exclude(pk=self.instance.pk).order_by(
                'nome_completo',
            )
            # Comparar com .value: `instance.sexo in (Sexo.MASCULINO, …)` pode falhar com TextChoices.
            sx = (self.instance.sexo or '').strip().upper()
            if sx == Sexo.MASCULINO.value:
                q = q.filter(sexo__iexact=Sexo.FEMININO.value)
            elif sx == Sexo.FEMININO.value:
                q = q.filter(sexo__iexact=Sexo.MASCULINO.value)
            self.fields['casado_com'].queryset = q
            self.filhos_choice_queryset = Membro.objects.exclude(
                pk=self.instance.pk,
            ).order_by('nome_completo')
        else:
            self.fields['casado_com'].queryset = Membro.objects.all()
            self.filhos_choice_queryset = Membro.objects.all().order_by(
                'nome_completo',
            )
        _widget_classes_membro_public(
            self,
            exclude=('filhos', 'adicionar_filhos_conjuge'),
        )

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
        if len(ids) != len(set(ids)):
            raise forms.ValidationError(
                _('Não é possível repetir o mesmo filho na lista.'),
            )
        qs = Membro.objects.filter(pk__in=ids)
        if inst.pk:
            qs = qs.exclude(pk=inst.pk)
        if inst.pk and inst.pk in ids:
            raise forms.ValidationError(
                _('Um membro não pode ser filho de si mesmo.'),
            )
        if inst.pk and ids:
            allowed = set(
                self.filhos_choice_queryset.values_list('pk', flat=True),
            )
            bad = [i for i in ids if i not in allowed]
            if bad:
                raise forms.ValidationError(
                    _('Seleção de filho inválida.'),
                )
        cleaned['filhos'] = qs
        est = cleaned.get('estado_civil') or ''
        if est not in ESTADOS_COM_CONJUGE:
            cleaned['casado_com'] = None
            cleaned['data_casamento'] = None
        else:
            c = cleaned.get('casado_com')
            sx = (self.instance.sexo or '').strip().upper()
            if c and self.instance.pk and sx in (
                Sexo.MASCULINO.value,
                Sexo.FEMININO.value,
            ):
                opp_letter = (
                    Sexo.FEMININO.value
                    if sx == Sexo.MASCULINO.value
                    else Sexo.MASCULINO.value
                )
                if (c.sexo or '').strip().upper() != opp_letter:
                    raise forms.ValidationError(
                        {
                            'casado_com': _(
                                'O cônjuge deve ser do sexo oposto ao do membro.'
                            ),
                        }
                    )
        mirror = bool(cleaned.get('adicionar_filhos_conjuge'))
        if (
            (cleaned.get('estado_civil') or '').strip()
            != EstadoCivil.CASADO.value
            or not cleaned.get('casado_com')
        ):
            mirror = False
        cleaned['adicionar_filhos_conjuge'] = mirror
        return cleaned

    def save(self, commit=True):
        obj = super().save(commit=commit)
        if commit:
            filhos = self.cleaned_data.get('filhos', [])
            obj.filhos.set(filhos)
            if self.cleaned_data.get('adicionar_filhos_conjuge') and obj.casado_com_id:
                obj.casado_com.filhos.set(filhos)
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
