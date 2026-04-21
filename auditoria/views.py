from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.shortcuts import render

from usuarios.permissions import requer_modulo

from .models import LogAuditoria, TipoRegistoAuditoria

User = get_user_model()


def _tipo_badge_class(tipo: str) -> str:
    return {
        TipoRegistoAuditoria.CRIACAO: 'success',
        TipoRegistoAuditoria.REMOCAO: 'danger',
        TipoRegistoAuditoria.EDICAO: 'info',
        TipoRegistoAuditoria.ALTERACAO: 'warning',
    }.get(tipo, 'secondary')


@requer_modulo('auditoria', edicao=False)
def index(request):
    qs = LogAuditoria.objects.select_related('usuario').order_by('-criado_em')
    modulo = (request.GET.get('modulo') or '').strip()
    if modulo:
        qs = qs.filter(modulo=modulo)
    tipo = (request.GET.get('tipo') or '').strip()
    if tipo in dict(TipoRegistoAuditoria.choices):
        qs = qs.filter(tipo=tipo)

    usuario_raw = (request.GET.get('usuario') or '').strip()
    filtro_usuario = ''
    if usuario_raw == '0':
        filtro_usuario = '0'
        qs = qs.filter(usuario_id__isnull=True)
    elif usuario_raw.isdigit():
        uid = int(usuario_raw)
        if User.objects.filter(pk=uid).exists():
            filtro_usuario = str(uid)
            qs = qs.filter(usuario_id=uid)

    user_ids = (
        LogAuditoria.objects.exclude(usuario_id__isnull=True)
        .values_list('usuario_id', flat=True)
        .distinct()
    )
    usuarios_com_logs = User.objects.filter(pk__in=user_ids).order_by(User.USERNAME_FIELD)
    tem_registo_sistema = LogAuditoria.objects.filter(usuario_id__isnull=True).exists()

    paginator = Paginator(qs, 40)
    page_obj = paginator.get_page(request.GET.get('page'))

    rows = []
    for log in page_obj.object_list:
        rows.append(
            {
                'log': log,
                'tipo_badge': _tipo_badge_class(log.tipo),
            }
        )

    return render(
        request,
        'auditoria/index.html',
        {
            'page_obj': page_obj,
            'rows': rows,
            'filtro_modulo': modulo,
            'filtro_tipo': tipo,
            'filtro_usuario': filtro_usuario,
            'tipos': TipoRegistoAuditoria.choices,
            'usuarios_com_logs': usuarios_com_logs,
            'tem_registo_sistema': tem_registo_sistema,
        },
    )
