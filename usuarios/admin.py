from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

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
