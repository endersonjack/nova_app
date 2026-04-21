import json
from urllib.parse import urlencode

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.utils.translation import gettext_lazy as _lazy
from django.views.decorators.http import require_http_methods

from .forms import (
    MembroBatismoForm,
    MembroDadosPessoaisForm,
    MembroFamiliaForm,
    MembroInformacoesForm,
    MembroLocalidadeForm,
    MembroMinisteriosForm,
    MembroNovoForm,
)
from usuarios.familia import membros_visiveis_queryset
from usuarios.permissions import requer_modulo

from .models import EstadoCivil, Membro

LISTA_PER_PAGE = 30
LISTA_SORT_FIELDS = {
    'nome': 'nome_completo',
    'telefone': 'telefone',
    'nascimento': 'data_nascimento',
    'email': 'email',
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


SECAO_CONFIG = {
    'dados-pessoais': {
        'form_class': MembroDadosPessoaisForm,
        'display_template': 'membros/partials/detalhe/_secao_dados_pessoais_display.html',
        'form_partial': 'membros/partials/detalhe/_secao_dados_pessoais_form.html',
        'titulo_modal': _lazy('Editar dados pessoais'),
    },
    'localidade': {
        'form_class': MembroLocalidadeForm,
        'display_template': 'membros/partials/detalhe/_secao_localidade_display.html',
        'form_partial': 'membros/partials/detalhe/_secao_localidade_form.html',
        'titulo_modal': _lazy('Editar localidade'),
    },
    'familia': {
        'form_class': MembroFamiliaForm,
        'display_template': 'membros/partials/detalhe/_secao_familia_display.html',
        'form_partial': 'membros/partials/detalhe/_secao_familia_form.html',
        'titulo_modal': _lazy('Editar família'),
    },
    'batismo': {
        'form_class': MembroBatismoForm,
        'display_template': 'membros/partials/detalhe/_secao_batismo_display.html',
        'form_partial': 'membros/partials/detalhe/_secao_batismo_form.html',
        'titulo_modal': _lazy('Editar batismo'),
    },
    'informacoes': {
        'form_class': MembroInformacoesForm,
        'display_template': 'membros/partials/detalhe/_secao_informacoes_display.html',
        'form_partial': 'membros/partials/detalhe/_secao_informacoes_form.html',
        'titulo_modal': _lazy('Editar informações'),
    },
    'ministerios': {
        'form_class': MembroMinisteriosForm,
        'display_template': 'membros/partials/detalhe/_secao_ministerios_display.html',
        'form_partial': 'membros/partials/detalhe/_secao_ministerios_form.html',
        'titulo_modal': _lazy('Editar ministérios'),
    },
}

MODAL_SECAO_SHELL = 'membros/partials/detalhe/_modal_secao_editar.html'


def _membro_queryset(request):
    return (
        membros_visiveis_queryset(request.user)
        .select_related(
            'casado_com',
            'pai',
            'mae',
            'locomocao',
            'tamanho_camisa',
        )
        .prefetch_related('filhos')
    )


def _get_membro(request, pk):
    return get_object_or_404(_membro_queryset(request), pk=pk)


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
            'membrosListaRefresh': True,
        }
    )
    return r


def _filhos_labels_from_post(request, post):
    ids = [int(x) for x in post.getlist('filhos') if str(x).isdigit()]
    if not ids:
        return []
    membros = membros_visiveis_queryset(request.user).filter(pk__in=ids)
    by_id = {m.pk: str(m) for m in membros}
    return [{'id': i, 'label': by_id.get(i, '')} for i in ids if i in by_id]


def _familia_context(request, membro, post=None):
    ctx = {
        'filhos_iniciais': [],
    }
    if membro.pk:
        ctx['filhos_iniciais'] = [{'id': f.pk, 'label': str(f)} for f in membro.filhos.all()]
    if post is not None:
        fl = _filhos_labels_from_post(request, post)
        if fl:
            ctx['filhos_iniciais'] = fl
    return ctx


def _familia_conjuge_enabled(membro, form=None, post=None) -> bool:
    if post is not None:
        est = (post.get('estado_civil') or '').strip()
    elif form is not None and form.is_bound:
        est = (form.data.get('estado_civil') or '').strip()
    else:
        est = (membro.estado_civil or '').strip()
    return est == EstadoCivil.CASADO.value


def _build_secao_ctx(request, membro, slug, form=None, post=None, with_form=False):
    cfg = SECAO_CONFIG[slug]
    ctx = {
        'membro': membro,
        'secao_slug': slug,
        'titulo_modal': cfg['titulo_modal'],
        'form_partial': cfg['form_partial'],
        'action_url': reverse('membros:secao_salvar', args=[membro.pk, slug]),
    }
    if form is not None:
        ctx['form'] = form
    elif with_form:
        form_cls = cfg['form_class']
        if form_cls is MembroFamiliaForm:
            ctx['form'] = form_cls(
                instance=membro,
                membros_scope_qs=membros_visiveis_queryset(request.user),
            )
        else:
            ctx['form'] = form_cls(instance=membro)
    if slug == 'familia':
        ctx.update(_familia_context(request, membro, post))
        ctx['familia_conjuge_enabled'] = _familia_conjuge_enabled(
            membro, form=ctx.get('form'), post=post
        )
    return ctx


@requer_modulo('membros', edicao=False)
def index(request):
    return render(request, 'membros/index.html')


@requer_modulo('membros', edicao=False)
@require_http_methods(['GET'])
def mapa_membros(request):
    qs = (
        membros_visiveis_queryset(request.user)
        .filter(latitude__isnull=False, longitude__isnull=False)
        .only('pk', 'nome_completo', 'nome_conhecido', 'foto', 'latitude', 'longitude')
        .order_by('nome_completo')
    )
    markers = []
    for m in qs:
        exibir = ((m.nome_conhecido or '').strip() or (m.nome_completo or '').strip() or '—')
        markers.append(
            {
                'lat': float(m.latitude),
                'lng': float(m.longitude),
                'nome': exibir,
                'foto': m.foto.url if m.foto else '',
                'url': reverse('membros:detalhe', args=[m.pk]),
            }
        )
    return render(
        request,
        'membros/mapa_membros.html',
        {'markers_payload': markers},
    )


@requer_modulo('membros', edicao=False)
@require_http_methods(['GET'])
def lista_partial(request):
    q = (request.GET.get('q') or '').strip()
    sort = (request.GET.get('sort') or 'nome').strip()
    if sort not in LISTA_SORT_FIELDS:
        sort = 'nome'
    dir_ = (request.GET.get('dir') or 'asc').strip()
    if dir_ not in ('asc', 'desc'):
        dir_ = 'asc'

    qs = membros_visiveis_queryset(request.user).select_related('casado_com')
    if q:
        qs = qs.filter(
            Q(nome_completo__icontains=q) | Q(nome_conhecido__icontains=q),
        )

    order_field = LISTA_SORT_FIELDS[sort]
    if order_field == 'data_nascimento':
        if dir_ == 'desc':
            qs = qs.order_by(F('data_nascimento').desc(nulls_last=True))
        else:
            qs = qs.order_by(F('data_nascimento').asc(nulls_last=True))
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

    link_sort_nome = _lista_encode_params(
        q=q,
        sort='nome',
        dir=_lista_next_sort_dir(sort, dir_, 'nome'),
        page=1,
    )
    link_sort_telefone = _lista_encode_params(
        q=q,
        sort='telefone',
        dir=_lista_next_sort_dir(sort, dir_, 'telefone'),
        page=1,
    )
    link_sort_nascimento = _lista_encode_params(
        q=q,
        sort='nascimento',
        dir=_lista_next_sort_dir(sort, dir_, 'nascimento'),
        page=1,
    )
    link_sort_email = _lista_encode_params(
        q=q,
        sort='email',
        dir=_lista_next_sort_dir(sort, dir_, 'email'),
        page=1,
    )

    ctx = {
        'membros': page_obj.object_list,
        'page_obj': page_obj,
        'q': q,
        'sort': sort,
        'dir': dir_,
        'list_query_string': list_query_string,
        'link_sort_nome': link_sort_nome,
        'link_sort_telefone': link_sort_telefone,
        'link_sort_nascimento': link_sort_nascimento,
        'link_sort_email': link_sort_email,
        'link_page_prev': enc(page_obj.previous_page_number())
        if page_obj.has_previous()
        else '',
        'link_page_next': enc(page_obj.next_page_number())
        if page_obj.has_next()
        else '',
    }
    return render(request, 'membros/partials/_lista.html', ctx)


@requer_modulo('membros', edicao=False)
@require_http_methods(['GET'])
def autocomplete(request):
    q = request.GET.get('q', '').strip()
    exclude = request.GET.get('exclude', '').strip()
    qs = membros_visiveis_queryset(request.user).order_by('nome_completo')
    if exclude.isdigit():
        qs = qs.exclude(pk=int(exclude))
    sexo_conjuge = request.GET.get('sexo_conjuge', '').strip().upper()
    if sexo_conjuge in ('M', 'F'):
        qs = qs.filter(sexo=sexo_conjuge)
    if len(q) < 2:
        membros = Membro.objects.none()
    else:
        membros = qs.filter(
            Q(nome_completo__icontains=q)
            | Q(nome_conhecido__icontains=q)
            | Q(email__icontains=q)
        )[:20]
    return render(
        request,
        'membros/partials/_autocomplete_list.html',
        {'membros': membros, 'q': q},
    )


@requer_modulo('membros', edicao=True)
@require_http_methods(['GET'])
def modal_create(request):
    form = MembroNovoForm()
    return render(
        request,
        'membros/partials/_modal_novo.html',
        {
            'form': form,
            'titulo': 'Novo membro',
            'action_url': reverse('membros:create'),
        },
    )


@requer_modulo('membros', edicao=True)
@require_http_methods(['POST'])
def membro_create(request):
    form = MembroNovoForm(request.POST)
    if form.is_valid():
        membro = form.save()
        return _hx_redirect(reverse('membros:detalhe', args=[membro.pk]))
    return render(
        request,
        'membros/partials/_modal_novo.html',
        {
            'form': form,
            'titulo': 'Novo membro',
            'action_url': reverse('membros:create'),
        },
        status=422,
    )


@requer_modulo('membros', edicao=False)
@require_http_methods(['GET'])
def membro_detalhe(request, pk):
    membro = _get_membro(request, pk)
    secao_ativa = 'dados-pessoais'
    cfg = SECAO_CONFIG[secao_ativa]
    ctx = _build_secao_ctx(request, membro, secao_ativa)
    return render(
        request,
        'membros/membro_detalhe.html',
        {
            'membro': membro,
            'secao_ativa': secao_ativa,
            'secao_include': cfg['display_template'],
            **ctx,
        },
    )


@requer_modulo('membros', edicao=False)
@require_http_methods(['GET'])
def membro_secao(request, pk, slug):
    if slug not in SECAO_CONFIG:
        raise Http404()
    membro = _get_membro(request, pk)
    cfg = SECAO_CONFIG[slug]
    ctx = _build_secao_ctx(request, membro, slug)
    ctx['section_partial'] = cfg['display_template']
    return render(request, 'membros/partials/detalhe/_secao_swap_shell.html', ctx)


@requer_modulo('membros', edicao=True)
@require_http_methods(['GET'])
def membro_secao_modal(request, pk, slug):
    if slug not in SECAO_CONFIG:
        raise Http404()
    membro = _get_membro(request, pk)
    ctx = _build_secao_ctx(request, membro, slug, with_form=True)
    return render(request, MODAL_SECAO_SHELL, ctx)


@requer_modulo('membros', edicao=True)
@require_http_methods(['POST'])
def membro_secao_salvar(request, pk, slug):
    if slug not in SECAO_CONFIG:
        raise Http404()
    membro = _get_membro(request, pk)
    cfg = SECAO_CONFIG[slug]
    form_class = cfg['form_class']
    form_kw = {}
    if form_class is MembroFamiliaForm:
        form_kw['membros_scope_qs'] = membros_visiveis_queryset(request.user)
    form = form_class(
        request.POST,
        request.FILES if slug == 'dados-pessoais' else None,
        instance=membro,
        **form_kw,
    )
    if form.is_valid():
        form.save()
        membro = _get_membro(request, pk)
        ctx = _build_secao_ctx(request, membro, slug)
        ctx['section_partial'] = cfg['display_template']
        response = render(
            request,
            'membros/partials/detalhe/_secao_swap_shell.html',
            ctx,
        )
        # Resposta do POST veio do formulário no modal (hx-target #app-modal-content);
        # redireciona o swap para a área principal e envia o mesmo HTML do GET da seção (+ OOB do topbar).
        response['HX-Retarget'] = '#membro-detalhe-main'
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
    ctx = _build_secao_ctx(request, membro, slug, form=form, post=request.POST)
    return render(request, MODAL_SECAO_SHELL, ctx, status=422)


@requer_modulo('membros', edicao=True)
@require_http_methods(['GET'])
def modal_delete_confirm(request, pk):
    membro = get_object_or_404(_membro_queryset(request), pk=pk)
    return render(
        request,
        'membros/partials/_modal_delete_confirm.html',
        {'membro': membro},
    )


@requer_modulo('membros', edicao=True)
@require_http_methods(['POST'])
def membro_delete(request, pk):
    membro = get_object_or_404(_membro_queryset(request), pk=pk)
    membro.ativo = False
    membro.save(update_fields=['ativo'])
    messages.success(request, _('Membro inativado. Deixou de aparecer nas listagens e pesquisas.'))
    return _hx_redirect(reverse('membros:membros_index'))
