from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .money_format import format_brl
from .models import (
    CategoriaFinanceira,
    CompetenciaTesouraria,
    ContaFinanceira,
    EventoFinanceiro,
    LancamentoFinanceiro,
)


@admin.register(CompetenciaTesouraria)
class CompetenciaTesourariaAdmin(admin.ModelAdmin):
    list_display = (
        'mes',
        'ano',
        'descricao',
        'competencia_continua',
        'fechada',
        'data_fechamento',
    )
    list_filter = ('fechada', 'competencia_continua', 'ano')
    search_fields = ('descricao',)
    ordering = ('-ano', '-mes')


@admin.register(ContaFinanceira)
class ContaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'ativa')
    list_filter = ('tipo', 'ativa')
    search_fields = ('nome', 'descricao')
    ordering = ('tipo', 'nome')


@admin.register(CategoriaFinanceira)
class CategoriaFinanceiraAdmin(admin.ModelAdmin):
    list_display = ('nome', 'tipo', 'ativa')
    list_filter = ('tipo', 'ativa')
    search_fields = ('nome',)
    ordering = ('tipo', 'nome')


@admin.register(EventoFinanceiro)
class EventoFinanceiroAdmin(admin.ModelAdmin):
    list_display = ('nome', 'ativa')
    list_filter = ('ativa',)
    search_fields = ('nome',)
    ordering = ('nome',)


@admin.register(LancamentoFinanceiro)
class LancamentoFinanceiroAdmin(admin.ModelAdmin):
    list_display = (
        'data',
        'tipo',
        'descricao',
        'valor_formatado',
        'competencia',
        'conta',
        'categoria',
        'membro',
    )
    list_filter = ('tipo', 'data', 'competencia', 'conta', 'categoria')
    search_fields = ('descricao', 'numero_documento', 'observacao')
    autocomplete_fields = ('competencia', 'conta', 'categoria', 'membro', 'evento')
    ordering = ('-data', '-id')
    date_hierarchy = 'data'

    @admin.display(description=_('Valor'), ordering='valor')
    def valor_formatado(self, obj):
        return f'R$ {format_brl(obj.valor)}'
