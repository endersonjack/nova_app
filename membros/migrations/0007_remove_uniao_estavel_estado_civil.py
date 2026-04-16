from django.db import migrations, models


def forwards(apps, schema_editor):
    Membro = apps.get_model('membros', 'Membro')
    Membro.objects.filter(estado_civil='uniao_estavel').update(estado_civil='casado')


class Migration(migrations.Migration):
    dependencies = [
        ('membros', '0006_alter_cpf_help_text'),
    ]

    operations = [
        migrations.RunPython(forwards, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='membro',
            name='estado_civil',
            field=models.CharField(
                blank=True,
                choices=[
                    ('solteiro', 'Solteiro(a)'),
                    ('casado', 'Casado(a)'),
                    ('divorciado', 'Divorciado(a)'),
                    ('viuvo', 'Viúvo(a)'),
                    ('separado', 'Separado(a)'),
                    ('outro', 'Outro'),
                ],
                max_length=20,
                verbose_name='Estado civil',
            ),
        ),
    ]
