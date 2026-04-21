from __future__ import annotations

from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .money_format import format_brl, parse_brl_decimal


class BRLDecimalField(forms.DecimalField):
    """Decimal com entrada no padrão brasileiro (milhar . e decimal ,)."""

    def to_python(self, value):
        if value in self.empty_values:
            return None
        if isinstance(value, Decimal):
            return value
        try:
            return parse_brl_decimal(
                value,
                max_digits=self.max_digits,
                decimal_places=self.decimal_places,
            )
        except ValidationError:
            raise

    def prepare_value(self, value):
        if value in self.empty_values:
            return ''
        if isinstance(value, Decimal):
            return format_brl(value)
        return str(value)
