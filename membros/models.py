import re
from decimal import Decimal
from html import escape, unescape
from typing import Optional, Tuple

from django.db import models
from django.utils.translation import gettext_lazy as _

from .validators import validate_cpf_digits


def _coord_text_to_decimal(fragment: str) -> Decimal:
    """Converte trecho numérico de coordenada (ponto ou vírgula decimal) em Decimal."""
    t = (fragment or '').strip()
    if not t:
        raise ValueError
    if '.' in t:
        t = t.replace(',', '')
    else:
        t = t.replace(',', '.')
    return Decimal(t)


def extract_maps_src_from_input(raw: str) -> str:
    """Obtém a URL do mapa a partir de um link solto ou do atributo src de um iframe."""
    text = (raw or '').strip()
    if not text:
        return ''
    m = re.search(r'src\s*=\s*["\']([^"\']+)["\']', text, re.I)
    if m:
        return m.group(1).strip()
    return text


def _maps_src_allowed(src: str) -> bool:
    s = (src or '').strip()
    if not s.startswith('https://'):
        return False
    low = s.lower()
    if 'javascript:' in low or '<' in s:
        return False
    return 'google.com/maps' in low or 'maps.google.com' in low


def normalize_maps_embed_for_storage(raw: str) -> str:
    """
    Gera um iframe compacto do Google Maps a partir de URL ou HTML colado.
    Retorna string vazia se a origem não for uma URL de embed permitida.
    """
    src = extract_maps_src_from_input(raw)
    if not src or not _maps_src_allowed(src):
        return ''
    esc = escape(src, quote=True)
    return (
        '<iframe class="membro-maps-iframe" src="{}" width="480" height="280" '
        'style="border:0;max-width:100%;" loading="lazy" '
        'referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>'
    ).format(esc)


def parse_lat_lng_from_maps_url(raw: str) -> Optional[Tuple[Decimal, Decimal]]:
    """Extrai latitude e longitude de URLs comuns do Google Maps / embed."""
    if not raw or not str(raw).strip():
        return None
    text = str(raw).strip()
    m_iframe = re.search(r'src\s*=\s*["\']([^"\']+)["\']', text, re.I)
    url = unescape((m_iframe.group(1) if m_iframe else text).strip())
    # @lat,lng (zoom opcional)
    num = r'-?[\d]+(?:[.,][\d]+)?'
    m = re.search(rf'@({num}),({num})', url)
    if m:
        return _coord_text_to_decimal(m.group(1)), _coord_text_to_decimal(m.group(2))
    # ?q=lat,lng ou &q=lat,lng
    m = re.search(rf'[?&]q=({num}),({num})', url, re.I)
    if m:
        return _coord_text_to_decimal(m.group(1)), _coord_text_to_decimal(m.group(2))
    # ll=lat,lng
    m = re.search(rf'[?&]ll=({num}),({num})', url, re.I)
    if m:
        return _coord_text_to_decimal(m.group(1)), _coord_text_to_decimal(m.group(2))
    # maps/embed?pb=… !2dLNG!3dLAT
    m = re.search(rf'!2d({num})!3d({num})', url)
    if m:
        lng, lat = m.group(1), m.group(2)
        return _coord_text_to_decimal(lat), _coord_text_to_decimal(lng)
    # !3dLAT!2dLNG (variação)
    m = re.search(rf'!3d({num})!2d({num})', url)
    if m:
        return _coord_text_to_decimal(m.group(1)), _coord_text_to_decimal(m.group(2))
    # !3dlat!4dlng (place / embed)
    m = re.search(rf'!3d({num})!4d({num})', url)
    if m:
        return _coord_text_to_decimal(m.group(1)), _coord_text_to_decimal(m.group(2))
    return None


class Sexo(models.TextChoices):
    MASCULINO = 'M', _('Masculino')
    FEMININO = 'F', _('Feminino')


class EstadoCivil(models.TextChoices):
    SOLTEIRO = 'solteiro', _('Solteiro(a)')
    CASADO = 'casado', _('Casado(a)')
    DIVORCIADO = 'divorciado', _('Divorciado(a)')
    VIUVO = 'viuvo', _('Viúvo(a)')
    SEPARADO = 'separado', _('Separado(a)')
    OUTRO = 'outro', _('Outro')


ESTADOS_COM_CONJUGE = frozenset((EstadoCivil.CASADO,))


class Locomocao(models.TextChoices):
    PE = 'pe', _('A pé')
    CARRO = 'carro', _('Carro')
    MOTO = 'moto', _('Moto')
    BICICLETA = 'bicicleta', _('Bicicleta')
    APPS = 'apps', _('Apps')
    OUTRO = 'outro', _('Outro')


class Membro(models.Model):
    nome_completo = models.CharField(_('Nome completo'), max_length=255)
    nome_conhecido = models.CharField(_('Conhecido por:'), max_length=120, blank=True)
    cpf = models.CharField(
        _('CPF'),
        max_length=11,
        unique=True,
        blank=True,
        null=True,
        validators=[validate_cpf_digits],
    )
    data_nascimento = models.DateField(_('Data de nascimento'), null=True, blank=True)
    sexo = models.CharField(
        _('Sexo'),
        max_length=1,
        choices=Sexo.choices,
        default=Sexo.MASCULINO,
    )
    endereco = models.TextField(_('Endereço'), blank=True)
    telefone = models.CharField(_('Telefone'), max_length=20, blank=True)
    email = models.EmailField(_('E-mail'), blank=True)

    estado_civil = models.CharField(
        _('Estado civil'),
        max_length=20,
        choices=EstadoCivil.choices,
        blank=True,
    )
    casado_com = models.ForeignKey(
        'self',
        verbose_name=_('Casado(a) com'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='parceiros',
    )
    data_casamento = models.DateField(_('Data de casamento'), null=True, blank=True)

    filhos = models.ManyToManyField(
        'self',
        verbose_name=_('Filhos(as)'),
        symmetrical=False,
        related_name='pais',
        blank=True,
        help_text=_('Outros membros cadastrados como filhos.'),
    )
    pai = models.ForeignKey(
        'self',
        verbose_name=_('Pai'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='como_pai_de',
        help_text=_(
            'Preenchido automaticamente ao vincular um filho a um pai (sexo masculino) '
            'na seção família desse pai.'
        ),
    )
    mae = models.ForeignKey(
        'self',
        verbose_name=_('Mãe'),
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='como_mae_de',
        help_text=_(
            'Preenchido automaticamente ao vincular um filho a uma mãe (sexo feminino) '
            'na seção família dessa mãe.'
        ),
    )

    batizado = models.BooleanField(_('É batizado(a)?'), default=False)
    data_batismo = models.DateField(_('Data de batismo'), null=True, blank=True)

    locomocao = models.CharField(
        _('Locomoção'),
        max_length=20,
        choices=Locomocao.choices,
        blank=True,
    )
    observacoes = models.TextField(_('Observações'), blank=True)

    ministerios = models.TextField(
        _('Ministérios'),
        blank=True,
        help_text=_('Participação em ministérios ou equipes.'),
    )

    foto = models.ImageField(_('Foto'), upload_to='membros/fotos/', blank=True, null=True)

    maps_embed = models.TextField(
        _('Mapa (embed)'),
        blank=True,
        help_text=_(
            'Cole o link ou o iframe do Google Maps. Ao salvar, o valor vira um '
            'iframe compacto e as coordenadas são preenchidas quando o link '
            'as contiver.'
        ),
    )
    latitude = models.DecimalField(
        _('Latitude'),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )
    longitude = models.DecimalField(
        _('Longitude'),
        max_digits=10,
        decimal_places=7,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _('Membro')
        verbose_name_plural = _('Membros')
        ordering = ['nome_completo']

    def __str__(self) -> str:
        return (self.nome_completo or '').strip() or '—'

    def sincronizar_papel_parental_filhos(self, old_ids: set, new_ids: set) -> None:
        """Atualiza pai/mae nos filhos quando a lista M2M filhos deste membro muda."""
        if not self.pk:
            return
        sx = (self.sexo or '').strip().upper()
        removed = old_ids - new_ids
        for cid in removed:
            if sx == Sexo.MASCULINO.value:
                Membro.objects.filter(pk=cid, pai_id=self.pk).update(pai_id=None)
            elif sx == Sexo.FEMININO.value:
                Membro.objects.filter(pk=cid, mae_id=self.pk).update(mae_id=None)
        for cid in new_ids:
            if sx == Sexo.MASCULINO.value:
                Membro.objects.filter(pk=cid).update(pai_id=self.pk)
            elif sx == Sexo.FEMININO.value:
                Membro.objects.filter(pk=cid).update(mae_id=self.pk)

    def _sync_maps_coordinates(self) -> None:
        raw = (self.maps_embed or '').strip()
        if not raw:
            self.latitude = None
            self.longitude = None
            return
        normalized = normalize_maps_embed_for_storage(raw)
        self.maps_embed = normalized
        if not normalized:
            self.latitude = None
            self.longitude = None
            return
        parsed = parse_lat_lng_from_maps_url(normalized)
        if parsed:
            self.latitude, self.longitude = parsed[0], parsed[1]
        else:
            self.latitude = None
            self.longitude = None

    def save(self, *args, **kwargs):
        update_fields = kwargs.get('update_fields')
        if update_fields is None or 'maps_embed' in update_fields:
            self._sync_maps_coordinates()
            if update_fields is not None:
                kwargs['update_fields'] = list(
                    frozenset(update_fields) | {'latitude', 'longitude'},
                )
        update_fields = kwargs.get('update_fields')
        spouse_fields_dirty = update_fields is None or any(
            name in update_fields
            for name in ('casado_com', 'estado_civil', 'data_casamento')
        )
        old_partner_id = None
        if spouse_fields_dirty and self.pk:
            old_partner_id = (
                Membro.objects.filter(pk=self.pk)
                .values_list('casado_com_id', flat=True)
                .first()
            )
        super().save(*args, **kwargs)
        if spouse_fields_dirty:
            self._espelhar_conjuge(old_partner_id)

    def _espelhar_conjuge(self, old_partner_id: Optional[int]) -> None:
        """Atualiza o outro membro para manter casamento / união espelhado (sem recursão em save())."""
        new_pid = self.casado_com_id
        union_ok = (self.estado_civil or '') in ESTADOS_COM_CONJUGE and bool(new_pid)

        if old_partner_id and (
            old_partner_id != new_pid or not union_ok
        ):
            Membro.objects.filter(pk=old_partner_id, casado_com_id=self.pk).update(
                casado_com=None,
                estado_civil='',
                data_casamento=None,
            )

        if union_ok and new_pid:
            Membro.objects.filter(casado_com_id=new_pid).exclude(pk=self.pk).update(
                casado_com=None,
                estado_civil='',
                data_casamento=None,
            )
            Membro.objects.filter(pk=new_pid).exclude(pk=self.pk).update(
                casado_com_id=self.pk,
                estado_civil=self.estado_civil,
                data_casamento=self.data_casamento,
            )
        elif new_pid and not union_ok:
            Membro.objects.filter(pk=new_pid, casado_com_id=self.pk).update(
                casado_com=None,
            )

    @property
    def cpf_formatado(self) -> str:
        """Exibe CPF no padrão 000.000.000-00."""
        c = self.cpf or ''
        if len(c) != 11:
            return c
        return f'{c[:3]}.{c[3:6]}.{c[6:9]}-{c[9:11]}'

    @property
    def telefone_formatado(self) -> str:
        """Exibe telefone (84) 99999-9999 ou (84) 9999-9999 a partir dos dígitos."""
        d = re.sub(r'\D', '', self.telefone or '')
        if len(d) == 11:
            return f'({d[:2]}) {d[2:7]}-{d[7:11]}'
        if len(d) == 10:
            return f'({d[:2]}) {d[2:6]}-{d[6:10]}'
        return self.telefone or ''
