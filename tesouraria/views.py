import json
import re
import unicodedata
from calendar import monthrange
from collections import defaultdict
from datetime import date
from decimal import Decimal
from urllib.parse import urlparse

from django import forms
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import DecimalField, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseBadRequest, QueryDict
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.utils.translation import gettext as _
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from membros.models import Membro
from visitantes.models import Visitante

from usuarios.familia import membros_visiveis_queryset
from usuarios.models import PapelMembro
from usuarios.permissions import get_perfil, requer_modulo, usuario_pode_modulo

from .forms import (
    CategoriaFinanceiraForm,
    CompetenciaTesourariaForm,
    ContaFinanceiraForm,
    EventoFinanceiroForm,
    LancamentoEntradaForm,
    LancamentoSaidaForm,
)
from .models import (
    CategoriaFinanceira,
    CompetenciaTesouraria,
    ContaFinanceira,
    EventoFinanceiro,
    LancamentoFinanceiro,
    TipoCategoriaFinanceira,
    TipoContaFinanceira,
)
from .pdf_relatorio_competencia import build_competencia_relatorio_pdf


MESES_PT_ABREV = (
    '',
    'Jan',
    'Fev',
    'Mar',
    'Abr',
    'Mai',
    'Jun',
    'Jul',
    'Ago',
    'Set',
    'Out',
    'Nov',
    'Dez',
)

MESES_PT = (
    '',
    'Janeiro',
    'Fevereiro',
    'Março',
    'Abril',
    'Maio',
    'Junho',
    'Julho',
    'Agosto',
    'Setembro',
    'Outubro',
    'Novembro',
    'Dezembro',
)


def _normalizar_busca(texto) -> str:
    base = unicodedata.normalize('NFKD', str(texto or ''))
    sem_acento = ''.join(ch for ch in base if not unicodedata.combining(ch))
    return sem_acento.casefold()


def _somente_digitos(texto) -> str:
    return re.sub(r'\D', '', str(texto or ''))


def _filtrar_sem_acento(queryset, termo: str, campos: tuple[str, ...], limite=10):
    termo_normalizado = _normalizar_busca(termo)
    termo_digitos = _somente_digitos(termo)
    encontrados = []
    for obj in queryset:
        valores = [str(getattr(obj, campo, '') or '') for campo in campos]
        texto_normalizado = _normalizar_busca(' '.join(valores))
        texto_digitos = _somente_digitos(' '.join(valores))
        if termo_normalizado in texto_normalizado or (
            termo_digitos and termo_digitos in texto_digitos
        ):
            encontrados.append(obj)
            if len(encontrados) >= limite:
                break
    return encontrados


def _agregados_por_conta_na_competencia(
    competencia,
) -> dict[int, dict[str, Decimal]]:
    """Por conta: totais de entradas, saídas e saldo (E − S) nesta competência."""
    out: dict[int, dict[str, Decimal]] = {}
    rows = (
        LancamentoFinanceiro.objects.filter(competencia=competencia)
        .values('conta_id')
        .annotate(
            entradas=Coalesce(
                Sum('valor', filter=Q(tipo=TipoCategoriaFinanceira.ENTRADA)),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
            saidas=Coalesce(
                Sum('valor', filter=Q(tipo=TipoCategoriaFinanceira.SAIDA)),
                Value(Decimal('0')),
                output_field=DecimalField(max_digits=12, decimal_places=2),
            ),
        )
    )
    for row in rows:
        e, s = row['entradas'], row['saidas']
        out[row['conta_id']] = {
            'entradas': e,
            'saidas': s,
            'saldo': e - s,
        }
    return out


def _resumo_eventos_na_competencia(competencia: CompetenciaTesouraria) -> list[dict]:
    """Totais de entradas/saídas nesta competência agrupados por evento (só lançamentos com evento)."""
    dec = DecimalField(max_digits=12, decimal_places=2)
    rows = (
        LancamentoFinanceiro.objects.filter(competencia=competencia)
        .exclude(evento_id=None)
        .values('evento_id', 'evento__nome')
        .annotate(
            entradas=Coalesce(
                Sum('valor', filter=Q(tipo=TipoCategoriaFinanceira.ENTRADA)),
                Value(Decimal('0')),
                output_field=dec,
            ),
            saidas=Coalesce(
                Sum('valor', filter=Q(tipo=TipoCategoriaFinanceira.SAIDA)),
                Value(Decimal('0')),
                output_field=dec,
            ),
        )
        .order_by('evento__nome')
    )
    out: list[dict] = []
    for r in rows:
        e, s = r['entradas'], r['saidas']
        out.append(
            {
                'nome': r['evento__nome'],
                'entradas': e,
                'saidas': s,
                'saldo': e - s,
            }
        )
    return out


def _competencia_anterior(
    competencia: CompetenciaTesouraria,
) -> CompetenciaTesouraria | None:
    if competencia.mes > 1:
        return CompetenciaTesouraria.objects.filter(
            mes=competencia.mes - 1,
            ano=competencia.ano,
        ).first()
    return CompetenciaTesouraria.objects.filter(
        mes=12,
        ano=competencia.ano - 1,
    ).first()


def _saldo_geral_movimentos_competencia(competencia: CompetenciaTesouraria) -> Decimal:
    ag = _agregados_por_conta_na_competencia(competencia)
    te = sum(d['entradas'] for d in ag.values())
    ts = sum(d['saidas'] for d in ag.values())
    return te - ts


def _fechamento_apos_competencia(competencia: CompetenciaTesouraria) -> Decimal:
    """
    Saldo ao fim desta competência: movimento do mês, mais cadeia de competências
    anteriores quando `competencia_continua` está ativo em cada elo.
    """
    net = _saldo_geral_movimentos_competencia(competencia)
    prev = _competencia_anterior(competencia)
    if prev is None or not competencia.competencia_continua:
        return net
    return _fechamento_apos_competencia(prev) + net


def usuario_pode_excluir_competencia_tesouraria(user) -> bool:
    """Apenas superusuário ou utilizador com papel Admin no perfil."""
    if not user.is_authenticated:
        return False
    if user.is_superuser:
        return True
    perfil = get_perfil(user)
    return bool(perfil and perfil.papel == PapelMembro.ADMIN)


def _hx_redirect(url: str) -> HttpResponse:
    r = HttpResponse(status=200)
    r['HX-Redirect'] = url
    return r


def _hx_close_modal_e_atualizar_lista() -> HttpResponse:
    r = HttpResponse(status=204)
    r['HX-Trigger'] = json.dumps(
        {
            'appModalHide': True,
            'tesourariaCompetenciasRefresh': True,
        }
    )
    return r


def _hx_close_modal_e_atualizar_categorias() -> HttpResponse:
    r = HttpResponse(status=204)
    r['HX-Trigger'] = json.dumps(
        {
            'appModalHide': True,
            'tesourariaCategoriasRefresh': True,
        }
    )
    return r


def _hx_close_modal_e_atualizar_eventos() -> HttpResponse:
    r = HttpResponse(status=204)
    r['HX-Trigger'] = json.dumps(
        {
            'appModalHide': True,
            'tesourariaEventosRefresh': True,
        }
    )
    return r


def _hx_close_modal_e_atualizar_lancamentos() -> HttpResponse:
    r = HttpResponse(status=204)
    r['HX-Trigger'] = json.dumps(
        {
            'appModalHide': True,
            'tesourariaLancamentosRefresh': True,
        }
    )
    return r


def _request_path_from_hx(request) -> str:
    url = request.headers.get('HX-Current-URL') or ''
    return urlparse(url).path or ''


def _salvando_competencia_na_pagina_detalhe(request, competencia_pk: int) -> bool:
    detalhe = reverse('tesouraria:competencia_detalhe', args=[competencia_pk]).rstrip('/')
    path = _request_path_from_hx(request).rstrip('/')
    return path == detalhe


def _membro_logado(user):
    perfil = getattr(user, 'perfil', None)
    if not perfil or not perfil.membro_id:
        return None
    return perfil.membro


def _conjuge_entradas_disponivel(membro):
    if not membro or not membro.pk or not membro.casado_com_id:
        return None
    return membro.casado_com


def _incluir_conjuge_param(request, membro) -> bool:
    return bool(_conjuge_entradas_disponivel(membro) and request.GET.get('conjuge') == '1')


def _minhas_entradas_base_qs(membro, *, incluir_conjuge=False):
    if not membro:
        return LancamentoFinanceiro.objects.none()
    membros_ids = [membro.pk]
    conjuge = _conjuge_entradas_disponivel(membro)
    if incluir_conjuge and conjuge:
        membros_ids.append(conjuge.pk)
    return LancamentoFinanceiro.objects.filter(
        tipo=TipoCategoriaFinanceira.ENTRADA,
        membro_id__in=membros_ids,
    ).select_related('competencia', 'conta', 'categoria', 'evento', 'membro')


def _month_add(year: int, month: int, delta: int) -> tuple[int, int]:
    total = year * 12 + (month - 1) + delta
    return total // 12, (total % 12) + 1


def _month_bounds(year: int, month: int) -> tuple[date, date]:
    return date(year, month, 1), date(year, month, monthrange(year, month)[1])


def _minhas_entradas_chart_payload(qs_base, hoje: date) -> dict:
    months = [_month_add(hoje.year, hoje.month, i) for i in range(-12, 0)]
    valores: dict[tuple[int, int], Decimal] = {}
    for year, month in months:
        inicio, fim = _month_bounds(year, month)
        valores[(year, month)] = (
            qs_base.filter(data__gte=inicio, data__lte=fim).aggregate(
                total=Coalesce(
                    Sum('valor'),
                    Value(Decimal('0')),
                    output_field=DecimalField(max_digits=12, decimal_places=2),
                )
            )['total']
            or Decimal('0')
        )

    return {
        'labels': [f'{MESES_PT_ABREV[month]}/{str(year)[2:]}' for year, month in months],
        'values': [float(valores[(year, month)]) for year, month in months],
        'total_periodo': sum(valores.values(), Decimal('0')),
    }


def _minhas_entradas_table_context(request, qs_base, hoje: date) -> dict:
    default_year, default_month = _month_add(hoje.year, hoje.month, -1)
    selected_year = default_year
    raw_year = (request.GET.get('ano') or '').strip()
    if raw_year.isdigit():
        selected_year = int(raw_year)

    selected_month = default_month
    raw_month = (request.GET.get('mes') or '').strip()
    if 'mes' in request.GET and raw_month == '':
        selected_month = None
    if raw_month.isdigit() and 1 <= int(raw_month) <= 12:
        selected_month = int(raw_month)

    years = [d.year for d in qs_base.dates('data', 'year', order='DESC')]
    if selected_year not in years:
        years.insert(0, selected_year)
    if hoje.year not in years:
        years.insert(0, hoje.year)
    years = sorted(set(years), reverse=True)

    qs_table = qs_base.filter(data__year=selected_year)
    if selected_month:
        qs_table = qs_table.filter(data__month=selected_month)

    monthly_sections = []
    meses = [selected_month] if selected_month else list(range(1, 13))
    for month in meses:
        lancamentos = list(
            qs_table.filter(data__month=month).order_by('data', 'id')
        )
        total = sum((l.valor for l in lancamentos), Decimal('0'))
        monthly_sections.append(
            {
                'month': month,
                'label': MESES_PT[month],
                'lancamentos': lancamentos,
                'total': total,
            }
        )

    return {
        'selected_month': selected_month,
        'selected_year': selected_year,
        'months': [(i, MESES_PT[i]) for i in range(1, 13)],
        'years': years,
        'monthly_sections': monthly_sections,
        'total_filtrado': sum((s['total'] for s in monthly_sections), Decimal('0')),
    }


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['GET'])
def index(request):
    return render(request, 'tesouraria/index.html')


@login_required
@require_http_methods(['GET'])
def minhas_entradas(request):
    membro = _membro_logado(request.user)
    hoje = date.today()
    incluir_conjuge = _incluir_conjuge_param(request, membro)
    conjuge = _conjuge_entradas_disponivel(membro)
    qs_base = _minhas_entradas_base_qs(membro, incluir_conjuge=incluir_conjuge)
    chart = _minhas_entradas_chart_payload(qs_base, hoje)
    table_ctx = _minhas_entradas_table_context(request, qs_base, hoje)
    return render(
        request,
        'tesouraria/minhas_entradas.html',
        {
            'membro': membro,
            'conjuge_entradas': conjuge,
            'incluir_conjuge': incluir_conjuge,
            'chart': chart,
            **table_ctx,
        },
    )


@login_required
@require_http_methods(['GET'])
def minhas_entradas_tabela(request):
    membro = _membro_logado(request.user)
    hoje = date.today()
    incluir_conjuge = _incluir_conjuge_param(request, membro)
    conjuge = _conjuge_entradas_disponivel(membro)
    qs_base = _minhas_entradas_base_qs(membro, incluir_conjuge=incluir_conjuge)
    ctx = _minhas_entradas_table_context(request, qs_base, hoje)
    ctx.update(
        {
            'conjuge_entradas': conjuge,
            'incluir_conjuge': incluir_conjuge,
            'chart': _minhas_entradas_chart_payload(qs_base, hoje),
            'chart_oob': True,
        }
    )
    return render(
        request,
        'tesouraria/partials/_minhas_entradas_tabela.html',
        ctx,
    )


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['GET'])
def categorias_index(request):
    return render(request, 'tesouraria/categorias_index.html')


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['GET'])
def eventos_index(request):
    return render(request, 'tesouraria/eventos_index.html')


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['GET'])
def categorias_lista_partial(request):
    categorias = CategoriaFinanceira.objects.all()
    pode_editar = usuario_pode_modulo(request.user, 'tesouraria', edicao=True)
    return render(
        request,
        'tesouraria/partials/_categorias_lista.html',
        {
            'categorias': categorias,
            'pode_editar': pode_editar,
        },
    )


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['GET'])
def eventos_lista_partial(request):
    eventos = EventoFinanceiro.objects.all()
    pode_editar = usuario_pode_modulo(request.user, 'tesouraria', edicao=True)
    return render(
        request,
        'tesouraria/partials/_eventos_lista.html',
        {
            'eventos': eventos,
            'pode_editar': pode_editar,
        },
    )


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['GET'])
def competencias_lista_partial(request):
    competencias = CompetenciaTesouraria.objects.all()
    pode_editar = usuario_pode_modulo(request.user, 'tesouraria', edicao=True)
    return render(
        request,
        'tesouraria/partials/_competencias_lista.html',
        {
            'competencias': competencias,
            'pode_editar': pode_editar,
        },
    )


@requer_modulo('tesouraria', edicao=False)
@never_cache
@require_http_methods(['GET'])
def competencia_detalhe(request, pk):
    competencia = get_object_or_404(CompetenciaTesouraria, pk=pk)
    contas = ContaFinanceira.objects.all()
    agregados = _agregados_por_conta_na_competencia(competencia)
    saldo_por_conta = {cid: d['saldo'] for cid, d in agregados.items()}
    zero = {
        'entradas': Decimal('0'),
        'saidas': Decimal('0'),
        'saldo': Decimal('0'),
    }
    resumo_contas = []
    for conta in ContaFinanceira.objects.all().order_by('tipo', 'nome'):
        d = agregados.get(conta.pk, zero)
        resumo_contas.append({'conta': conta, **d})
    total_entradas = sum(d['entradas'] for d in agregados.values())
    total_saidas = sum(d['saidas'] for d in agregados.values())
    competencia_prev = _competencia_anterior(competencia)
    if competencia.competencia_continua:
        saldo_trazido_anterior = (
            _fechamento_apos_competencia(competencia_prev)
            if competencia_prev
            else Decimal('0')
        )
    else:
        saldo_trazido_anterior = None
    competencia_saldo_geral_final = _fechamento_apos_competencia(competencia)
    resumo_eventos = _resumo_eventos_na_competencia(competencia)
    resumo_eventos_totais = (
        {
            'entradas': sum(r['entradas'] for r in resumo_eventos),
            'saidas': sum(r['saidas'] for r in resumo_eventos),
        }
        if resumo_eventos
        else None
    )
    if resumo_eventos_totais is not None:
        resumo_eventos_totais['saldo'] = (
            resumo_eventos_totais['entradas'] - resumo_eventos_totais['saidas']
        )
    pode_editar = usuario_pode_modulo(request.user, 'tesouraria', edicao=True)
    pode_excluir_competencia = usuario_pode_excluir_competencia_tesouraria(request.user)
    return render(
        request,
        'tesouraria/competencia_detalhe.html',
        {
            'competencia': competencia,
            'contas': contas,
            'saldo_por_conta': saldo_por_conta,
            'resumo_contas': resumo_contas,
            'competencia_total_entradas': total_entradas,
            'competencia_total_saidas': total_saidas,
            'competencia_saldo_geral': total_entradas - total_saidas,
            'competencia_prev': competencia_prev,
            'saldo_trazido_anterior': saldo_trazido_anterior,
            'competencia_saldo_geral_final': competencia_saldo_geral_final,
            'resumo_eventos': resumo_eventos,
            'resumo_eventos_totais': resumo_eventos_totais,
            'pode_editar': pode_editar,
            'pode_excluir_competencia': pode_excluir_competencia,
        },
    )


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['POST'])
def competencia_relatorio_pdf(request, pk):
    competencia = get_object_or_404(CompetenciaTesouraria, pk=pk)
    inc_contas = request.POST.get('inc_contas') == 'on'
    inc_resumo_eventos = request.POST.get('inc_resumo_eventos') == 'on'
    inc_resumo_geral = request.POST.get('inc_resumo_geral') == 'on'
    apenas_entradas = request.POST.get('apenas_entradas') == 'on'
    apenas_saidas = request.POST.get('apenas_saidas') == 'on'
    if not (inc_contas or inc_resumo_eventos or inc_resumo_geral):
        return HttpResponseBadRequest(
            _('Marque pelo menos uma secção do relatório.'),
            content_type='text/plain; charset=utf-8',
        )
    agregados = _agregados_por_conta_na_competencia(competencia)
    zero = {
        'entradas': Decimal('0'),
        'saidas': Decimal('0'),
        'saldo': Decimal('0'),
    }
    resumo_contas = []
    contas = list(ContaFinanceira.objects.all().order_by('tipo', 'nome'))
    for conta in contas:
        d = agregados.get(conta.pk, zero)
        resumo_contas.append({'conta': conta, **d})
    total_entradas = sum(d['entradas'] for d in agregados.values())
    total_saidas = sum(d['saidas'] for d in agregados.values())
    competencia_prev = _competencia_anterior(competencia)
    if competencia.competencia_continua:
        saldo_trazido_anterior = (
            _fechamento_apos_competencia(competencia_prev)
            if competencia_prev
            else Decimal('0')
        )
    else:
        saldo_trazido_anterior = None
    competencia_saldo_geral_final = _fechamento_apos_competencia(competencia)
    resumo_eventos = _resumo_eventos_na_competencia(competencia)
    resumo_eventos_totais = (
        {
            'entradas': sum(r['entradas'] for r in resumo_eventos),
            'saidas': sum(r['saidas'] for r in resumo_eventos),
        }
        if resumo_eventos
        else None
    )
    if resumo_eventos_totais is not None:
        resumo_eventos_totais['saldo'] = (
            resumo_eventos_totais['entradas'] - resumo_eventos_totais['saidas']
        )
    lancamentos_por_conta: dict[int, list] = defaultdict(list)
    for lan in (
        LancamentoFinanceiro.objects.filter(competencia=competencia)
        .select_related('categoria', 'membro', 'visitante', 'evento')
        .order_by('data', 'id')
    ):
        lancamentos_por_conta[lan.conta_id].append(lan)
    pdf_bytes = build_competencia_relatorio_pdf(
        competencia=competencia,
        contas=contas,
        lancamentos_por_conta=dict(lancamentos_por_conta),
        resumo_contas=resumo_contas,
        competencia_prev=competencia_prev,
        saldo_trazido_anterior=saldo_trazido_anterior,
        competencia_saldo_geral_final=competencia_saldo_geral_final,
        competencia_total_entradas=total_entradas,
        competencia_total_saidas=total_saidas,
        resumo_eventos=resumo_eventos,
        resumo_eventos_totais=resumo_eventos_totais,
        inc_contas=inc_contas,
        inc_resumo_eventos=inc_resumo_eventos,
        inc_resumo_geral=inc_resumo_geral,
        apenas_entradas=apenas_entradas,
        apenas_saidas=apenas_saidas,
    )
    fn = f'relatorio-tesouraria-{competencia.mes:02d}-{competencia.ano}.pdf'
    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{fn}"'
    return response


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def competencia_definir_continua(request, pk):
    competencia = get_object_or_404(CompetenciaTesouraria, pk=pk)
    competencia.competencia_continua = (
        request.POST.get('competencia_continua') == 'on'
    )
    competencia.save(update_fields=['competencia_continua'])
    return _hx_redirect(
        reverse('tesouraria:competencia_detalhe', args=[competencia.pk])
    )


def _ctx_modal_competencia(form, *, titulo, action_url, competencia, request):
    return {
        'form': form,
        'titulo': titulo,
        'action_url': action_url,
        'competencia': competencia,
        'pode_excluir_competencia': usuario_pode_excluir_competencia_tesouraria(
            request.user
        ),
    }


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def competencia_modal_criar(request):
    form = CompetenciaTesourariaForm()
    return render(
        request,
        'tesouraria/partials/_modal_competencia_form.html',
        _ctx_modal_competencia(
            form,
            titulo='Adicionar competência',
            action_url=reverse('tesouraria:competencia_criar'),
            competencia=None,
            request=request,
        ),
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def competencia_criar(request):
    form = CompetenciaTesourariaForm(request.POST)
    if form.is_valid():
        form.save()
        return _hx_close_modal_e_atualizar_lista()
    return render(
        request,
        'tesouraria/partials/_modal_competencia_form.html',
        _ctx_modal_competencia(
            form,
            titulo='Adicionar competência',
            action_url=reverse('tesouraria:competencia_criar'),
            competencia=None,
            request=request,
        ),
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def competencia_modal_editar(request, pk):
    competencia = get_object_or_404(CompetenciaTesouraria, pk=pk)
    form = CompetenciaTesourariaForm(instance=competencia)
    return render(
        request,
        'tesouraria/partials/_modal_competencia_form.html',
        _ctx_modal_competencia(
            form,
            titulo='Editar competência',
            action_url=reverse('tesouraria:competencia_salvar', args=[competencia.pk]),
            competencia=competencia,
            request=request,
        ),
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def competencia_salvar(request, pk):
    competencia = get_object_or_404(CompetenciaTesouraria, pk=pk)
    form = CompetenciaTesourariaForm(request.POST, instance=competencia)
    if form.is_valid():
        form.save()
        if _salvando_competencia_na_pagina_detalhe(request, competencia.pk):
            return _hx_redirect(
                reverse('tesouraria:competencia_detalhe', args=[competencia.pk])
            )
        return _hx_close_modal_e_atualizar_lista()
    return render(
        request,
        'tesouraria/partials/_modal_competencia_form.html',
        _ctx_modal_competencia(
            form,
            titulo='Editar competência',
            action_url=reverse('tesouraria:competencia_salvar', args=[competencia.pk]),
            competencia=competencia,
            request=request,
        ),
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def competencia_modal_excluir(request, pk):
    if not usuario_pode_excluir_competencia_tesouraria(request.user):
        raise PermissionDenied
    competencia = get_object_or_404(CompetenciaTesouraria, pk=pk)
    return render(
        request,
        'tesouraria/partials/_modal_competencia_excluir.html',
        {'competencia': competencia},
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def competencia_excluir(request, pk):
    if not usuario_pode_excluir_competencia_tesouraria(request.user):
        raise PermissionDenied
    competencia = get_object_or_404(CompetenciaTesouraria, pk=pk)
    competencia.delete()
    return _hx_redirect(reverse('tesouraria:index'))


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def categoria_modal_criar(request):
    form = CategoriaFinanceiraForm(initial={'ativa': True})
    return render(
        request,
        'tesouraria/partials/_modal_categoria_form.html',
        {
            'form': form,
            'titulo': _('Adicionar categoria'),
            'action_url': reverse('tesouraria:categoria_criar'),
            'categoria': None,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def categoria_criar(request):
    form = CategoriaFinanceiraForm(request.POST)
    if form.is_valid():
        categoria = form.save()
        if (
            request.POST.get('retorno_lancamento') == '1'
            and request.session.get(SESSION_KEY_RASCUNHO_LANCAMENTO)
        ):
            return _render_lancamento_modal_from_stash(
                request,
                nova_categoria_pk=categoria.pk,
            )
        return _hx_close_modal_e_atualizar_categorias()
    ctx = {
        'form': form,
        'titulo': _('Adicionar categoria'),
        'action_url': reverse('tesouraria:categoria_criar'),
        'categoria': None,
    }
    if request.POST.get('retorno_lancamento') == '1':
        stash = request.session.get(SESSION_KEY_RASCUNHO_LANCAMENTO)
        if stash:
            form.fields['tipo'].widget = forms.HiddenInput()
            ctx['titulo'] = _('Nova categoria')
            ctx['modal_categoria_desde_lancamento'] = True
            ctx['url_voltar_lancamento'] = reverse(
                'tesouraria:lancamento_restaurar_rascunho_modal',
                args=[stash['competencia_pk'], stash['conta_pk']],
            )
    return render(
        request,
        'tesouraria/partials/_modal_categoria_form.html',
        ctx,
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def categoria_modal_editar(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    form = CategoriaFinanceiraForm(instance=categoria)
    return render(
        request,
        'tesouraria/partials/_modal_categoria_form.html',
        {
            'form': form,
            'titulo': _('Editar categoria'),
            'action_url': reverse('tesouraria:categoria_salvar', args=[categoria.pk]),
            'categoria': categoria,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def categoria_salvar(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    form = CategoriaFinanceiraForm(request.POST, instance=categoria)
    if form.is_valid():
        form.save()
        return _hx_close_modal_e_atualizar_categorias()
    return render(
        request,
        'tesouraria/partials/_modal_categoria_form.html',
        {
            'form': form,
            'titulo': _('Editar categoria'),
            'action_url': reverse('tesouraria:categoria_salvar', args=[categoria.pk]),
            'categoria': categoria,
        },
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def categoria_modal_excluir(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    return render(
        request,
        'tesouraria/partials/_modal_categoria_excluir.html',
        {'categoria': categoria},
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def categoria_excluir(request, pk):
    categoria = get_object_or_404(CategoriaFinanceira, pk=pk)
    categoria.delete()
    return _hx_close_modal_e_atualizar_categorias()


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def evento_modal_criar(request):
    form = EventoFinanceiroForm(initial={'ativa': True})
    return render(
        request,
        'tesouraria/partials/_modal_evento_form.html',
        {
            'form': form,
            'titulo': _('Adicionar evento'),
            'action_url': reverse('tesouraria:evento_criar'),
            'evento': None,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def evento_criar(request):
    form = EventoFinanceiroForm(request.POST)
    if form.is_valid():
        form.save()
        return _hx_close_modal_e_atualizar_eventos()
    return render(
        request,
        'tesouraria/partials/_modal_evento_form.html',
        {
            'form': form,
            'titulo': _('Adicionar evento'),
            'action_url': reverse('tesouraria:evento_criar'),
            'evento': None,
        },
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def evento_modal_editar(request, pk):
    evento = get_object_or_404(EventoFinanceiro, pk=pk)
    form = EventoFinanceiroForm(instance=evento)
    return render(
        request,
        'tesouraria/partials/_modal_evento_form.html',
        {
            'form': form,
            'titulo': _('Editar evento'),
            'action_url': reverse('tesouraria:evento_salvar', args=[evento.pk]),
            'evento': evento,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def evento_salvar(request, pk):
    evento = get_object_or_404(EventoFinanceiro, pk=pk)
    form = EventoFinanceiroForm(request.POST, instance=evento)
    if form.is_valid():
        form.save()
        return _hx_close_modal_e_atualizar_eventos()
    return render(
        request,
        'tesouraria/partials/_modal_evento_form.html',
        {
            'form': form,
            'titulo': _('Editar evento'),
            'action_url': reverse('tesouraria:evento_salvar', args=[evento.pk]),
            'evento': evento,
        },
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def evento_modal_excluir(request, pk):
    evento = get_object_or_404(EventoFinanceiro, pk=pk)
    return render(
        request,
        'tesouraria/partials/_modal_evento_excluir.html',
        {'evento': evento},
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def evento_excluir(request, pk):
    evento = get_object_or_404(EventoFinanceiro, pk=pk)
    evento.delete()
    return _hx_close_modal_e_atualizar_eventos()


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def conta_modal_criar(request, competencia_pk):
    get_object_or_404(CompetenciaTesouraria, pk=competencia_pk)
    tipo = request.GET.get('tipo', '').strip().lower()
    valid = {c.value for c in TipoContaFinanceira}
    if tipo not in valid:
        return HttpResponse(_('Tipo inválido.'), status=400)
    form = ContaFinanceiraForm(initial={'tipo': tipo, 'ativa': True})
    if tipo == TipoContaFinanceira.CAIXA:
        titulo = _('Novo caixa')
    else:
        titulo = _('Nova conta')
    return render(
        request,
        'tesouraria/partials/_modal_conta_form.html',
        {
            'form': form,
            'titulo': titulo,
            'action_url': reverse(
                'tesouraria:conta_criar', args=[competencia_pk]
            ),
            'competencia_pk': competencia_pk,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def conta_criar(request, competencia_pk):
    get_object_or_404(CompetenciaTesouraria, pk=competencia_pk)
    form = ContaFinanceiraForm(request.POST)
    if form.is_valid():
        form.save()
        return _hx_redirect(
            reverse('tesouraria:competencia_detalhe', args=[competencia_pk])
        )
    tipo = (form.data.get('tipo') or '').strip().lower()
    if tipo == TipoContaFinanceira.CAIXA:
        titulo = _('Novo caixa')
    else:
        titulo = _('Nova conta')
    return render(
        request,
        'tesouraria/partials/_modal_conta_form.html',
        {
            'form': form,
            'titulo': titulo,
            'action_url': reverse(
                'tesouraria:conta_criar', args=[competencia_pk]
            ),
            'competencia_pk': competencia_pk,
        },
        status=422,
    )


def _get_competencia_e_conta(competencia_pk, conta_pk):
    competencia = get_object_or_404(CompetenciaTesouraria, pk=competencia_pk)
    conta = get_object_or_404(ContaFinanceira, pk=conta_pk)
    return competencia, conta


def _lancamento_na_conta(competencia_pk, conta_pk, pk):
    return get_object_or_404(
        LancamentoFinanceiro.objects.select_related(
            'categoria',
            'membro',
            'visitante',
            'evento',
        ),
        pk=pk,
        competencia_id=competencia_pk,
        conta_id=conta_pk,
    )


SESSION_KEY_RASCUNHO_LANCAMENTO = 'tesouraria_rascunho_lancamento'


def _post_para_stash(post):
    out = {}
    for key in post.keys():
        if key == 'csrfmiddlewaretoken':
            continue
        vals = post.getlist(key)
        if not vals:
            continue
        out[key] = vals[0] if len(vals) == 1 else vals
    return out


def _stash_post_as_querydict(stash_post: dict) -> QueryDict:
    q = QueryDict(mutable=True)
    for key, value in stash_post.items():
        if isinstance(value, (list, tuple)):
            for item in value:
                q.appendlist(key, str(item))
        elif value is not None and value != '':
            q[key] = str(value)
    return q


def _participante_label_de_data(data: dict, lan=None):
    raw_visitante = data.get('visitante', '')
    if raw_visitante is not None and str(raw_visitante).strip():
        vid = str(raw_visitante).strip()
        if vid.isdigit():
            v = Visitante.todos.filter(pk=int(vid)).first()
            if v:
                return v.nome_completo
    raw = data.get('membro', '')
    if raw is not None and str(raw).strip():
        mid = str(raw).strip()
        if mid.isdigit():
            m = Membro.objects.filter(pk=int(mid)).first()
            if m:
                return m.nome_completo
    if lan:
        if lan.membro_id:
            return lan.membro.nome_completo
        if lan.visitante_id:
            return lan.visitante.nome_completo
    return ''


def _render_lancamento_modal_from_stash(request, *, nova_categoria_pk=None):
    stash = request.session.get(SESSION_KEY_RASCUNHO_LANCAMENTO)
    if not stash:
        return HttpResponse(_('Rascunho não encontrado.'), status=400)
    raw = dict(stash['post'])
    if nova_categoria_pk is not None:
        raw['categoria'] = str(nova_categoria_pk)
    data = _stash_post_as_querydict(raw)
    competencia_pk = stash['competencia_pk']
    conta_pk = stash['conta_pk']
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    tipo_fluxo = stash['tipo_fluxo']
    pk_edit = stash.get('lancamento_pk')

    if tipo_fluxo == 'entrada':
        if pk_edit:
            lan = _lancamento_na_conta(competencia_pk, conta_pk, pk_edit)
            form = LancamentoEntradaForm(data, instance=lan, competencia=competencia)
            titulo = _('Editar entrada')
            action_url = reverse(
                'tesouraria:lancamento_salvar',
                args=[competencia_pk, conta_pk, pk_edit],
            )
            membro_busca_inicial = _participante_label_de_data(data, lan)
        else:
            form = LancamentoEntradaForm(data, competencia=competencia)
            titulo = _('Nova entrada')
            action_url = reverse(
                'tesouraria:lancamento_criar_entrada',
                args=[competencia_pk, conta_pk],
            )
            membro_busca_inicial = _participante_label_de_data(data, None)
        return render(
            request,
            'tesouraria/partials/_modal_lancamento_entrada.html',
            {
                'form': form,
                'titulo': titulo,
                'action_url': action_url,
                'competencia': competencia,
                'conta': conta,
                'membro_busca_inicial': membro_busca_inicial,
                'lancamento_pk': pk_edit,
            },
        )

    if pk_edit:
        lan = _lancamento_na_conta(competencia_pk, conta_pk, pk_edit)
        form = LancamentoSaidaForm(data, instance=lan, competencia=competencia)
        titulo = _('Editar saída')
        action_url = reverse(
            'tesouraria:lancamento_salvar',
            args=[competencia_pk, conta_pk, pk_edit],
        )
    else:
        form = LancamentoSaidaForm(data, competencia=competencia)
        titulo = _('Nova saída')
        action_url = reverse(
            'tesouraria:lancamento_criar_saida',
            args=[competencia_pk, conta_pk],
        )
    return render(
        request,
        'tesouraria/partials/_modal_lancamento_saida.html',
        {
            'form': form,
            'titulo': titulo,
            'action_url': action_url,
            'competencia': competencia,
            'conta': conta,
            'lancamento_pk': pk_edit,
        },
    )


@requer_modulo('tesouraria', edicao=False)
@never_cache
@require_http_methods(['GET'])
def conta_detalhe(request, competencia_pk, conta_pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    pode_editar = usuario_pode_modulo(request.user, 'tesouraria', edicao=True)
    return render(
        request,
        'tesouraria/conta_detalhe.html',
        {
            'competencia': competencia,
            'conta': conta,
            'pode_editar': pode_editar,
        },
    )


@requer_modulo('tesouraria', edicao=False)
@never_cache
@require_http_methods(['GET'])
def lancamentos_lista_partial(request, competencia_pk, conta_pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    base = LancamentoFinanceiro.objects.filter(
        competencia_id=competencia.pk,
        conta_id=conta.pk,
    ).select_related('categoria', 'membro', 'visitante', 'evento')
    lancamentos_entrada = list(
        base.filter(
            tipo=TipoCategoriaFinanceira.ENTRADA,
        ).order_by('data', 'id')
    )
    lancamentos_saida = list(
        base.filter(
            tipo=TipoCategoriaFinanceira.SAIDA,
        ).order_by('data', 'id')
    )
    total_entrada_valor = sum(
        (lan.valor for lan in lancamentos_entrada),
        Decimal('0'),
    )
    total_saida_valor = sum(
        (lan.valor for lan in lancamentos_saida),
        Decimal('0'),
    )
    pode_editar = usuario_pode_modulo(request.user, 'tesouraria', edicao=True)
    return render(
        request,
        'tesouraria/partials/_lancamentos_lista.html',
        {
            'competencia': competencia,
            'conta': conta,
            'lancamentos_entrada': lancamentos_entrada,
            'lancamentos_saida': lancamentos_saida,
            'total_entrada_quantidade': len(lancamentos_entrada),
            'total_entrada_valor': total_entrada_valor,
            'total_saida_quantidade': len(lancamentos_saida),
            'total_saida_valor': total_saida_valor,
            'pode_editar': pode_editar,
        },
    )


@requer_modulo('tesouraria', edicao=False)
@require_http_methods(['GET'])
def membro_autocomplete_lancamento(request):
    q = request.GET.get('tesouraria_membro_q', '').strip()
    if len(q) < 2:
        membros = Membro.objects.none()
        visitantes = Visitante.objects.none()
    else:
        base = membros_visiveis_queryset(request.user).filter(ativo=True)
        membros = _filtrar_sem_acento(
            base.order_by('nome_completo'),
            q,
            ('nome_completo', 'nome_conhecido', 'cpf'),
            limite=10,
        )
        visitantes = _filtrar_sem_acento(
            Visitante.objects.filter(ativo=True).order_by('nome_completo'),
            q,
            ('nome_completo', 'nome_conhecido', 'telefone'),
            limite=10,
        )
    return render(
        request,
        'tesouraria/partials/_participante_autocomplete_list.html',
        {'membros': membros, 'visitantes': visitantes, 'q': q},
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def lancamento_preservar_rascunho_abrir_categoria(request, competencia_pk, conta_pk):
    _get_competencia_e_conta(competencia_pk, conta_pk)
    tipo_fluxo = request.POST.get('tipo_fluxo')
    if tipo_fluxo not in ('entrada', 'saida'):
        return HttpResponse(_('Fluxo inválido.'), status=400)
    lp = request.POST.get('stash_lancamento_pk')
    lancamento_pk = int(lp) if lp and str(lp).isdigit() else None
    request.session[SESSION_KEY_RASCUNHO_LANCAMENTO] = {
        'tipo_fluxo': tipo_fluxo,
        'competencia_pk': competencia_pk,
        'conta_pk': conta_pk,
        'lancamento_pk': lancamento_pk,
        'post': _post_para_stash(request.POST),
    }
    tipo_cat = (
        TipoCategoriaFinanceira.ENTRADA
        if tipo_fluxo == 'entrada'
        else TipoCategoriaFinanceira.SAIDA
    )
    form = CategoriaFinanceiraForm(initial={'tipo': tipo_cat, 'ativa': True})
    form.fields['tipo'].widget = forms.HiddenInput()
    stash = request.session[SESSION_KEY_RASCUNHO_LANCAMENTO]
    return render(
        request,
        'tesouraria/partials/_modal_categoria_form.html',
        {
            'form': form,
            'titulo': _('Nova categoria'),
            'action_url': reverse('tesouraria:categoria_criar'),
            'categoria': None,
            'modal_categoria_desde_lancamento': True,
            'url_voltar_lancamento': reverse(
                'tesouraria:lancamento_restaurar_rascunho_modal',
                args=[stash['competencia_pk'], stash['conta_pk']],
            ),
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def lancamento_restaurar_rascunho_modal(request, competencia_pk, conta_pk):
    stash = request.session.get(SESSION_KEY_RASCUNHO_LANCAMENTO)
    if not stash:
        return HttpResponse(_('Rascunho não encontrado.'), status=400)
    if (
        int(stash['competencia_pk']) != competencia_pk
        or int(stash['conta_pk']) != conta_pk
    ):
        return HttpResponse(status=400)
    return _render_lancamento_modal_from_stash(request)


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def lancamento_modal_entrada(request, competencia_pk, conta_pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    form = LancamentoEntradaForm(competencia=competencia)
    return render(
        request,
        'tesouraria/partials/_modal_lancamento_entrada.html',
        {
            'form': form,
            'titulo': _('Nova entrada'),
            'action_url': reverse(
                'tesouraria:lancamento_criar_entrada',
                args=[competencia_pk, conta_pk],
            ),
            'competencia': competencia,
            'conta': conta,
            'lancamento_pk': None,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def lancamento_criar_entrada(request, competencia_pk, conta_pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    form = LancamentoEntradaForm(request.POST, competencia=competencia)
    sl = request.POST.get('stash_lancamento_pk')
    lancamento_pk_ctx = int(sl) if sl and str(sl).isdigit() else None
    if form.is_valid():
        request.session.pop(SESSION_KEY_RASCUNHO_LANCAMENTO, None)
        lan = form.save(commit=False)
        lan.competencia = competencia
        lan.conta = conta
        lan.tipo = TipoCategoriaFinanceira.ENTRADA
        lan.save()
        return _hx_close_modal_e_atualizar_lancamentos()
    return render(
        request,
        'tesouraria/partials/_modal_lancamento_entrada.html',
        {
            'form': form,
            'titulo': _('Nova entrada'),
            'action_url': reverse(
                'tesouraria:lancamento_criar_entrada',
                args=[competencia_pk, conta_pk],
            ),
            'competencia': competencia,
            'conta': conta,
            'membro_busca_inicial': _participante_label_de_data(
                request.POST.dict(),
                None,
            ),
            'lancamento_pk': lancamento_pk_ctx,
        },
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def lancamento_modal_saida(request, competencia_pk, conta_pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    form = LancamentoSaidaForm(competencia=competencia)
    return render(
        request,
        'tesouraria/partials/_modal_lancamento_saida.html',
        {
            'form': form,
            'titulo': _('Nova saída'),
            'action_url': reverse(
                'tesouraria:lancamento_criar_saida',
                args=[competencia_pk, conta_pk],
            ),
            'competencia': competencia,
            'conta': conta,
            'lancamento_pk': None,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def lancamento_criar_saida(request, competencia_pk, conta_pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    form = LancamentoSaidaForm(request.POST, competencia=competencia)
    sl = request.POST.get('stash_lancamento_pk')
    lancamento_pk_ctx = int(sl) if sl and str(sl).isdigit() else None
    if form.is_valid():
        request.session.pop(SESSION_KEY_RASCUNHO_LANCAMENTO, None)
        lan = form.save(commit=False)
        lan.competencia = competencia
        lan.conta = conta
        lan.tipo = TipoCategoriaFinanceira.SAIDA
        lan.membro = None
        lan.visitante = None
        lan.save()
        return _hx_close_modal_e_atualizar_lancamentos()
    return render(
        request,
        'tesouraria/partials/_modal_lancamento_saida.html',
        {
            'form': form,
            'titulo': _('Nova saída'),
            'action_url': reverse(
                'tesouraria:lancamento_criar_saida',
                args=[competencia_pk, conta_pk],
            ),
            'competencia': competencia,
            'conta': conta,
            'lancamento_pk': lancamento_pk_ctx,
        },
        status=422,
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def lancamento_modal_editar(request, competencia_pk, conta_pk, pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    lan = _lancamento_na_conta(competencia_pk, conta_pk, pk)
    action_url = reverse(
        'tesouraria:lancamento_salvar',
        args=[competencia_pk, conta_pk, pk],
    )
    membro_busca_inicial = ''
    if lan.tipo == TipoCategoriaFinanceira.ENTRADA:
        form = LancamentoEntradaForm(instance=lan, competencia=competencia)
        if lan.membro_id:
            membro_busca_inicial = lan.membro.nome_completo
        elif lan.visitante_id:
            membro_busca_inicial = lan.visitante.nome_completo
        return render(
            request,
            'tesouraria/partials/_modal_lancamento_entrada.html',
            {
                'form': form,
                'titulo': _('Editar entrada'),
                'action_url': action_url,
                'competencia': competencia,
                'conta': conta,
                'membro_busca_inicial': membro_busca_inicial,
                'lancamento_pk': lan.pk,
            },
        )
    form = LancamentoSaidaForm(instance=lan, competencia=competencia)
    return render(
        request,
        'tesouraria/partials/_modal_lancamento_saida.html',
        {
            'form': form,
            'titulo': _('Editar saída'),
            'action_url': action_url,
            'competencia': competencia,
            'conta': conta,
            'lancamento_pk': lan.pk,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def lancamento_salvar(request, competencia_pk, conta_pk, pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    lan = _lancamento_na_conta(competencia_pk, conta_pk, pk)
    action_url = reverse(
        'tesouraria:lancamento_salvar',
        args=[competencia_pk, conta_pk, pk],
    )
    if lan.tipo == TipoCategoriaFinanceira.ENTRADA:
        form = LancamentoEntradaForm(request.POST, instance=lan, competencia=competencia)
        membro_busca_inicial = _membro_label_para_busca(request.POST, lan)
        ctx = {
            'form': form,
            'titulo': _('Editar entrada'),
            'action_url': action_url,
            'competencia': competencia,
            'conta': conta,
            'membro_busca_inicial': membro_busca_inicial,
            'lancamento_pk': pk,
        }
        template = 'tesouraria/partials/_modal_lancamento_entrada.html'
    else:
        form = LancamentoSaidaForm(request.POST, instance=lan, competencia=competencia)
        ctx = {
            'form': form,
            'titulo': _('Editar saída'),
            'action_url': action_url,
            'competencia': competencia,
            'conta': conta,
            'lancamento_pk': pk,
        }
        template = 'tesouraria/partials/_modal_lancamento_saida.html'
    if form.is_valid():
        request.session.pop(SESSION_KEY_RASCUNHO_LANCAMENTO, None)
        obj = form.save(commit=False)
        obj.competencia = competencia
        obj.conta = conta
        obj.tipo = lan.tipo
        if lan.tipo == TipoCategoriaFinanceira.SAIDA:
            obj.membro = None
            obj.visitante = None
        obj.save()
        return _hx_close_modal_e_atualizar_lancamentos()
    return render(request, template, ctx, status=422)


def _membro_label_para_busca(post, lan):
    return _participante_label_de_data(post.dict(), lan)


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['GET'])
def lancamento_modal_excluir(request, competencia_pk, conta_pk, pk):
    competencia, conta = _get_competencia_e_conta(competencia_pk, conta_pk)
    lan = _lancamento_na_conta(competencia_pk, conta_pk, pk)
    return render(
        request,
        'tesouraria/partials/_modal_lancamento_excluir.html',
        {
            'competencia': competencia,
            'conta': conta,
            'lan': lan,
        },
    )


@requer_modulo('tesouraria', edicao=True)
@require_http_methods(['POST'])
def lancamento_excluir(request, competencia_pk, conta_pk, pk):
    _get_competencia_e_conta(competencia_pk, conta_pk)
    lan = _lancamento_na_conta(competencia_pk, conta_pk, pk)
    lan.delete()
    return _hx_close_modal_e_atualizar_lancamentos()
