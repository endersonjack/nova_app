from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


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

    class Meta:
        verbose_name = _('Perfil de usuário')
        verbose_name_plural = _('Perfis de usuário')

    def __str__(self) -> str:
        u = self.user.get_username() if self.user_id else '—'
        if self.membro_id:
            return f'{u} → {self.membro}'
        return u
