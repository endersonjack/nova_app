from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .money_format import format_brl


class TipoContaFinanceira(models.TextChoices):
    BANCO = 'banco', _('Banco')
    CAIXA = 'caixa', _('Caixa')


class TipoCategoriaFinanceira(models.TextChoices):
    ENTRADA = 'entrada', _('Entrada')
    SAIDA = 'saida', _('Saída')


class CompetenciaTesouraria(models.Model):
    """Mês/ano de referência para relatórios e lançamentos da tesouraria."""

    mes = models.PositiveSmallIntegerField(
        _('Mês'),
        validators=[MinValueValidator(1), MaxValueValidator(12)],
    )
    ano = models.PositiveSmallIntegerField(_('Ano'))
    descricao = models.CharField(_('Descrição'), max_length=30, blank=True)
    fechada = models.BooleanField(_('Fechada'), default=False)
    data_fechamento = models.DateTimeField(
        _('Data de fechamento'),
        null=True,
        blank=True,
    )
    competencia_continua = models.BooleanField(
        _('Competência contínua'),
        default=True,
        help_text=_(
            'Se ativo, o saldo geral inclui o acumulado da competência anterior (cadeia de meses).'
        ),
    )

    class Meta:
        verbose_name = _('Competência da tesouraria')
        verbose_name_plural = _('Competências da tesouraria')
        ordering = ['-ano', '-mes']
        constraints = [
            models.UniqueConstraint(
                fields=('mes', 'ano'),
                name='tesouraria_competencia_mes_ano_uniq',
            ),
        ]

    def __str__(self) -> str:
        if self.descricao:
            return self.descricao
        return f'{self.mes:02d}/{self.ano}'


class ContaFinanceira(models.Model):
    """Onde a movimentação ocorre (conta bancária, caixa físico, etc.)."""

    nome = models.CharField(_('Nome'), max_length=100)
    tipo = models.CharField(
        _('Tipo'),
        max_length=10,
        choices=TipoContaFinanceira.choices,
    )
    descricao = models.TextField(_('Descrição'), blank=True)
    ativa = models.BooleanField(_('Ativa'), default=True)

    class Meta:
        verbose_name = _('Conta financeira')
        verbose_name_plural = _('Contas financeiras')
        ordering = ['tipo', 'nome']

    def __str__(self) -> str:
        return self.nome


class CategoriaFinanceira(models.Model):
    """Classifica lançamentos para relatórios e totais por tipo (entrada / saída)."""

    nome = models.CharField(_('Nome'), max_length=100)
    tipo = models.CharField(
        _('Tipo'),
        max_length=10,
        choices=TipoCategoriaFinanceira.choices,
    )
    ativa = models.BooleanField(_('Ativa'), default=True)

    class Meta:
        verbose_name = _('Categoria financeira')
        verbose_name_plural = _('Categorias financeiras')
        ordering = ['tipo', 'nome']

    def __str__(self) -> str:
        return f'{self.nome} ({self.get_tipo_display()})'


class EventoFinanceiro(models.Model):
    """Evento da igreja (culto, conferência, etc.) para marcar lançamentos e relatórios."""

    nome = models.CharField(_('Nome'), max_length=100)
    ativa = models.BooleanField(_('Ativa'), default=True)

    class Meta:
        verbose_name = _('Evento')
        verbose_name_plural = _('Eventos')
        ordering = ['nome']

    def __str__(self) -> str:
        return self.nome


class LancamentoFinanceiro(models.Model):
    """Linha de movimentação (entrada/saída) em conta, numa competência e categoria."""

    competencia = models.ForeignKey(
        CompetenciaTesouraria,
        on_delete=models.PROTECT,
        related_name='lancamentos',
        verbose_name=_('Competência'),
    )
    conta = models.ForeignKey(
        ContaFinanceira,
        on_delete=models.PROTECT,
        related_name='lancamentos',
        verbose_name=_('Conta'),
    )
    categoria = models.ForeignKey(
        CategoriaFinanceira,
        on_delete=models.PROTECT,
        related_name='lancamentos',
        verbose_name=_('Categoria'),
    )
    membro = models.ForeignKey(
        'membros.Membro',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lancamentos_financeiros',
        verbose_name=_('Membro'),
    )
    tipo = models.CharField(
        _('Tipo'),
        max_length=10,
        choices=TipoCategoriaFinanceira.choices,
    )
    data = models.DateField(_('Data'))
    descricao = models.CharField(_('Descrição'), max_length=255, blank=True)
    valor = models.DecimalField(
        _('Valor'),
        max_digits=12,
        decimal_places=2,
    )
    numero_documento = models.CharField(
        _('Número do documento'),
        max_length=50,
        blank=True,
    )
    observacao = models.TextField(_('Observação'), blank=True)
    evento = models.ForeignKey(
        EventoFinanceiro,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='lancamentos',
        verbose_name=_('Evento'),
    )
    criado_em = models.DateTimeField(_('Criado em'), auto_now_add=True)
    atualizado_em = models.DateTimeField(_('Atualizado em'), auto_now=True)

    class Meta:
        verbose_name = _('Lançamento financeiro')
        verbose_name_plural = _('Lançamentos financeiros')
        ordering = ['data', 'id']

    def save(self, *args, **kwargs):
        if not (self.descricao or '').strip() and self.categoria_id:
            self.descricao = self.categoria.nome
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        label = self.descricao.strip() if self.descricao else str(self.pk)
        return f'{self.get_tipo_display()} — {label} — R$ {format_brl(self.valor)}'
