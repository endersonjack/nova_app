# Generated manually for ContaFinanceira

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tesouraria', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContaFinanceira',
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
                ('nome', models.CharField(max_length=100, verbose_name='Nome')),
                (
                    'tipo',
                    models.CharField(
                        choices=[('banco', 'Banco'), ('caixa', 'Caixa')],
                        max_length=10,
                        verbose_name='Tipo',
                    ),
                ),
                ('descricao', models.TextField(blank=True, verbose_name='Descrição')),
                ('ativa', models.BooleanField(default=True, verbose_name='Ativa')),
            ],
            options={
                'verbose_name': 'Conta financeira',
                'verbose_name_plural': 'Contas financeiras',
                'ordering': ['tipo', 'nome'],
            },
        ),
    ]
