import re

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


def validate_cpf_digits(value: str) -> None:
    """Aceita apenas 11 dígitos (armazenamento sem máscara)."""
    if not value:
        return
    if not re.fullmatch(r'\d{11}', value):
        raise ValidationError(_('Informe o CPF com 11 dígitos.'))


def only_digits_cpf(value: str) -> str:
    if not value:
        return ''
    return re.sub(r'\D', '', value)
