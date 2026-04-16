import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def create_profiles_for_existing_users(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('usuarios', 'UserProfile')
    for u in User.objects.all():
        UserProfile.objects.get_or_create(user_id=u.pk)


def noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('membros', '0010_membro_pai_mae'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                (
                    'id',
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name='ID',
                    ),
                ),
                (
                    'membro',
                    models.OneToOneField(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='perfil_usuario',
                        to='membros.membro',
                        verbose_name='Membro',
                    ),
                ),
                (
                    'user',
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='perfil',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Usuário',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Perfil de usuário',
                'verbose_name_plural': 'Perfis de usuário',
            },
        ),
        migrations.RunPython(create_profiles_for_existing_users, noop),
    ]
