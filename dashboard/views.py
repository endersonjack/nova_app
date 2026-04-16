from collections import Counter
from datetime import date

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from membros.models import Membro, Sexo

# Ordem fixa das fatias no gráfico (chave, rótulo exibido).
IDADE_FAIXAS = (
    ('bebe', 'Bebê (0–1 a.)'),
    ('crianca', 'Criança (1–4 a.)'),
    ('infantil', 'Infantil (4–6 a.)'),
    ('kids', 'Kids (6–8 a.)'),
    ('junior', 'Junior (8–12 a.)'),
    ('teens', 'Teens (12–14 a.)'),
    ('jovens', 'Jovens (14–18 a.)'),
    ('adultos', 'Adultos (18–55 a.)'),
    ('idoso', 'Idoso (56+ a.)'),
    ('sem_data', 'Sem data de nasc.'),
)

IDADE_CORES = (
    '#0ea5e9',
    '#14b8a6',
    '#22c55e',
    '#84cc16',
    '#eab308',
    '#f97316',
    '#ef4444',
    '#a855f7',
    '#6366f1',
    '#94a3b8',
)


def _idade_faixa_chave(data_nascimento) -> str:
    if not data_nascimento:
        return 'sem_data'
    hoje = date.today()
    if data_nascimento > hoje:
        return 'sem_data'
    anos = hoje.year - data_nascimento.year - (
        (hoje.month, hoje.day) < (data_nascimento.month, data_nascimento.day)
    )
    if anos < 0:
        return 'sem_data'
    if anos < 1:
        return 'bebe'
    if anos < 4:
        return 'crianca'
    if anos < 6:
        return 'infantil'
    if anos < 8:
        return 'kids'
    if anos < 12:
        return 'junior'
    if anos < 14:
        return 'teens'
    if anos < 18:
        return 'jovens'
    if anos <= 55:
        return 'adultos'
    return 'idoso'


def _idade_chart_payload(contagem: Counter) -> dict:
    labels = []
    counts = []
    colors = []
    for i, (key, rotulo) in enumerate(IDADE_FAIXAS):
        n = contagem.get(key, 0)
        if n > 0:
            labels.append(rotulo)
            counts.append(n)
            colors.append(IDADE_CORES[i])
    return {'labels': labels, 'counts': counts, 'colors': colors}


@login_required
def index(request):
    return render(request, 'dashboard/index.html')


@login_required
def inicio_conteudo(request):
    total = Membro.objects.count()
    masculino = Membro.objects.filter(sexo=Sexo.MASCULINO).count()
    feminino = Membro.objects.filter(sexo=Sexo.FEMININO).count()

    contagem_idade = Counter()
    for dn in Membro.objects.values_list('data_nascimento', flat=True):
        contagem_idade[_idade_faixa_chave(dn)] += 1

    idade_chart_payload = _idade_chart_payload(contagem_idade)

    return render(
        request,
        'dashboard/partials/_inicio_conteudo.html',
        {
            'total_membros': total,
            'membros_masculino': masculino,
            'membros_feminino': feminino,
            'idade_chart_payload': idade_chart_payload,
        },
    )
