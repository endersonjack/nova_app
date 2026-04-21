from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import LogAuditoria


@admin.register(LogAuditoria)
class LogAuditoriaAdmin(admin.ModelAdmin):
    list_display = (
        'criado_em',
        'usuario',
        'tipo',
        'modulo',
        'detalhes_curto',
        'objeto_tipo',
        'objeto_id',
    )
    list_filter = ('tipo', 'modulo', 'criado_em')
    search_fields = ('detalhes', 'usuario__username')
    readonly_fields = (
        'criado_em',
        'usuario',
        'tipo',
        'modulo',
        'detalhes',
        'objeto_tipo',
        'objeto_id',
    )
    date_hierarchy = 'criado_em'

    @admin.display(description=_('Detalhes'))
    def detalhes_curto(self, obj: LogAuditoria) -> str:
        t = (obj.detalhes or '').strip()
        if len(t) > 100:
            return t[:97] + '…'
        return t

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return request.user.is_staff

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser
