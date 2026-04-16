(function () {
  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function escapeHtml(s) {
    return escapeAttr(s);
  }

  /** ~0,00009° ≈ 10 m (latitude); pins mais próximos que isso são espalhados em círculo. */
  var PROXIMITY_DEG = 0.00009;
  var SPREAD_BASE_DEG = 0.00004;

  function distDeg(a, b) {
    var dLat = a.lat - b.lat;
    var dLng = a.lng - b.lng;
    return Math.sqrt(dLat * dLat + dLng * dLng);
  }

  /**
   * Agrupa pins muito próximos (ligação transitiva) e reposiciona cada grupo
   * em círculo ao redor do centro, para não ficarem um em cima do outro.
   */
  function spreadOverlappingPins(items) {
    var validIdx = [];
    for (var i = 0; i < items.length; i++) {
      if (typeof items[i].lat === 'number' && typeof items[i].lng === 'number') {
        validIdx.push(i);
      }
    }
    var n = validIdx.length;
    if (n < 2) return;

    var parent = [];
    for (var i = 0; i < n; i++) parent[i] = i;

    function find(x) {
      return parent[x] === x ? x : (parent[x] = find(parent[x]));
    }
    function union(a, b) {
      var ra = find(a);
      var rb = find(b);
      if (ra !== rb) parent[ra] = rb;
    }

    for (var i = 0; i < n; i++) {
      for (var j = i + 1; j < n; j++) {
        var ii = validIdx[i];
        var jj = validIdx[j];
        if (distDeg(items[ii], items[jj]) < PROXIMITY_DEG) {
          union(i, j);
        }
      }
    }

    var comps = {};
    for (var i = 0; i < n; i++) {
      var r = find(i);
      if (!comps[r]) comps[r] = [];
      comps[r].push(validIdx[i]);
    }

    Object.keys(comps).forEach(function (k) {
      var idxs = comps[k];
      if (idxs.length < 2) return;

      var nomesGrupo = idxs.map(function (ii) {
        return ((items[ii].nome || '').trim() || '—');
      });
      for (var g = 0; g < idxs.length; g++) {
        items[idxs[g]].nomesGrupo = nomesGrupo;
      }

      var latSum = 0;
      var lngSum = 0;
      for (var t = 0; t < idxs.length; t++) {
        latSum += items[idxs[t]].lat;
        lngSum += items[idxs[t]].lng;
      }
      var cLat = latSum / idxs.length;
      var cLng = lngSum / idxs.length;
      var scaleLng = 1 / Math.cos((cLat * Math.PI) / 180);
      var R = SPREAD_BASE_DEG * Math.sqrt(idxs.length);
      for (var t = 0; t < idxs.length; t++) {
        var angle = (2 * Math.PI * t) / idxs.length - Math.PI / 2;
        var ii = idxs[t];
        items[ii].lat = cLat + R * Math.cos(angle);
        items[ii].lng = cLng + R * Math.sin(angle) * scaleLng;
      }
    });
  }

  function buildTooltipHtml(markerData, nomeFallback) {
    var grupo = markerData.nomesGrupo;
    if (grupo && grupo.length > 1) {
      return (
        '<div class="membro-mapa-tooltip-inner">' +
        grupo
          .map(function (n) {
            return '<div class="membro-mapa-tooltip-nome">' + escapeHtml(n) + '</div>';
          })
          .join('') +
        '</div>'
      );
    }
    return escapeHtml(nomeFallback);
  }

  function init() {
    var mount = document.getElementById('membros-mapa-global');
    if (!mount || !window.L) return;

    var scriptEl = document.getElementById('membros-mapa-data');
    var markers = [];
    if (scriptEl) {
      try {
        markers = JSON.parse(scriptEl.textContent) || [];
      } catch (e) {
        markers = [];
      }
    }

    spreadOverlappingPins(markers);

    var map = L.map(mount, {
      scrollWheelZoom: true,
      attributionControl: true,
    });

    L.tileLayer(
      'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}.png',
      {
        attribution:
          '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> ' +
          '&copy; <a href="https://carto.com/attributions" rel="noopener">CARTO</a>',
        subdomains: 'abcd',
        maxZoom: 20,
      },
    ).addTo(map);

    var layerGroup = L.featureGroup();

    for (var i = 0; i < markers.length; i++) {
      var m = markers[i];
      var lat = m.lat;
      var lng = m.lng;
      if (typeof lat !== 'number' || typeof lng !== 'number') continue;

      var nome = (m.nome || '').trim() || '—';
      var foto = (m.foto || '').trim();
      var url = (m.url || '').trim();

      var inner;
      if (foto) {
        inner =
          '<div class="membro-mapa-pin-inner"><img src="' +
          escapeAttr(foto) +
          '" alt="" width="44" height="44" loading="lazy" decoding="async" /></div>';
      } else {
        var ini = nome.charAt(0) || '?';
        inner = '<div class="membro-mapa-pin-inner">' + escapeHtml(ini) + '</div>';
      }

      var icon = L.divIcon({
        className: 'membro-mapa-pin',
        html: inner,
        iconSize: [48, 56],
        iconAnchor: [24, 56],
        tooltipAnchor: [0, -52],
      });

      var marker = L.marker([lat, lng], { icon: icon }).addTo(layerGroup);

      var tooltipMulti = m.nomesGrupo && m.nomesGrupo.length > 1;
      marker.bindTooltip(buildTooltipHtml(m, nome), {
        permanent: false,
        direction: 'top',
        className: tooltipMulti
          ? 'membro-mapa-tooltip membro-mapa-tooltip--multi'
          : 'membro-mapa-tooltip',
        opacity: 1,
      });

      if (url) {
        marker.on('click', function (href) {
          return function () {
            window.location.href = href;
          };
        }(url));
      }
    }

    layerGroup.addTo(map);

    if (markers.length > 0) {
      try {
        map.fitBounds(layerGroup.getBounds().pad(0.12));
      } catch (e) {
        map.setView([-14.235, -51.9253], 4);
      }
    } else {
      map.setView([-14.235, -51.9253], 4);
    }

    window.setTimeout(function () {
      map.invalidateSize(true);
    }, 200);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
