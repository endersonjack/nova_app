from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from django.urls import reverse
from django.utils.html import format_html

from .forms import UserProfileAdminForm
from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    form = UserProfileAdminForm
    can_delete = False
    fk_name = 'user'
    max_num = 1
    min_num = 0
    verbose_name = 'Perfil e permissões'
    verbose_name_plural = 'Perfil e permissões'
    autocomplete_fields = ('membro',)
    fields = ('membro', 'papel', 'modulos')


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)
    list_display = (
        'username',
        'membro_vinculado',
        'email',
        'first_name',
        'last_name',
        'is_staff',
    )
    search_fields = BaseUserAdmin.search_fields + (
        'perfil__membro__nome_completo',
        'perfil__membro__nome_conhecido',
        'perfil__membro__cpf',
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('perfil__membro')

    @admin.display(description='Membro vinculado', ordering='perfil__membro__nome_completo')
    def membro_vinculado(self, obj: User):
        try:
            perfil = obj.perfil
        except ObjectDoesNotExist:
            return '—'
        if not perfil.membro_id:
            return '—'
        url = reverse('admin:membros_membro_change', args=[perfil.membro_id])
        return format_html('<a href="{}">{}</a>', url, perfil.membro)


if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    form = UserProfileAdminForm
    list_display = ('user', 'membro', 'papel', 'modulos_resumo')
    list_select_related = ('user', 'membro')
    list_filter = ('papel',)
    search_fields = ('user__username', 'membro__nome_completo', 'membro__email')
    autocomplete_fields = ('user', 'membro')

    @admin.display(description='Módulos')
    def modulos_resumo(self, obj: UserProfile) -> str:
        return obj.rotulos_modulos()
