from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class TesourariaConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tesouraria'
    verbose_name = _('Tesouraria')
