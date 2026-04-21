from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser

from .middleware import get_auditoria_usuario
from .models import LogAuditoria


def registrar_auditoria(
    *,
    tipo: str,
    modulo: str,
    detalhes: str,
    usuario: AbstractBaseUser | None = None,
    objeto_tipo: str = '',
    objeto_id: int | None = None,
) -> LogAuditoria:
    """
    Persiste um registo. Se `usuario` for None, usa o da request (middleware)
    ou None (ex.: comandos de gestão).
    """
    if usuario is None:
        usuario = get_auditoria_usuario()
    return LogAuditoria.objects.create(
        usuario=usuario,
        tipo=tipo,
        modulo=modulo,
        detalhes=detalhes,
        objeto_tipo=objeto_tipo or '',
        objeto_id=objeto_id,
    )


def nome_exibicao_utilizador(user) -> str:
    if user is None or not getattr(user, 'is_authenticated', False):
        return 'Sistema'
    u = user.get_username()
    fn = (getattr(user, 'get_full_name', lambda: '')() or '').strip()
    if fn:
        return f'{fn} ({u})'
    return u
