"""Permissões por módulo (UserProfile.papel + modulos)."""

from __future__ import annotations

from functools import wraps

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from django.http import HttpRequest
from django.utils.translation import gettext as _

from .models import ModuloSistema, UserProfile


def get_perfil(user) -> UserProfile | None:
    if not user.is_authenticated:
        return None
    return getattr(user, 'perfil', None)


def usuario_pode_modulo(user, codigo: str, *, edicao: bool = False) -> bool:
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    if codigo not in dict(ModuloSistema.choices):
        return False
    perfil = get_perfil(user)
    if perfil is None:
        return False
    if edicao:
        return perfil.pode_editar_modulo(codigo)
    return perfil.pode_ver_modulo(codigo)


def requer_modulo(codigo: str, *, edicao: bool = False):
    """
    Exige login e permissão no módulo `codigo` (ModuloSistema).
    edicao=False: leitura (lista, detalhe, GET).
    edicao=True: alteração (POST de criação/edição/exclusão).
    """

    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request: HttpRequest, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if not usuario_pode_modulo(request.user, codigo, edicao=edicao):
                raise PermissionDenied(_('Sem permissão para aceder a este módulo.'))
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator
