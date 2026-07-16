"""Geração de PDF do relatório de competência (tesouraria)."""

from __future__ import annotations

from decimal import Decimal
from io import BytesIO
from xml.sax.saxutils import escape

from django.utils.translation import gettext as _

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from .money_format import format_brl
from .models import (
    CompetenciaTesouraria,
    ContaFinanceira,
    LancamentoFinanceiro,
    TipoCategoriaFinanceira,
    TipoContaFinanceira,
)


def _moeda(d: Decimal) -> str:
    return f'R$ {format_brl(d)}'


def _filtro_movimento(
    apenas_entradas: bool, apenas_saidas: bool
) -> str:
    if apenas_entradas and not apenas_saidas:
        return 'e'
    if apenas_saidas and not apenas_entradas:
        return 's'
    return 'all'


def _p(text: str) -> str:
    return escape(str(text), {'"': '&quot;', "'": '&apos;'})


def _trunc(text: str, max_len: int) -> str:
    s = (text or '').strip()
    if len(s) <= max_len:
        return s
    return s[: max_len - 1] + '…'


def _totais_de_lancamentos(lancs: list[LancamentoFinanceiro]) -> tuple[Decimal, Decimal]:
    ent = Decimal('0')
    sai = Decimal('0')
    for l in lancs:
        if l.tipo == TipoCategoriaFinanceira.ENTRADA:
            ent += l.valor
        else:
            sai += l.valor
    return ent, sai


def _participante(l: LancamentoFinanceiro) -> str:
    if l.membro_id:
        return l.membro.nome_completo
    if l.visitante_id:
        return l.visitante.nome_completo
    return '—'


def _lancamentos_de_tipo(
    lancamentos_por_conta: dict[int, list[LancamentoFinanceiro]],
    tipo: str,
) -> list[LancamentoFinanceiro]:
    out: list[LancamentoFinanceiro] = []
    for lancamentos in lancamentos_por_conta.values():
        out.extend(l for l in lancamentos if l.tipo == tipo)
    return sorted(out, key=lambda l: (l.data, l.id or 0))


def _append_tabela_lancamentos_por_data(
    story: list,
    *,
    titulo: str,
    lancamentos: list[LancamentoFinanceiro],
    total_label: str,
    h2_style,
    body,
) -> None:
    story.append(Paragraph(_p(titulo), h2_style))
    story.append(Spacer(1, 0.15 * cm))
    hdr = [
        _('Data'),
        _('Conta/Caixa'),
        _('Categoria'),
        _('Descrição'),
        _('Participante'),
        _('Evento'),
        _('Valor'),
    ]
    data = [[_p(h) for h in hdr]]
    total = Decimal('0')
    for l in lancamentos:
        total += l.valor
        ev = l.evento.nome if l.evento_id else '—'
        data.append(
            [
                _p(l.data.strftime('%d/%m/%Y')),
                _p(_trunc(l.conta.nome, 38)),
                _p(_trunc(l.categoria.nome, 42)),
                _p(_trunc(l.descricao, 70)),
                _p(_trunc(_participante(l), 42)),
                _p(_trunc(ev, 38)),
                _p(_moeda(l.valor)),
            ]
        )
    if len(data) == 1:
        data.append(
            [_p(_('Nenhum lançamento encontrado nesta competência.'))]
            + ([''] * (len(hdr) - 1))
        )
    total_row = len(data)
    data.append(
        [
            _p(''),
            _p(''),
            _p(''),
            _p(''),
            _p(''),
            _p(total_label),
            _p(_moeda(total)),
        ]
    )
    tw = [
        2.0 * cm,
        3.6 * cm,
        3.5 * cm,
        6.2 * cm,
        4.2 * cm,
        3.6 * cm,
        2.5 * cm,
    ]
    t = Table(data, colWidths=tw, repeatRows=1)
    style_cmds = [
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7.5),
        ('GRID', (0, 0), (-1, -1), 0.2, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROWBACKGROUNDS', (0, 1), (-1, total_row - 1), [colors.white, colors.HexColor('#f8f9fa')]),
        ('FONTNAME', (0, total_row), (-1, total_row), 'Helvetica-Bold'),
        ('BACKGROUND', (0, total_row), (-1, total_row), colors.HexColor('#e7f1ff')),
    ]
    t.setStyle(TableStyle(style_cmds))
    story.append(t)
    story.append(Spacer(1, 0.25 * cm))


def build_competencia_relatorio_pdf(
    *,
    competencia: CompetenciaTesouraria,
    contas: list[ContaFinanceira],
    lancamentos_por_conta: dict[int, list[LancamentoFinanceiro]],
    resumo_contas: list[dict],
    competencia_prev: CompetenciaTesouraria | None,
    competencia_anterior_acumulado: CompetenciaTesouraria | None,
    saldo_trazido_anterior: Decimal | None,
    competencia_saldo_geral_final: Decimal,
    competencia_total_entradas: Decimal,
    competencia_total_saidas: Decimal,
    totais_anteriores: dict[str, Decimal],
    totais_acumulados: dict[str, Decimal],
    resumo_eventos: list[dict],
    resumo_eventos_totais: dict | None,
    inc_contas: bool,
    inc_resumo_eventos: bool,
    inc_resumo_geral: bool,
    apenas_entradas: bool,
    apenas_saidas: bool,
) -> bytes:
    buf = BytesIO()
    page_size = landscape(A4)
    doc = SimpleDocTemplate(
        buf,
        pagesize=page_size,
        leftMargin=1.4 * cm,
        rightMargin=1.4 * cm,
        topMargin=1.1 * cm,
        bottomMargin=1.1 * cm,
        title=str(_('Relatório da competência')),
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        name='TituloComp',
        parent=styles['Heading1'],
        fontSize=14,
        spaceAfter=6,
    )
    h2_style = ParagraphStyle(
        name='SecComp',
        parent=styles['Heading2'],
        fontSize=11,
        spaceBefore=10,
        spaceAfter=6,
    )
    h_conta_style = ParagraphStyle(
        name='TituloContaPdf',
        parent=styles['Heading2'],
        fontSize=10,
        spaceBefore=10,
        spaceAfter=3,
    )
    body = styles['Normal']
    body.fontSize = 9

    story: list = []
    titulo = str(competencia)
    story.append(Paragraph(_p(titulo), title_style))
    periodo = _('Período: %(mes)02d/%(ano)s') % {
        'mes': competencia.mes,
        'ano': competencia.ano,
    }
    story.append(Paragraph(_p(periodo), body))
    story.append(Spacer(1, 0.3 * cm))

    flt = _filtro_movimento(apenas_entradas, apenas_saidas)

    if inc_contas:
        entradas = _lancamentos_de_tipo(
            lancamentos_por_conta,
            TipoCategoriaFinanceira.ENTRADA,
        )
        saidas = _lancamentos_de_tipo(
            lancamentos_por_conta,
            TipoCategoriaFinanceira.SAIDA,
        )
        if flt in ('all', 'e'):
            _append_tabela_lancamentos_por_data(
                story,
                titulo=_('Entradas por data (contas e caixas juntas)'),
                lancamentos=entradas,
                total_label=_('Total Entradas'),
                h2_style=h2_style,
                body=body,
            )
        if flt in ('all', 's'):
            _append_tabela_lancamentos_por_data(
                story,
                titulo=_('Saídas por data (contas e caixas juntas)'),
                lancamentos=saidas,
                total_label=_('Total Saídas'),
                h2_style=h2_style,
                body=body,
            )

    if inc_resumo_eventos:
        story.append(Paragraph(_p(_('Resumo por eventos')), h2_style))
        story.append(
            Paragraph(
                _p(
                    _(
                        'Totais desta competência para lançamentos com evento associado.'
                    )
                ),
                body,
            )
        )
        story.append(Spacer(1, 0.2 * cm))
        if flt == 'e':
            hdr = [_('Evento'), _('Total entradas (R$)')]
        elif flt == 's':
            hdr = [_('Evento'), _('Total saídas (R$)')]
        else:
            hdr = [
                _('Evento'),
                _('Entradas (R$)'),
                _('Saídas (R$)'),
                _('Saldo (R$)'),
            ]
        data = [[_p(h) for h in hdr]]
        for item in resumo_eventos:
            e, s = item['entradas'], item['saidas']
            if flt == 'e':
                data.append([_p(item['nome']), _p(_moeda(e))])
            elif flt == 's':
                data.append([_p(item['nome']), _p(_moeda(s))])
            else:
                data.append(
                    [
                        _p(item['nome']),
                        _p(_moeda(e)),
                        _p(_moeda(s)),
                        _p(_moeda(e - s)),
                    ]
                )
        if resumo_eventos_totais and resumo_eventos:
            te = resumo_eventos_totais['entradas']
            ts = resumo_eventos_totais['saidas']
            if flt == 'e':
                data.append([_p(_('Total')), _p(_moeda(te))])
            elif flt == 's':
                data.append([_p(_('Total')), _p(_moeda(ts))])
            else:
                data.append(
                    [
                        _p(_('Total')),
                        _p(_moeda(te)),
                        _p(_moeda(ts)),
                        _p(_moeda(te - ts)),
                    ]
                )
        if len(data) == 1:
            data.append(
                [_p(_('Nenhum lançamento com evento nesta competência.'))]
                + ([''] * (len(hdr) - 1))
            )
        if flt in ('e', 's'):
            tw = [18 * cm, 5.5 * cm]
        else:
            tw = [10 * cm, 4.5 * cm, 4.5 * cm, 4.5 * cm]
        t = Table(data, colWidths=tw)
        t.setStyle(
            TableStyle(
                [
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
                ]
            )
        )
        story.append(t)

    if inc_resumo_geral:
        story.append(Paragraph(_p(_('Resumos da Competência')), h2_style))
        story.append(Spacer(1, 0.2 * cm))
        hdr = [
            _('Nome'),
            _('Tipo'),
            _('Total Entradas (R$)'),
            _('Total Saídas (R$)'),
            _('Saldo (R$)'),
        ]
        data = [[_p(h) for h in hdr]]
        for row in resumo_contas:
            conta = row['conta']
            e, s = row['entradas'], row['saidas']
            tipo_lbl = (
                _('Banco')
                if conta.tipo == TipoContaFinanceira.BANCO
                else _('Caixa')
            )
            data.append(
                [
                    _p(conta.nome),
                    _p(tipo_lbl),
                    _p(_moeda(e)),
                    _p(_moeda(s)),
                    _p(_moeda(e - s)),
                ]
            )
        first_footer_row = len(data)
        data.append(
            [
                _p(
                    _('Saldo da Competência (%(mes)02d/%(ano)s)')
                    % {'mes': competencia.mes, 'ano': competencia.ano}
                ),
                _p(''),
                _p(_moeda(competencia_total_entradas)),
                _p(_moeda(competencia_total_saidas)),
                _p(_moeda(competencia_total_entradas - competencia_total_saidas)),
            ]
        )
        if competencia_anterior_acumulado:
            anterior_label = _('Saldo anterior (competência %(mes)02d/%(ano)s)') % {
                'mes': competencia_anterior_acumulado.mes,
                'ano': competencia_anterior_acumulado.ano,
            }
        else:
            anterior_label = _('Saldo anterior (sem competência anterior)')
        data.append(
            [
                _p(anterior_label),
                _p(''),
                _p(_moeda(totais_anteriores['entradas'])),
                _p(_moeda(totais_anteriores['saidas'])),
                _p(_moeda(totais_anteriores['saldo'])),
            ]
        )
        data.append(
            [
                _p(_('Saldo Geral Acumulado')),
                _p(''),
                _p(_moeda(totais_acumulados['entradas'])),
                _p(_moeda(totais_acumulados['saidas'])),
                _p(_moeda(totais_acumulados['saldo'])),
            ]
        )
        tw = [7 * cm, 3 * cm, 4.5 * cm, 4.5 * cm, 5 * cm]
        t = Table(data, colWidths=tw)
        style_cmds = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]
        last_body = first_footer_row - 1
        if last_body >= 1:
            style_cmds.append(
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, last_body),
                    [colors.white, colors.HexColor('#f8f9fa')],
                )
            )
        for r in range(first_footer_row, len(data)):
            style_cmds.append(('FONTNAME', (0, r), (-1, r), 'Helvetica-Bold'))
            style_cmds.append(('BACKGROUND', (0, r), (-1, r), colors.HexColor('#e7f1ff')))
        style_cmds.append(('BACKGROUND', (0, len(data) - 1), (-1, len(data) - 1), colors.HexColor('#d8e9ff')))
        t.setStyle(TableStyle(style_cmds))
        story.append(t)

    doc.build(story)
    return buf.getvalue()
