from __future__ import annotations

from decimal import Decimal

from django import template

from ..money_format import format_brl

register = template.Library()


@register.filter
def saldo_na_conta(saldos, conta) -> Decimal:
    """`saldos` é dict conta_pk → Decimal (entradas − saídas)."""
    if saldos is None or conta is None:
        return Decimal('0')
    v = saldos.get(conta.pk)
    return v if v is not None else Decimal('0')


@register.filter
def moeda_brl(value) -> str:
    """Formata como Real brasileiro: R$ 1.234,56."""
    if value is None or value == '':
        return '—'
    try:
        d = Decimal(str(value))
    except Exception:
        return str(value)
    return f'R$ {format_brl(d)}'
