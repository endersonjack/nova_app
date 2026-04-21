from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class TipoRegistoAuditoria(models.TextChoices):
    CRIACAO = 'criacao', _('Criação')
    REMOCAO = 'remocao', _('Remoção')
    EDICAO = 'edicao', _('Edição')
    ALTERACAO = 'alteracao', _('Alteração')


class LogAuditoria(models.Model):
    """Registo imutável de uma ação rastreada (ex.: alterações em Membros)."""

    criado_em = models.DateTimeField(_('Data e hora'), auto_now_add=True, db_index=True)
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_('Utilizador'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='registos_auditoria',
    )
    tipo = models.CharField(
        _('Tipo'),
        max_length=20,
        choices=TipoRegistoAuditoria.choices,
        db_index=True,
    )
    modulo = models.CharField(
        _('Módulo'),
        max_length=32,
        db_index=True,
        help_text=_('Código do módulo (ex.: membros, tesouraria).'),
    )
    detalhes = models.TextField(_('Detalhes'))
    objeto_tipo = models.CharField(
        _('Tipo de objeto'),
        max_length=120,
        blank=True,
        help_text=_('Ex.: membros.Membro'),
    )
    objeto_id = models.PositiveIntegerField(
        _('ID do objeto'),
        null=True,
        blank=True,
        db_index=True,
    )

    class Meta:
        verbose_name = _('Registo de auditoria')
        verbose_name_plural = _('Registos de auditoria')
        ordering = ['-criado_em']

    def __str__(self) -> str:
        u = self.usuario.get_username() if self.usuario_id else '—'
        return f'{self.criado_em:%Y-%m-%d %H:%M} · {u} · {self.get_tipo_display()}'
