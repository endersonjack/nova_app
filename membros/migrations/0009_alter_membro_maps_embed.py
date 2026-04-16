from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('membros', '0008_membro_maps_coords'),
    ]

    operations = [
        migrations.AlterField(
            model_name='membro',
            name='maps_embed',
            field=models.TextField(
                blank=True,
                help_text='Cole o link ou o iframe do Google Maps. Ao salvar, o valor vira um iframe compacto e as coordenadas são preenchidas quando o link as contiver.',
                verbose_name='Mapa (embed)',
            ),
        ),
    ]
