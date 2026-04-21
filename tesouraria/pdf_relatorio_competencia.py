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


def _filter_lancamentos_por_tipo(
    lancs: list[LancamentoFinanceiro], flt: str
) -> list[LancamentoFinanceiro]:
    if flt == 'e':
        return [l for l in lancs if l.tipo == TipoCategoriaFinanceira.ENTRADA]
    if flt == 's':
        return [l for l in lancs if l.tipo == TipoCategoriaFinanceira.SAIDA]
    return list(lancs)


def _totais_de_lancamentos(lancs: list[LancamentoFinanceiro]) -> tuple[Decimal, Decimal]:
    ent = Decimal('0')
    sai = Decimal('0')
    for l in lancs:
        if l.tipo == TipoCategoriaFinanceira.ENTRADA:
            ent += l.valor
        else:
            sai += l.valor
    return ent, sai


def build_competencia_relatorio_pdf(
    *,
    competencia: CompetenciaTesouraria,
    contas: list[ContaFinanceira],
    lancamentos_por_conta: dict[int, list[LancamentoFinanceiro]],
    resumo_contas: list[dict],
    competencia_prev: CompetenciaTesouraria | None,
    saldo_trazido_anterior: Decimal | None,
    competencia_saldo_geral_final: Decimal,
    competencia_total_entradas: Decimal,
    competencia_total_saidas: Decimal,
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
        story.append(Paragraph(_p(_('Caixas e contas')), h2_style))
        story.append(
            Paragraph(
                _p(
                    _(
                        'Cada conta ou caixa com o detalhe de todos os lançamentos '
                        'desta competência (respeitando os filtros «só entradas» ou '
                        '«só saídas», quando ativos).'
                    )
                ),
                body,
            )
        )
        story.append(Spacer(1, 0.25 * cm))
        if not contas:
            story.append(
                Paragraph(_p(_('Nenhuma conta ou caixa cadastrada.')), body)
            )
        hdr_lanc = [
            _('Data'),
            _('Tipo'),
            _('Categoria'),
            _('Descrição'),
            _('Valor'),
            _('Documento'),
            _('Evento'),
        ]
        # Larguras para A4 paisagem (~26,7 cm úteis); evita sobreposição de células.
        tw_lanc = [
            2.2 * cm,
            1.5 * cm,
            3.5 * cm,
            9.0 * cm,
            2.3 * cm,
            2.4 * cm,
            4.5 * cm,
        ]
        for conta in contas:
            story.append(Paragraph(_p(conta.nome), h_conta_style))
            tipo_lbl = (
                _('Banco')
                if conta.tipo == TipoContaFinanceira.BANCO
                else _('Caixa')
            )
            ativa_lbl = _('Ativa') if conta.ativa else _('Inativa')
            linha_conta = f'{tipo_lbl} · {ativa_lbl}'
            story.append(Paragraph(_p(linha_conta), body))
            if (conta.descricao or '').strip():
                story.append(
                    Paragraph(
                        _p(_('Descrição da conta: %(txt)s') % {'txt': _trunc(conta.descricao, 200)}),
                        body,
                    )
                )
            raw_lancs = lancamentos_por_conta.get(conta.pk, [])
            vis_lancs = _filter_lancamentos_por_tipo(raw_lancs, flt)
            if not raw_lancs:
                story.append(
                    Paragraph(
                        _p(_('Nenhum lançamento nesta competência.')),
                        body,
                    )
                )
                story.append(Spacer(1, 0.15 * cm))
                continue
            if not vis_lancs:
                story.append(
                    Paragraph(
                        _p(
                            _(
                                'Nenhum lançamento corresponde ao filtro escolhido '
                                '(só entradas / só saídas).'
                            )
                        ),
                        body,
                    )
                )
                story.append(Spacer(1, 0.15 * cm))
                continue
            data = [[_p(h) for h in hdr_lanc]]
            for l in vis_lancs:
                ev = l.evento.nome if l.evento_id else '—'
                num_doc = (l.numero_documento or '').strip() or '—'
                data.append(
                    [
                        _p(l.data.strftime('%d/%m/%Y')),
                        _p(str(l.get_tipo_display())),
                        _p(_trunc(l.categoria.nome, 56)),
                        _p(_trunc(l.descricao, 110)),
                        _p(_moeda(l.valor)),
                        _p(_trunc(num_doc, 22)),
                        _p(_trunc(ev, 42)),
                    ]
                )
            te, ts = _totais_de_lancamentos(vis_lancs)
            n0 = len(data)
            if flt == 'all':
                data.append(
                    [
                        _p(''),
                        _p(''),
                        _p(''),
                        _p(_('Total entradas')),
                        _p(_moeda(te)),
                        _p(''),
                        _p(''),
                    ]
                )
                data.append(
                    [
                        _p(''),
                        _p(''),
                        _p(''),
                        _p(_('Total saídas')),
                        _p(_moeda(ts)),
                        _p(''),
                        _p(''),
                    ]
                )
                data.append(
                    [
                        _p(''),
                        _p(''),
                        _p(''),
                        _p(_('Saldo (entradas − saídas)')),
                        _p(_moeda(te - ts)),
                        _p(''),
                        _p(''),
                    ]
                )
            elif flt == 'e':
                data.append(
                    [
                        _p(''),
                        _p(''),
                        _p(''),
                        _p(_('Total entradas')),
                        _p(_moeda(te)),
                        _p(''),
                        _p(''),
                    ]
                )
            else:
                data.append(
                    [
                        _p(''),
                        _p(''),
                        _p(''),
                        _p(_('Total saídas')),
                        _p(_moeda(ts)),
                        _p(''),
                        _p(''),
                    ]
                )
            t = Table(data, colWidths=tw_lanc, repeatRows=1)
            st_cmds = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e9ecef')),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('GRID', (0, 0), (-1, -1), 0.2, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                (
                    'ROWBACKGROUNDS',
                    (0, 1),
                    (-1, n0 - 1),
                    [colors.white, colors.HexColor('#f8f9fa')],
                ),
            ]
            for r in range(n0, len(data)):
                st_cmds.append(('FONTNAME', (0, r), (-1, r), 'Helvetica-Bold'))
            t.setStyle(TableStyle(st_cmds))
            story.append(t)
            story.append(Spacer(1, 0.2 * cm))

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
        story.append(Paragraph(_p(_('Resumo geral da competência')), h2_style))
        continua_txt = (
            _('Competência contínua: sim.')
            if competencia.competencia_continua
            else _('Competência contínua: não.')
        )
        story.append(Paragraph(_p(continua_txt), body))
        story.append(Spacer(1, 0.2 * cm))
        if flt == 'e':
            hdr = [
                _('Nome'),
                _('Tipo'),
                _('Total entradas (R$)'),
            ]
        elif flt == 's':
            hdr = [
                _('Nome'),
                _('Tipo'),
                _('Total saídas (R$)'),
            ]
        else:
            hdr = [
                _('Nome'),
                _('Tipo'),
                _('Entradas (R$)'),
                _('Saídas (R$)'),
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
            if flt == 'e':
                data.append([_p(conta.nome), _p(tipo_lbl), _p(_moeda(e))])
            elif flt == 's':
                data.append([_p(conta.nome), _p(tipo_lbl), _p(_moeda(s))])
            else:
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
        if competencia.competencia_continua and saldo_trazido_anterior is not None:
            prev_lbl = (
                _('Saldo acumulado até %(mes)02d/%(ano)s')
                % {
                    'mes': competencia_prev.mes,
                    'ano': competencia_prev.ano,
                }
                if competencia_prev
                else _('Saldo acumulado (sem competência anterior)')
            )
            if flt == 'e':
                data.append([_p(prev_lbl), _p(''), _p('—')])
            elif flt == 's':
                data.append([_p(prev_lbl), _p(''), _p('—')])
            else:
                data.append(
                    [
                        _p(prev_lbl),
                        _p(''),
                        _p('—'),
                        _p('—'),
                        _p(_moeda(saldo_trazido_anterior)),
                    ]
                )
        if flt == 'e':
            data.append(
                [
                    _p(_('Saldo geral (fechamento)')),
                    '',
                    _p(_moeda(competencia_total_entradas)),
                ]
            )
        elif flt == 's':
            data.append(
                [
                    _p(_('Saldo geral (fechamento)')),
                    '',
                    _p(_moeda(competencia_total_saidas)),
                ]
            )
        else:
            data.append(
                [
                    _p(_('Saldo geral (fechamento)')),
                    '',
                    _p(_moeda(competencia_total_entradas)),
                    _p(_moeda(competencia_total_saidas)),
                    _p(_moeda(competencia_saldo_geral_final)),
                ]
            )
        if flt in ('e', 's'):
            tw = [10 * cm, 3 * cm, 10.5 * cm]
        else:
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
        t.setStyle(TableStyle(style_cmds))
        story.append(t)

    doc.build(story)
    return buf.getvalue()
