import re
from typing import Optional

from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_cpf_digits


class Sexo(models.TextChoices):
    MASCULINO = 'M', _('Masculino')
    FEMININO = 'F', _('Feminino')


class EstadoCivil(models.TextChoices):
    SOLTEIRO = 'solteiro', _('Solteiro(a)')
    CASADO = 'casado', _('Casado(a)')
    DIVORCIADO = 'divorciado', _('Divorciado(a)')
    VIUVO = 'viuvo', _('Viúvo(a)')
    UNIAO_ESTAVEL = 'uniao_estavel', _('União estável')
    SEPARADO = 'separado', _('Separado(a)')
    OUTRO = 'outro', _('Outro')


ESTADOS_COM_CONJUGE = frozenset(
    (
        EstadoCivil.CASADO,
        EstadoCivil.UNIAO_ESTAVEL,
    )
)


class Locomocao(models.TextChoices):
    PE = 'pe', _('A pé')
    CARRO = 'carro', _('Carro')
    MOTO = 'moto', _('Moto')
    BICICLETA = 'bicicleta', _('Bicicleta')
    APPS = 'apps', _('Apps')
    OUTRO = 'outro', _('Outro')


class Membro(models.Model):
    nome_completo = models.CharField(_('Nome completo'), max_length=255)
    nome_conhecido = models.CharField(_('Conhecido por:'), max_length=120, blank=True)
    cpf = models.CharField(
        _('CPF'),
        max_length=11,
        unique=True,
        blank=True,
        null=True,
        validators=[validate_cpf_digits],
    )
    data_nascimento = models.DateField(_('Data de nascimento'), null=True, blank=True)
    sexo = models.CharField(
        _('Sexo'),
        max_length=1,
        choices=Sexo.choices,
        default=Sexo.MASCULINO,
    )
    endereco = models.TextField(_('Endereço'), blank=True)
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True)
    email = models.EmailField(_('E-mail'), blank=True)

    estado_civil = models.CharField(
        _('Estado civil'),
        max_length=20,
        choices=EstadoCivil.choices,
        blank=True,
    )
    casado_com = models.ForeignKey(
        'self',
        verbose_name=_('Casado(a) com'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parceiros',
    )
    data_casamento = models.DateField(_('Data de casamento'), null=True, blank=True)

    filhos = models.ManyToManyField(
        'self',
        verbose_name=_('Filhos(as)'),
        symmetrical=False,
        related_name='pais',
        blank=True,
        help_text=_('Outros membros cadastrados como filhos.'),
    )

    batizado = models.BooleanField(_('É batizado(a)?'), default=False)
    data_batismo = models.DateField(_('Data de batismo'), null=True, blank=True)

    locomocao = models.CharField(
        _('Locomoção'),
        max_length=20,
        choices=Locomocao.choices,
        blank=True,
    )
    observacoes = models.TextField(_('Observações'), blank=True)

    ministerios = models.TextField(
        _('Ministérios'),
        blank=True,
        help_text=_('Participação em ministérios ou equipes.'),
    )

    foto = models.ImageField(_('Foto'), upload_to='membros/fotos/', blank=True, null=True)

    class Meta:
        verbose_name = _('Membro')
        verbose_name_plural = _('Membros')
        ordering = ['nome_completo']

    def __str__(self) -> str:
        return self.nome_conhecido.strip() if self.nome_conhecido else self.nome_completo

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        spouse_fields_dirty = update_fields is None or any(
            name in update_fields
            for name in ('casado_com', 'estado_civil', 'data_casamento')
        )
        old_partner_id = None
        if spouse_fields_dirty and self.pk:
            old_partner_id = (
                Membro.objects.filter(pk=self.pk)
                .values_list('casado_com_id', flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        if spouse_fields_dirty:
            self._espelhar_conjuge(old_partner_id)

    def _espelhar_conjuge(self, old_partner_id: Optional[int]) -> None:
        """Atualiza o outro membro para manter casamento / união espelhado (sem recursão em save())."""
        new_pid = self.casado_com_id
        union_ok = (self.estado_civil or '') in ESTADOS_COM_CONJUGE and bool(new_pid)

        if old_partner_id and (
            old_partner_id != new_pid or not union_ok
        ):
            Membro.objects.filter(pk=old_partner_id, casado_com_id=self.pk).update(
                casado_com=None,
                estado_civil='',
                data_casamento=None,
            )

        if union_ok and new_pid:
            Membro.objects.filter(casado_com_id=new_pid).exclude(pk=self.pk).update(
                casado_com=None,
                estado_civil='',
                data_casamento=None,
            )
            Membro.objects.filter(pk=new_pid).exclude(pk=self.pk).update(
                casado_com_id=self.pk,
                estado_civil=self.estado_civil,
                data_casamento=self.data_casamento,
            )
        elif new_pid and not union_ok:
            Membro.objects.filter(pk=new_pid, casado_com_id=self.pk).update(
                casado_com=None,
            )

    @property
    def cpf_formatado(self) -> str:
        """Exibe CPF no padrão 000.000.000-00."""
        c = self.cpf or ''
        if len(c) != 11:
            return c
        return f'{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:11]}'

    @property
    def telefone_formatado(self) -> str:
        """Exibe telefone (84) 99999-9999 ou (84) 9999-9999 a partir dos dígitos."""
        d = re.sub(r'\D', '', self.telefone or '')
        if len(d) == 11:
            return f'({d[:2]}) {d[2:7]}-{d[7:11]}'
        if len(d) == 10:
            return f'({d[:2]}) {d[2:6]}-{d[6:10]}'
        return self.telefone or ''
