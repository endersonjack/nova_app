import django.db.models.deletion
from django.db import migrations, models


LEGACY_LOCOMOCAO = {
    'pe': 'A pé',
    'carro': 'Carro',
    'moto': 'Moto',
    'bicicleta': 'Bicicleta',
    'apps': 'Apps',
    'outro': 'Outro',
}


def forwards_migrate(apps, schema_editor):
    Membro = apps.get_model('membros', 'Membro')
    Locomocao = apps.get_model('membros', 'Locomocao')
    TamanhoCamisa = apps.get_model('membros', 'TamanhoCamisa')

    cache_loco = {}
    for key, label in LEGACY_LOCOMOCAO.items():
        obj, _ = Locomocao.objects.get_or_create(descricao=label)
        cache_loco[key] = obj.pk

    for m in Membro.objects.all():
        updates = []
        raw_lo = (getattr(m, 'locomocao', '') or '').strip()
        if raw_lo and raw_lo in cache_loco:
            m.locomocao_ref_id = cache_loco[raw_lo]
            updates.append('locomocao_ref_id')
        tc = (getattr(m, 'tamanho_camisa', '') or '').strip()
        if tc:
            t, _ = TamanhoCamisa.objects.get_or_create(descricao=tc[:120])
            m.tamanho_camisa_ref_id = t.pk
            updates.append('tamanho_camisa_ref_id')
        if updates:
            m.save(update_fields=updates)


def backwards_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):
    dependencies = [
        ('membros', '0011_membro_tamanho_camisa'),
    ]

    operations = [
        migrations.CreateModel(
            name='Locomocao',
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
                    'descricao',
                    models.CharField(max_length=120, unique=True, verbose_name='Descrição'),
                ),
            ],
            options={
                'verbose_name': 'Locomoção',
                'verbose_name_plural': 'Locomoções',
                'ordering': ['descricao'],
            },
        ),
        migrations.CreateModel(
            name='TamanhoCamisa',
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
                    'descricao',
                    models.CharField(max_length=120, unique=True, verbose_name='Descrição'),
                ),
            ],
            options={
                'verbose_name': 'Tamanho da camisa',
                'verbose_name_plural': 'Tamanhos de camisa',
                'ordering': ['descricao'],
            },
        ),
        migrations.AddField(
            model_name='membro',
            name='locomocao_ref',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='membros',
                to='membros.locomocao',
                verbose_name='Locomoção',
            ),
        ),
        migrations.AddField(
            model_name='membro',
            name='tamanho_camisa_ref',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='membros',
                to='membros.tamanhocamisa',
                verbose_name='Tamanho da camisa',
            ),
        ),
        migrations.RunPython(forwards_migrate, backwards_noop),
        migrations.RemoveField(
            model_name='membro',
            name='locomocao',
        ),
        migrations.RemoveField(
            model_name='membro',
            name='tamanho_camisa',
        ),
        migrations.RenameField(
            model_name='membro',
            old_name='locomocao_ref',
            new_name='locomocao',
        ),
        migrations.RenameField(
            model_name='membro',
            old_name='tamanho_camisa_ref',
            new_name='tamanho_camisa',
        ),
    ]
