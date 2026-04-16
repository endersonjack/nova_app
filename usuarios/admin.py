from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User

from .models import UserProfile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    fk_name = 'user'
    max_num = 1
    min_num = 0
    verbose_name = 'Vínculo com membro'
    verbose_name_plural = 'Vínculo com membro'
    autocomplete_fields = ('membro',)
    fields = ('membro',)


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)


if admin.site.is_registered(User):
    admin.site.unregister(User)
admin.site.register(User, UserAdmin)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'membro')
    list_select_related = ('user', 'membro')
    search_fields = ('user__username', 'membro__nome_completo', 'membro__email')
    autocomplete_fields = ('user', 'membro')
