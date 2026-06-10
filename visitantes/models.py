import re

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from membros.models import Membro, Sexo


class ConheceuIgrejaPor(models.TextChoices):
    CULTO_FAMILIA = 'culto_familia', _('Culto Família')
    CULTO_JOVEM = 'culto_jovem', _('Culto Jovem')
    EVENTOS = 'eventos', _('Eventos')
    GRUPOS = 'grupos', _('Grupos')
    INSTAGRAM = 'instagram', _('Instagram')
    OUTRO = 'outro', _('Outro')


class VisitanteQuerySet(models.QuerySet):
    def delete(self):
        updated = self.update(ativo=False)
        return updated, {self.model._meta.label: updated}


class VisitanteAtivosManager(models.Manager.from_queryset(VisitanteQuerySet)):
    def get_queryset(self):
        return super().get_queryset().filter(ativo=True)


class Visitante(models.Model):
    ativo = models.BooleanField(_('Ativo no cadastro'), default=True, db_index=True)
    nome_completo = models.CharField(_('Nome completo'), max_length=255)
    nome_conhecido = models.CharField(_('Conhecido por'), max_length=120, blank=True)
    sexo = models.CharField(_('Sexo'), max_length=1, choices=Sexo.choices)
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True)
    endereco = models.TextField(_('Endereço'), blank=True)
    membro_acompanha = models.ForeignKey(
        Membro,
        verbose_name=_('Membro que acompanha'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='visitantes_acompanhados',
    )
    conheceu_por = models.CharField(
        _('Conheceu a igreja por'),
        max_length=30,
        choices=ConheceuIgrejaPor.choices,
        blank=True,
    )
    convertido = models.BooleanField(_('É convertido?'), default=False)
    batizado = models.BooleanField(_('É batizado?'), default=False)
    denominacao = models.CharField(_('Denominação'), max_length=180, blank=True)
    observacoes = models.TextField(_('Obs'), blank=True)
    criado_em = models.DateTimeField(_('Data/hora do cadastro'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now=True)
    criado_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Usuário que cadastrou'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        editable=False,
        related_name='visitantes_cadastrados',
    )

    objects = VisitanteAtivosManager()
    todos = VisitanteQuerySet.as_manager()

    class Meta:
        verbose_name = _('Visitante')
        verbose_name_plural = _('Visitantes')
        ordering = ['nome_completo']

    def __str__(self) -> str:
        return (self.nome_completo or '').strip() or '—'

    def delete(self, using=None, keep_parents=False):
        if self.pk is None:
            raise ValueError('Visitante object cannot be deleted because its id is None.')
        self.ativo = False
        self.save(update_fields=['ativo'])
        return 1, {self._meta.label: 1}

    @property
    def telefone_formatado(self) -> str:
        d = re.sub(r'\D', '', self.telefone or '')
        if len(d) == 11:
            return f'({d[:2]}) {d[2:7]}-{d[7:11]}'
        if len(d) == 10:
            return f'({d[:2]}) {d[2:6]}-{d[6:10]}'
        return self.telefone or ''
