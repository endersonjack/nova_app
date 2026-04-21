# Generated manually for LancamentoFinanceiro

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('membros', '0013_membro_ativo_soft_delete'),
        ('tesouraria', '0003_categoriafinanceira'),
    ]

    operations = [
        migrations.CreateModel(
            name='LancamentoFinanceiro',
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
                    'tipo',
                    models.CharField(
                        choices=[('entrada', 'Entrada'), ('saida', 'Saída')],
                        max_length=10,
                        verbose_name='Tipo',
                    ),
                ),
                ('data', models.DateField(verbose_name='Data')),
                (
                    'descricao',
                    models.CharField(max_length=255, verbose_name='Descrição'),
                ),
                (
                    'valor',
                    models.DecimalField(
                        decimal_places=2,
                        max_digits=12,
                        verbose_name='Valor',
                    ),
                ),
                (
                    'numero_documento',
                    models.CharField(
                        blank=True,
                        max_length=50,
                        verbose_name='Número do documento',
                    ),
                ),
                (
                    'observacao',
                    models.TextField(blank=True, verbose_name='Observação'),
                ),
                (
                    'criado_em',
                    models.DateTimeField(
                        auto_now_add=True,
                        verbose_name='Criado em',
                    ),
                ),
                (
                    'atualizado_em',
                    models.DateTimeField(
                        auto_now=True,
                        verbose_name='Atualizado em',
                    ),
                ),
                (
                    'categoria',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='lancamentos',
                        to='tesouraria.categoriafinanceira',
                        verbose_name='Categoria',
                    ),
                ),
                (
                    'competencia',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='lancamentos',
                        to='tesouraria.competenciatesouraria',
                        verbose_name='Competência',
                    ),
                ),
                (
                    'conta',
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name='lancamentos',
                        to='tesouraria.contafinanceira',
                        verbose_name='Conta',
                    ),
                ),
                (
                    'membro',
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name='lancamentos_financeiros',
                        to='membros.membro',
                        verbose_name='Membro',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Lançamento financeiro',
                'verbose_name_plural': 'Lançamentos financeiros',
                'ordering': ['data', 'id'],
            },
        ),
    ]
