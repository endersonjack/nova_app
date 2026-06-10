import json
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from usuarios.permissions import requer_modulo

from .forms import VisitanteForm
from .models import Visitante

LISTA_PER_PAGE = 30
LISTA_SORT_FIELDS = {
    'nome': 'nome_completo',
    'telefone': 'telefone',
    'membro': 'membro_acompanha__nome_completo',
    'cadastro': 'criado_em',
}


def _lista_encode_params(*, q='', sort='nome', dir='asc', page=1) -> str:
    parts = []
    if q:
        parts.append(('q', q))
    parts.extend(
        [
            ('sort', sort),
            ('dir', dir),
            ('page', str(page)),
        ]
    )
    return urlencode(parts)


def _lista_next_sort_dir(current_sort: str, current_dir: str, column: str) -> str:
    if current_sort == column:
        return 'desc' if current_dir == 'asc' else 'asc'
    return 'asc'


def _visitante_queryset():
    return Visitante.objects.select_related('membro_acompanha', 'criado_por')


def _get_visitante(pk):
    return get_object_or_404(_visitante_queryset(), pk=pk)


def _hx_redirect(url: str) -> HttpResponse:
    r = HttpResponse()
    r['HX-Redirect'] = url
    r.status_code = 200
    return r


def _hx_response_ok_lista() -> HttpResponse:
    r = HttpResponse(status=204)
    r['HX-Trigger'] = json.dumps(
        {
            'appModalHide': True,
            'visitantesListaRefresh': True,
        }
    )
    return r


@requer_modulo('visitantes', edicao=False)
def index(request):
    return render(request, 'visitantes/index.html')


@requer_modulo('visitantes', edicao=False)
@require_http_methods(['GET'])
def lista_partial(request):
    q = (request.GET.get('q') or '').strip()
    sort = (request.GET.get('sort') or 'nome').strip()
    if sort not in LISTA_SORT_FIELDS:
        sort = 'nome'
    dir_ = (request.GET.get('dir') or 'asc').strip()
    if dir_ not in ('asc', 'desc'):
        dir_ = 'asc'

    qs = _visitante_queryset()
    if q:
        qs = qs.filter(
            Q(nome_completo__icontains=q)
            | Q(nome_conhecido__icontains=q)
            | Q(telefone__icontains=q)
            | Q(membro_acompanha__nome_completo__icontains=q)
        )

    order_field = LISTA_SORT_FIELDS[sort]
    if order_field == 'criado_em':
        order_expr = F('criado_em').desc(nulls_last=True) if dir_ == 'desc' else F('criado_em').asc(nulls_last=True)
        qs = qs.order_by(order_expr, 'pk')
    else:
        prefix = '-' if dir_ == 'desc' else ''
        qs = qs.order_by(f'{prefix}{order_field}', 'pk')

    paginator = Paginator(qs, LISTA_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get('page'))

    list_query_string = _lista_encode_params(
        q=q,
        sort=sort,
        dir=dir_,
        page=page_obj.number,
    )

    def enc(page_num: int) -> str:
        return _lista_encode_params(q=q, sort=sort, dir=dir_, page=page_num)

    ctx = {
        'visitantes': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'sort': sort,
        'dir': dir_,
        'list_query_string': list_query_string,
        'link_sort_nome': _lista_encode_params(
            q=q,
            sort='nome',
            dir=_lista_next_sort_dir(sort, dir_, 'nome'),
            page=1,
        ),
        'link_sort_telefone': _lista_encode_params(
            q=q,
            sort='telefone',
            dir=_lista_next_sort_dir(sort, dir_, 'telefone'),
            page=1,
        ),
        'link_sort_membro': _lista_encode_params(
            q=q,
            sort='membro',
            dir=_lista_next_sort_dir(sort, dir_, 'membro'),
            page=1,
        ),
        'link_sort_cadastro': _lista_encode_params(
            q=q,
            sort='cadastro',
            dir=_lista_next_sort_dir(sort, dir_, 'cadastro'),
            page=1,
        ),
        'link_page_prev': enc(page_obj.previous_page_number())
        if page_obj.has_previous()
        else '',
        'link_page_next': enc(page_obj.next_page_number())
        if page_obj.has_next()
        else '',
    }
    return render(request, 'visitantes/partials/_lista.html', ctx)


@requer_modulo('visitantes', edicao=True)
@require_http_methods(['GET'])
def modal_create(request):
    form = VisitanteForm()
    return render(
        request,
        'visitantes/partials/_modal_form.html',
        {
            'form': form,
            'titulo': _('Novo visitante'),
            'action_url': reverse('visitantes:create'),
        },
    )


@requer_modulo('visitantes', edicao=True)
@require_http_methods(['POST'])
def visitante_create(request):
    form = VisitanteForm(request.POST)
    if form.is_valid():
        visitante = form.save(commit=False)
        visitante.criado_por = request.user
        visitante.save()
        return _hx_redirect(reverse('visitantes:detalhe', args=[visitante.pk]))
    return render(
        request,
        'visitantes/partials/_modal_form.html',
        {
            'form': form,
            'titulo': _('Novo visitante'),
            'action_url': reverse('visitantes:create'),
        },
        status=422,
    )


@requer_modulo('visitantes', edicao=False)
@require_http_methods(['GET'])
def visitante_detalhe(request, pk):
    visitante = _get_visitante(pk)
    return render(request, 'visitantes/visitante_detalhe.html', {'visitante': visitante})


@requer_modulo('visitantes', edicao=True)
@require_http_methods(['GET'])
def modal_edit(request, pk):
    visitante = _get_visitante(pk)
    form = VisitanteForm(instance=visitante)
    return render(
        request,
        'visitantes/partials/_modal_form.html',
        {
            'form': form,
            'visitante': visitante,
            'titulo': _('Editar visitante'),
            'action_url': reverse('visitantes:update', args=[visitante.pk]),
        },
    )


@requer_modulo('visitantes', edicao=True)
@require_http_methods(['POST'])
def visitante_update(request, pk):
    visitante = _get_visitante(pk)
    form = VisitanteForm(request.POST, instance=visitante)
    if form.is_valid():
        form.save()
        response = render(
            request,
            'visitantes/partials/_detalhe_main.html',
            {'visitante': _get_visitante(pk)},
        )
        response['HX-Retarget'] = '#visitante-detalhe-main'
        response['HX-Reswap'] = 'innerHTML'
        response['HX-Trigger-After-Swap'] = json.dumps(
            {
                'appModalHide': True,
                'appToast': {
                    'message': str(_('Alterações salvas.')),
                    'variant': 'success',
                },
            }
        )
        return response
    return render(
        request,
        'visitantes/partials/_modal_form.html',
        {
            'form': form,
            'visitante': visitante,
            'titulo': _('Editar visitante'),
            'action_url': reverse('visitantes:update', args=[visitante.pk]),
        },
        status=422,
    )


@requer_modulo('visitantes', edicao=True)
@require_http_methods(['GET'])
def modal_delete_confirm(request, pk):
    visitante = _get_visitante(pk)
    return render(
        request,
        'visitantes/partials/_modal_delete_confirm.html',
        {'visitante': visitante},
    )


@requer_modulo('visitantes', edicao=True)
@require_http_methods(['POST'])
def visitante_delete(request, pk):
    visitante = _get_visitante(pk)
    visitante.ativo = False
    visitante.save(update_fields=['ativo'])
    messages.success(request, _('Visitante desativado. Deixou de aparecer nas listagens.'))
    return _hx_redirect(reverse('visitantes:index'))
