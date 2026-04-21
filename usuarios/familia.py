"""Regras de visibilidade de membros para o papel «comum» (apenas família vinculada)."""

from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser

from membros.models import Membro

from .models import PapelMembro, UserProfile


def pks_familia_membro(membro: Membro) -> frozenset[int]:
    """Pks do próprio membro, cônjuge, filhos(as), pai e mãe cadastrados."""
    if not membro.pk:
        return frozenset()
    ids = {membro.pk}
    if membro.casado_com_id:
        ids.add(membro.casado_com_id)
    ids |= set(membro.filhos.values_list('pk', flat=True))
    if membro.pai_id:
        ids.add(membro.pai_id)
    if membro.mae_id:
        ids.add(membro.mae_id)
    return frozenset(ids)


def perfil_membro_comum_restrito(user: AbstractBaseUser) -> bool:
    if not user.is_authenticated or user.is_superuser:
        return False
    perfil: UserProfile | None = getattr(user, 'perfil', None)
    return bool(perfil and perfil.papel == PapelMembro.COMUM)


def membros_visiveis_queryset(user: AbstractBaseUser):
    """
    Queryset de membros ativos visíveis ao utilizador.
    Papel comum: só a família do `UserProfile.membro`; sem vínculo → vazio.
    """
    if not user.is_authenticated:
        return Membro.objects.none()
    if user.is_superuser:
        return Membro.objects.all()
    perfil: UserProfile | None = getattr(user, 'perfil', None)
    if not perfil or perfil.papel != PapelMembro.COMUM:
        return Membro.objects.all()
    if not perfil.membro_id:
        return Membro.objects.none()
    m = perfil.membro
    if not m.pk:
        return Membro.objects.none()
    return Membro.objects.filter(pk__in=pks_familia_membro(m))
