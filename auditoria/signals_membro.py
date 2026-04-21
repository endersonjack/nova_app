"""
Auditoria do modelo Membro: criação, remoção, alteração de campos e edição de M2M (filhos).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver

from membros.models import EstadoCivil, Membro, Sexo

from .middleware import get_auditoria_usuario
from .models import TipoRegistoAuditoria
from .services import nome_exibicao_utilizador, registrar_auditoria

# Estado antes do save (por pk) para comparar alterações escalares.
_membro_snapshot_antes: dict[int, dict[str, Any]] = {}

_MEMBRO_ATTS = (
    'ativo',
    'nome_completo',
    'nome_conhecido',
    'cpf',
    'data_nascimento',
    'sexo',
    'endereco',
    'telefone',
    'email',
    'estado_civil',
    'casado_com_id',
    'data_casamento',
    'pai_id',
    'mae_id',
    'batizado',
    'data_batismo',
    'locomocao_id',
    'tamanho_camisa_id',
    'observacoes',
    'ministerios',
    'maps_embed',
    'latitude',
    'longitude',
)

_SEXO_LABEL = dict(Sexo.choices)
_ESTADO_CIVIL_LABEL = dict(EstadoCivil.choices)


def _foto_nome(m: Membro) -> str:
    f = m.foto
    if f and getattr(f, 'name', None):
        return str(f.name)
    return ''


def _snapshot(m: Membro) -> dict[str, Any]:
    d: dict[str, Any] = {att: getattr(m, att, None) for att in _MEMBRO_ATTS}
    d['_foto'] = _foto_nome(m)
    return d


def _locomocao_ou_camisa_label(field_name: str, pk: int) -> str:
    from membros.models import Locomocao, TamanhoCamisa

    if field_name == 'locomocao_id':
        return Locomocao.objects.filter(pk=pk).values_list('descricao', flat=True).first() or ''
    if field_name == 'tamanho_camisa_id':
        return TamanhoCamisa.objects.filter(pk=pk).values_list('descricao', flat=True).first() or ''
    return ''


def _fmt_valor(field_name: str, value: Any, membro_ref: Membro | None = None) -> str:
    if value is None or value == '':
        return '—'
    if field_name == 'sexo':
        if membro_ref is not None:
            try:
                return membro_ref.get_sexo_display()
            except Exception:
                pass
        return str(_SEXO_LABEL.get(str(value), value))
    if field_name == 'estado_civil':
        if membro_ref is not None:
            try:
                return membro_ref.get_estado_civil_display()
            except Exception:
                pass
        return str(_ESTADO_CIVIL_LABEL.get(str(value), value or '—'))
    if field_name in ('batizado', 'ativo'):
        return 'Sim' if value else 'Não'
    if field_name in ('data_nascimento', 'data_casamento', 'data_batismo') and isinstance(
        value, date
    ):
        return value.strftime('%d/%m/%Y')
    if field_name in ('latitude', 'longitude') and value is not None:
        return str(value)
    if field_name == 'maps_embed' and isinstance(value, str) and len(value) > 120:
        return value[:117] + '…'
    if field_name.endswith('_id'):
        pk = value
        if not pk:
            return '—'
        nome = Membro.todos.filter(pk=pk).values_list('nome_completo', flat=True).first()
        if nome:
            return f'{nome} (id {pk})'
        extra = _locomocao_ou_camisa_label(field_name, int(pk))
        if extra:
            return f'{extra} (id {pk})'
        return f'id {pk}'
    if field_name == 'cpf' and value:
        c = str(value)
        if len(c) == 11:
            return f'{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:11]}'
    return str(value)


def _rotulo_campo(name: str) -> str:
    try:
        f = Membro._meta.get_field(name)
        return str(f.verbose_name)
    except Exception:
        return name


def _nome_membro(m: Membro) -> str:
    return (m.nome_completo or '').strip() or f'Membro #{m.pk}'


@receiver(pre_save, sender=Membro)
def membro_pre_save_guardar_estado(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        antigo = Membro.todos.get(pk=instance.pk)
    except Membro.DoesNotExist:
        return
    _membro_snapshot_antes[instance.pk] = _snapshot(antigo)


@receiver(post_save, sender=Membro)
def membro_post_save_auditoria(sender, instance, created, **kwargs):
    ator = nome_exibicao_utilizador(get_auditoria_usuario())
    nome_m = _nome_membro(instance)
    objeto_tipo = 'membros.Membro'
    oid = instance.pk

    if created:
        registrar_auditoria(
            tipo=TipoRegistoAuditoria.CRIACAO,
            modulo='membros',
            detalhes=f'{ator} criou o membro «{nome_m}» (id {oid}).',
            objeto_tipo=objeto_tipo,
            objeto_id=oid,
        )
        _membro_snapshot_antes.pop(instance.pk, None)
        return

    antes = _membro_snapshot_antes.pop(instance.pk, None)
    if not antes:
        return

    depois = _snapshot(instance)
    linhas: list[str] = []
    for att in _MEMBRO_ATTS:
        a, b = antes.get(att), depois.get(att)
        if a != b:
            rotulo = _rotulo_campo(att)
            va = _fmt_valor(att, a, None)
            vb = _fmt_valor(att, b, instance)
            linhas.append(f'«{rotulo}» de {va} para {vb}')

    fa, fb = antes.get('_foto'), depois.get('_foto')
    if fa != fb:
        rotulo = _rotulo_campo('foto')
        if not fa:
            linhas.append(f'«{rotulo}»: enviou novo ficheiro ({fb or "—"})')
        elif not fb:
            linhas.append(f'«{rotulo}»: removeu a foto')
        else:
            linhas.append(f'«{rotulo}»: substituiu o ficheiro ({fa} → {fb})')

    if not linhas:
        return

    detalhes = (
        f'{ator} alterou dados do membro «{nome_m}» (id {oid}): '
        + '; '.join(linhas)
        + '.'
    )
    registrar_auditoria(
        tipo=TipoRegistoAuditoria.ALTERACAO,
        modulo='membros',
        detalhes=detalhes,
        objeto_tipo=objeto_tipo,
        objeto_id=oid,
    )


@receiver(post_delete, sender=Membro)
def membro_post_delete_auditoria(sender, instance, **kwargs):
    ator = nome_exibicao_utilizador(get_auditoria_usuario())
    nome_m = _nome_membro(instance)
    oid = instance.pk
    registrar_auditoria(
        tipo=TipoRegistoAuditoria.REMOCAO,
        modulo='membros',
        detalhes=f'{ator} removeu o membro «{nome_m}» (id {oid}).',
        objeto_tipo='membros.Membro',
        objeto_id=oid,
    )


def _nomes_membros_ids(pks: set) -> str:
    if not pks:
        return '—'
    rows = list(
        Membro.todos.filter(pk__in=pks)
        .values_list('pk', 'nome_completo')
        .order_by('nome_completo')
    )
    parts = [f'«{n or "—"}» (id {pk})' for pk, n in rows]
    return ', '.join(parts) if parts else ', '.join(str(x) for x in sorted(pks))


@receiver(m2m_changed, sender=Membro.filhos.through)
def membro_filhos_m2m_auditoria(sender, instance, action, pk_set, **kwargs):
    if action not in ('post_add', 'post_remove', 'post_clear'):
        return
    if not isinstance(instance, Membro):
        return
    ator = nome_exibicao_utilizador(get_auditoria_usuario())
    nome_pai = _nome_membro(instance)
    oid = instance.pk

    if action == 'post_clear':
        detalhes = f'{ator} removeu todos os vínculos de filhos(as) do membro «{nome_pai}» (id {oid}).'
    elif action == 'post_add':
        nomes = _nomes_membros_ids(set(pk_set))
        detalhes = f'{ator} associou filhos(as) ao membro «{nome_pai}» (id {oid}): {nomes}.'
    else:
        nomes = _nomes_membros_ids(set(pk_set))
        detalhes = f'{ator} desassociou filhos(as) do membro «{nome_pai}» (id {oid}): {nomes}.'

    registrar_auditoria(
        tipo=TipoRegistoAuditoria.EDICAO,
        modulo='membros',
        detalhes=detalhes,
        objeto_tipo='membros.Membro',
        objeto_id=oid,
    )
