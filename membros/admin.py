from django.contrib import admin
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.html import format_html

from .forms import MembroAdminForm
from .models import Locomocao, Membro, TamanhoCamisa


@admin.register(Locomocao)
class LocomocaoAdmin(admin.ModelAdmin):
    list_display = ('descricao',)
    search_fields = ('descricao',)


@admin.register(TamanhoCamisa)
class TamanhoCamisaAdmin(admin.ModelAdmin):
    list_display = ('descricao',)
    search_fields = ('descricao',)


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
    list_filter = ('sexo', 'estado_civil', 'batizado', 'locomocao', 'tamanho_camisa')
    search_fields = ('nome_completo', 'nome_conhecido', 'email', 'cpf', 'telefone')
    autocomplete_fields = ('casado_com', 'pai', 'mae', 'locomocao', 'tamanho_camisa')
    filter_horizontal = ('filhos',)
    readonly_fields = (
        'cpf_formatado_readonly',
        'foto_preview',
        'usuario_login_display',
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
            {'fields': ('telefone', 'email', 'usuario_login_display')},
        ),
        (
            'Localidade',
            {
                'fields': ('endereco', 'maps_embed', 'latitude', 'longitude'),
                'description': 'Ao salvar, latitude e longitude são atualizadas quando o link ou iframe contiver coordenadas; caso contrário você pode preenchê-las à mão.',
            },
        ),
        (
            'Família',
            {
                'fields': (
                    'estado_civil',
                    'casado_com',
                    'data_casamento',
                    'pai',
                    'mae',
                    'filhos',
                ),
            },
        ),
        (
            'Batismo',
            {'fields': ('batizado', 'data_batismo')},
        ),
        (
            'Informações',
            {'fields': ('locomocao', 'tamanho_camisa', 'observacoes')},
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

    @admin.display(description='Usuário do sistema vinculado')
    def usuario_login_display(self, obj: Membro) -> str:
        if not obj.pk:
            return '—'
        try:
            p = obj.perfil_usuario
        except ObjectDoesNotExist:
            return '—'
        if not p.user_id:
            return '—'
        u = p.user
        url = reverse('admin:auth_user_change', args=[u.pk])
        return format_html('<a href="{}">{}</a>', url, u.get_username())
