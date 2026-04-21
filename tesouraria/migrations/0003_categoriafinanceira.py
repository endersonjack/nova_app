# Generated manually for CategoriaFinanceira

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tesouraria', '0002_contafinanceira'),
    ]

    operations = [
        migrations.CreateModel(
            name='CategoriaFinanceira',
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
                        choices=[
                            ('entrada', 'Entrada'),
                            ('saida', 'Saída'),
                        ],
                        max_length=10,
                        verbose_name='Tipo',
                    ),
                ),
                ('ativa', models.BooleanField(default=True, verbose_name='Ativa')),
            ],
            options={
                'verbose_name': 'Categoria financeira',
                'verbose_name_plural': 'Categorias financeiras',
                'ordering': ['tipo', 'nome'],
            },
        ),
    ]
