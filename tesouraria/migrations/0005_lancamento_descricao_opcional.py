# Generated manually

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tesouraria', '0004_lancamentofinanceiro'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lancamentofinanceiro',
            name='descricao',
            field=models.CharField(blank=True, max_length=255, verbose_name='Descrição'),
        ),
    ]
