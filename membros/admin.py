from django.contrib import admin
from django.utils.html import format_html

from .forms import MembroAdminForm
from .models import Membro


@admin.register(Membro)
class MembroAdmin(admin.ModelAdmin):
    form = MembroAdminForm
    list_display = (
        'nome_completo',
        'nome_conhecido',
        'cpf_formatado_list',
        'email',
        'telefone_formatado_list',
        'batizado',
    )
    list_filter = ('sexo', 'estado_civil', 'batizado', 'locomocao')
    search_fields = ('nome_completo', 'nome_conhecido', 'email', 'cpf', 'telefone')
    autocomplete_fields = ('casado_com',)
    filter_horizontal = ('filhos',)
    readonly_fields = (
        'cpf_formatado_readonly',
        'foto_preview',
    )

    fieldsets = (
        (
            None,
            {
                'fields': (
                    'nome_completo',
                    'nome_conhecido',
                    'cpf',
                    'cpf_formatado_readonly',
                    'data_nascimento',
                    'sexo',
                    'foto',
                    'foto_preview',
                ),
            },
        ),
        (
            'Contato',
            {'fields': ('endereco', 'telefone', 'email')},
        ),
        (
            'Família',
            {'fields': ('estado_civil', 'casado_com', 'data_casamento', 'filhos')},
        ),
        (
            'Batismo',
            {'fields': ('batizado', 'data_batismo')},
        ),
        (
            'Informações',
            {'fields': ('locomocao', 'observacoes')},
        ),
        (
            'Ministérios',
            {'fields': ('ministerios',)},
        ),
    )

    class Media:
        js = ('membros/js/admin_cpf_mask.js',)

    @admin.display(description='CPF')
    def cpf_formatado_list(self, obj: Membro) -> str:
        return obj.cpf_formatado or '—'

    @admin.display(description='Telefone')
    def telefone_formatado_list(self, obj: Membro) -> str:
        return obj.telefone_formatado or '—'

    @admin.display(description='CPF (visualização)')
    def cpf_formatado_readonly(self, obj: Membro) -> str:
        if obj is None or not getattr(obj, 'cpf', None):
            return '—'
        return obj.cpf_formatado

    @admin.display(description='Pré-visualização da foto')
    def foto_preview(self, obj: Membro):
        if obj.foto:
            return format_html(
                '<img src="{}" style="max-height:120px;max-width:120px;object-fit:cover;border-radius:8px;" />',
                obj.foto.url,
            )
        return '—'
