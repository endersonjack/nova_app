from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tesouraria', '0005_lancamento_descricao_opcional'),
    ]

    operations = [
        migrations.AddField(
            model_name='competenciatesouraria',
            name='competencia_continua',
            field=models.BooleanField(
                default=True,
                help_text='Se ativo, o saldo geral inclui o acumulado da competência anterior (cadeia de meses).',
                verbose_name='Competência contínua',
            ),
        ),
    ]
