import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q
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
from .models import EstadoCivil, Membro

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


def _membro_queryset():
    return Membro.objects.select_related('casado_com').prefetch_related('filhos')


def _get_membro(pk):
    return get_object_or_404(_membro_queryset(), pk=pk)


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


def _filhos_labels_from_post(post):
    ids = [int(x) for x in post.getlist('filhos') if str(x).isdigit()]
    if not ids:
        return []
    membros = Membro.objects.filter(pk__in=ids)
    by_id = {m.pk: str(m) for m in membros}
    return [{'id': i, 'label': by_id.get(i, '')} for i in ids if i in by_id]


def _familia_context(membro, post=None):
    ctx = {
        'filhos_iniciais': [],
    }
    if membro.pk:
        ctx['filhos_iniciais'] = [{'id': f.pk, 'label': str(f)} for f in membro.filhos.all()]
    if post is not None:
        fl = _filhos_labels_from_post(post)
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


def _build_secao_ctx(membro, slug, form=None, post=None, with_form=False):
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
        ctx['form'] = cfg['form_class'](instance=membro)
    if slug == 'familia':
        ctx.update(_familia_context(membro, post))
        ctx['familia_conjuge_enabled'] = _familia_conjuge_enabled(
            membro, form=ctx.get('form'), post=post
        )
    return ctx


@login_required
def index(request):
    return render(request, 'membros/index.html')


@login_required
@require_http_methods(['GET'])
def lista_partial(request):
    membros = Membro.objects.select_related('casado_com').order_by('nome_completo')
    return render(
        request,
        'membros/partials/_lista.html',
        {'membros': membros},
    )


@login_required
@require_http_methods(['GET'])
def autocomplete(request):
    q = request.GET.get('q', '').strip()
    exclude = request.GET.get('exclude', '').strip()
    qs = Membro.objects.all().order_by('nome_completo')
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


@login_required
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


@login_required
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


@login_required
@require_http_methods(['GET'])
def membro_detalhe(request, pk):
    membro = _get_membro(pk)
    secao_ativa = 'dados-pessoais'
    cfg = SECAO_CONFIG[secao_ativa]
    ctx = _build_secao_ctx(membro, secao_ativa)
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


@login_required
@require_http_methods(['GET'])
def membro_secao(request, pk, slug):
    if slug not in SECAO_CONFIG:
        raise Http404()
    membro = _get_membro(pk)
    cfg = SECAO_CONFIG[slug]
    ctx = _build_secao_ctx(membro, slug)
    ctx['section_partial'] = cfg['display_template']
    return render(request, 'membros/partials/detalhe/_secao_swap_shell.html', ctx)


@login_required
@require_http_methods(['GET'])
def membro_secao_modal(request, pk, slug):
    if slug not in SECAO_CONFIG:
        raise Http404()
    membro = _get_membro(pk)
    ctx = _build_secao_ctx(membro, slug, with_form=True)
    return render(request, MODAL_SECAO_SHELL, ctx)


@login_required
@require_http_methods(['POST'])
def membro_secao_salvar(request, pk, slug):
    if slug not in SECAO_CONFIG:
        raise Http404()
    membro = _get_membro(pk)
    cfg = SECAO_CONFIG[slug]
    form_class = cfg['form_class']
    form = form_class(
        request.POST,
        request.FILES if slug == 'dados-pessoais' else None,
        instance=membro,
    )
    if form.is_valid():
        form.save()
        membro = _get_membro(pk)
        ctx = _build_secao_ctx(membro, slug)
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
    ctx = _build_secao_ctx(membro, slug, form=form, post=request.POST)
    return render(request, MODAL_SECAO_SHELL, ctx, status=422)


@login_required
@require_http_methods(['GET'])
def modal_delete_confirm(request, pk):
    membro = get_object_or_404(Membro, pk=pk)
    return render(
        request,
        'membros/partials/_modal_delete_confirm.html',
        {'membro': membro},
    )


@login_required
@require_http_methods(['POST'])
def membro_delete(request, pk):
    membro = get_object_or_404(Membro, pk=pk)
    membro.delete()
    messages.success(request, _('Membro excluído com sucesso.'))
    return _hx_redirect(reverse('membros:membros_index'))
