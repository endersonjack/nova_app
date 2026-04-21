# Generated manually for CompetenciaTesouraria

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='CompetenciaTesouraria',
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
                    'mes',
                    models.PositiveSmallIntegerField(
                        validators=[
                            django.core.validators.MinValueValidator(1),
                            django.core.validators.MaxValueValidator(12),
                        ],
                        verbose_name='Mês',
                    ),
                ),
                ('ano', models.PositiveSmallIntegerField(verbose_name='Ano')),
                (
                    'descricao',
                    models.CharField(
                        blank=True,
                        max_length=30,
                        verbose_name='Descrição',
                    ),
                ),
                (
                    'fechada',
                    models.BooleanField(default=False, verbose_name='Fechada'),
                ),
                (
                    'data_fechamento',
                    models.DateTimeField(
                        blank=True,
                        null=True,
                        verbose_name='Data de fechamento',
                    ),
                ),
            ],
            options={
                'verbose_name': 'Competência da tesouraria',
                'verbose_name_plural': 'Competências da tesouraria',
                'ordering': ['-ano', '-mes'],
            },
        ),
        migrations.AddConstraint(
            model_name='competenciatesouraria',
            constraint=models.UniqueConstraint(
                fields=('mes', 'ano'),
                name='tesouraria_competencia_mes_ano_uniq',
            ),
        ),
    ]
