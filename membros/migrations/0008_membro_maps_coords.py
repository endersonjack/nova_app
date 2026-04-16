from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('membros', '0007_remove_uniao_estavel_estado_civil'),
    ]

    operations = [
        migrations.AddField(
            model_name='membro',
            name='maps_embed',
            field=models.CharField(
                blank=True,
                help_text='Cole o link ou o iframe incorporado; latitude e longitude serão preenchidas automaticamente quando o link contiver coordenadas.',
                max_length=2048,
                verbose_name='Link do Google Maps',
            ),
        ),
        migrations.AddField(
            model_name='membro',
            name='latitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name='Latitude',
            ),
        ),
        migrations.AddField(
            model_name='membro',
            name='longitude',
            field=models.DecimalField(
                blank=True,
                decimal_places=7,
                max_digits=10,
                null=True,
                verbose_name='Longitude',
            ),
        ),
    ]
