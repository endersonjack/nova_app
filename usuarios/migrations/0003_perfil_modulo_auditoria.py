# Generated manually — expõe o módulo Auditoria a perfis não-admin (admin já tem todos).

from django.db import migrations


def add_modulo_auditoria(apps, schema_editor):
    UserProfile = apps.get_model('usuarios', 'UserProfile')
    for row in UserProfile.objects.exclude(papel='admin'):
        mods = list(row.modulos or [])
        if 'auditoria' not in mods:
            mods.append('auditoria')
            UserProfile.objects.filter(pk=row.pk).update(modulos=mods)


class Migration(migrations.Migration):

    dependencies = [
        ('usuarios', '0002_perfil_papel_modulos'),
    ]

    operations = [
        migrations.RunPython(add_modulo_auditoria, migrations.RunPython.noop),
    ]
