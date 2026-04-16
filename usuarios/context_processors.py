from .models import UserProfile


def usuario_membro(request):
    """Expõe o Membro vinculado ao usuário logado (se houver) em todos os templates."""
    if not request.user.is_authenticated:
        return {
            'membro_logado': None,
            'perfil_usuario': None,
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
        }
    return {
        'membro_logado': perfil.membro,
        'perfil_usuario': perfil,
    }
