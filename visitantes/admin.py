from django.contrib import admin

from .forms import VisitanteForm
from .models import Visitante


@admin.register(Visitante)
class VisitanteAdmin(admin.ModelAdmin):
    form = VisitanteForm
    list_display = (
        'ativo',
        'nome_completo',
        'nome_conhecido',
        'telefone_formatado_list',
        'membro_acompanha',
        'conheceu_por',
        'convertido',
        'batizado',
        'criado_em',
        'criado_por',
    )
    list_filter = ('ativo', 'sexo', 'conheceu_por', 'convertido', 'batizado', 'criado_em')
    search_fields = (
        'nome_completo',
        'nome_conhecido',
        'telefone',
        'denominacao',
        'membro_acompanha__nome_completo',
        'criado_por__username',
    )
    autocomplete_fields = ('membro_acompanha',)
    readonly_fields = ('criado_em', 'atualizado_em', 'criado_por')
    date_hierarchy = 'criado_em'

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'ativo',
                    'nome_completo',
                    'nome_conhecido',
                    'sexo',
                    'telefone',
                    'endereco',
                )
            },
        ),
        (
            'Acompanhamento',
            {'fields': ('membro_acompanha', 'conheceu_por')},
        ),
        (
            'Vida cristã',
            {'fields': ('convertido', 'batizado', 'denominacao')},
        ),
        (
            'Observações',
            {'fields': ('observacoes',)},
        ),
        (
            'Cadastro',
            {'fields': ('criado_em', 'atualizado_em', 'criado_por')},
        ),
    )

    def get_queryset(self, request):
        return Visitante.todos.select_related('membro_acompanha', 'criado_por')

    def save_model(self, request, obj, form, change):
        if not obj.pk and obj.criado_por_id is None:
            obj.criado_por = request.user
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        obj.ativo = False
        obj.save(update_fields=['ativo'])

    def delete_queryset(self, request, queryset):
        for obj in queryset:
            obj.ativo = False
            obj.save(update_fields=['ativo'])

    @admin.display(description='Telefone')
    def telefone_formatado_list(self, obj: Visitante) -> str:
        return obj.telefone_formatado or '—'
