from .familia import perfil_membro_comum_restrito
from .models import ModuloSistema, UserProfile
from .permissions import usuario_pode_modulo


def _acesso_modulos_por_codigo(user) -> dict[str, dict[str, bool]]:
    out: dict[str, dict[str, bool]] = {}
    for codigo, _label in ModuloSistema.choices:
        out[codigo] = {
            'ver': usuario_pode_modulo(user, codigo, edicao=False),
            'editar': usuario_pode_modulo(user, codigo, edicao=True),
        }
    return out


def _primeiro_nome(nome: str) -> str:
    partes = (nome or '').strip().split()
    return partes[0] if partes else ''


def _sidebar_usuario(user, membro=None) -> dict[str, str]:
    if not user.is_authenticated:
        return {
            'sidebar_user_primary': 'Visitante',
            'sidebar_user_secondary': '',
        }
    if membro:
        nome_completo = (membro.nome_completo or '').strip()
        nome_principal = (membro.nome_conhecido or '').strip() or _primeiro_nome(nome_completo)
        return {
            'sidebar_user_primary': nome_principal or user.get_username(),
            'sidebar_user_secondary': nome_completo or user.get_username(),
        }
    nome_completo = (user.get_full_name() or '').strip()
    nome_principal = _primeiro_nome(nome_completo) or user.get_username()
    return {
        'sidebar_user_primary': nome_principal,
        'sidebar_user_secondary': nome_completo or user.get_username(),
    }


def usuario_membro(request):
    """Expõe o Membro vinculado ao usuário logado (se houver) em todos os templates."""
    if not request.user.is_authenticated:
        return {
            'membro_logado': None,
            'perfil_usuario': None,
            **_sidebar_usuario(request.user),
            'acesso_modulos': {},
            'pode_acesso_django_admin': False,
            'membro_comum_somente_familia': False,
        }
    perfil = (
        UserProfile.objects.select_related('membro')
        .filter(user=request.user)
        .first()
    )
    if not perfil:
        return {
            'membro_logado': None,
            'perfil_usuario': None,
            **_sidebar_usuario(request.user),
            'acesso_modulos': {},
            'pode_acesso_django_admin': request.user.is_superuser,
            'membro_comum_somente_familia': False,
        }
    return {
        'membro_logado': perfil.membro,
        'perfil_usuario': perfil,
        **_sidebar_usuario(request.user, perfil.membro),
        'acesso_modulos': _acesso_modulos_por_codigo(request.user),
        'pode_acesso_django_admin': request.user.is_superuser or request.user.is_staff,
        'membro_comum_somente_familia': perfil_membro_comum_restrito(request.user),
    }
