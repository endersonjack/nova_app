import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('membros', '0009_alter_membro_maps_embed'),
    ]

    operations = [
        migrations.AddField(
            model_name='membro',
            name='pai',
            field=models.ForeignKey(
                blank=True,
                help_text='Preenchido automaticamente ao vincular um filho a um pai (sexo masculino) na seção família desse pai.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='como_pai_de',
                to='membros.membro',
                verbose_name='Pai',
            ),
        ),
        migrations.AddField(
            model_name='membro',
            name='mae',
            field=models.ForeignKey(
                blank=True,
                help_text='Preenchido automaticamente ao vincular um filho a uma mãe (sexo feminino) na seção família dessa mãe.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='como_mae_de',
                to='membros.membro',
                verbose_name='Mãe',
            ),
        ),
    ]
