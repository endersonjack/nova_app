"""Expõe o utilizador da request atual aos sinais de auditoria (context var)."""

from __future__ import annotations

import contextvars

_auditoria_usuario: contextvars.ContextVar = contextvars.ContextVar(
    'auditoria_usuario',
    default=None,
)


def get_auditoria_usuario():
    return _auditoria_usuario.get()


class AuditoriaUsuarioMiddleware:
    """Define o utilizador autenticado para `get_auditoria_usuario()` durante o pedido."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = None
        u = getattr(request, 'user', None)
        if u is not None and u.is_authenticated:
            user = u
        token = _auditoria_usuario.set(user)
        try:
            return self.get_response(request)
        finally:
            _auditoria_usuario.reset(token)
