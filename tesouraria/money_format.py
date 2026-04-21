"""Formato monetário brasileiro (Real) para o módulo tesouraria."""

from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def format_brl(value: Decimal | float | str | int | None) -> str:
    """Ex.: Decimal('1234.56') → '1.234,56'."""
    if value is None:
        return ''
    try:
        d = Decimal(str(value)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return ''
    negative = d < 0
    d = abs(d)
    s = f'{d:.2f}'
    whole, frac = s.split('.')
    rev = whole[::-1]
    chunks = [rev[i : i + 3] for i in range(0, len(rev), 3)]
    whole_fmt = '.'.join(c[::-1] for c in reversed(chunks))
    out = f'{whole_fmt},{frac}'
    return f'-{out}' if negative else out


def parse_brl_decimal(
    value,
    *,
    max_digits: int = 12,
    decimal_places: int = 2,
) -> Decimal | None:
    """
    Aceita '1.234,56', '1234,56', '1234.56', espaços, prefixo R$.
    """
    if value in (None, ''):
        return None
    if isinstance(value, Decimal):
        return value.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    s = str(value).strip().replace('R$', '').replace('\u00a0', '').replace(' ', '')
    if not s:
        return None
    if ',' in s:
        s = s.replace('.', '').replace(',', '.')
    try:
        d = Decimal(s)
    except InvalidOperation as e:
        raise ValidationError(_('Informe um valor numérico válido.')) from e
    d = d.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
    lim = Decimal(10) ** (max_digits - decimal_places) - Decimal('0.01')
    if abs(d) > lim:
        raise ValidationError(
            _('O valor excede o limite permitido (%(lim)s).')
            % {'lim': format_brl(lim)}
        )
    return d
