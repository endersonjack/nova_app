from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class ModuloSistema(models.TextChoices):
    MEMBROS = 'membros', _('Membros')
    TESOURARIA = 'tesouraria', _('Tesouraria')
    VISITANTES = 'visitantes', _('Visitantes')
    SEMINARIO = 'seminario', _('Seminário')
    AUDITORIA = 'auditoria', _('Auditoria')


class PapelMembro(models.TextChoices):
    COMUM = 'comum', _('Membro comum')
    EDITOR = 'editor', _('Membro editor')
    ADMIN = 'admin', _('Membro admin')


class UserProfile(models.Model):
    """Liga um usuário de login a um cadastro de Membro (dados no app membros)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='perfil',
        verbose_name=_('Usuário'),
    )
    membro = models.OneToOneField(
        'membros.Membro',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='perfil_usuario',
        verbose_name=_('Membro'),
    )
    papel = models.CharField(
        _('Papel'),
        max_length=20,
        choices=PapelMembro.choices,
        default=PapelMembro.COMUM,
        help_text=_(
            'Comum: só visualização nos módulos marcados. '
            'Editor: criar/editar/excluir nos módulos marcados. '
            'Admin: todos os módulos e acesso ao Django Admin (marque também “Staff” ou use este papel).'
        ),
    )
    modulos = models.JSONField(
        _('Módulos'),
        default=list,
        blank=True,
        help_text=_(
            'Para Comum e Editor, marque os módulos permitidos. '
            'Para Admin, este campo é ignorado (acesso total à aplicação).'
        ),
    )

    class Meta:
        verbose_name = _('Perfil de usuário')
        verbose_name_plural = _('Perfis de usuário')

    def __str__(self) -> str:
        u = self.user.get_username() if self.user_id else '—'
        if self.membro_id:
            return f'{u} → {self.membro}'
        return u

    def modulos_normalizados(self) -> list[str]:
        raw = self.modulos
        if not isinstance(raw, list):
            return []
        valid = {c for c, _ in ModuloSistema.choices}
        return [x for x in raw if isinstance(x, str) and x in valid]

    def modulos_efetivos(self) -> frozenset[str]:
        if self.papel == PapelMembro.ADMIN:
            return frozenset(c for c, _ in ModuloSistema.choices)
        return frozenset(self.modulos_normalizados())

    def pode_ver_modulo(self, codigo: str) -> bool:
        valid = frozenset(c for c, _ in ModuloSistema.choices)
        if codigo not in valid:
            return False
        return codigo in self.modulos_efetivos()

    def pode_editar_modulo(self, codigo: str) -> bool:
        if self.papel == PapelMembro.ADMIN:
            return True
        if self.papel != PapelMembro.EDITOR:
            return False
        return codigo in self.modulos_efetivos()

    def rotulos_modulos(self) -> str:
        if self.papel == PapelMembro.ADMIN:
            return str(_('Todos'))
        labels = dict(ModuloSistema.choices)
        parts = [str(labels[c]) for c in self.modulos_normalizados() if c in labels]
        return ', '.join(parts) if parts else '—'

    def save(self, *args, **kwargs):
        if self.papel == PapelMembro.ADMIN:
            self.modulos = []
        super().save(*args, **kwargs)
        if self.papel == PapelMembro.ADMIN and self.user_id:
            u = self.user
            if not u.is_superuser and not u.is_staff:
                u.is_staff = True
                u.save(update_fields=['is_staff'])
        elif self.user_id:
            u = self.user
            if not u.is_superuser and u.is_staff and self.papel != PapelMembro.ADMIN:
                u.is_staff = False
                u.save(update_fields=['is_staff'])
