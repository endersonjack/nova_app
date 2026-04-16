from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('membros', '0010_membro_pai_mae'),
    ]

    operations = [
        migrations.AddField(
            model_name='membro',
            name='tamanho_camisa',
            field=models.CharField(blank=True, max_length=20, verbose_name='Tamanho da camisa'),
        ),
    ]

