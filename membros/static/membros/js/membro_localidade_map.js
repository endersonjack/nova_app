(function () {
  function parseCoord(s) {
    if (s == null || s === '') return NaN;
    var t = String(s).trim();
    if (t.indexOf('.') >= 0) {
      t = t.replace(/,/g, '');
    } else {
      t = t.replace(',', '.');
    }
    return parseFloat(t);
  }

  function escapeAttr(s) {
    return String(s)
      .replace(/&/g, '&amp;')
      .replace(/"/g, '&quot;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;');
  }

  function destroyMap(el) {
    if (!el || !el._membroLeafletMap) return;
    try {
      el._membroLeafletMap.remove();
    } catch (e) {
      /* ignore */
    }
    el._membroLeafletMap = null;
  }

  function initMount(el) {
    if (!el || !window.L) return;
    var lat = parseCoord(el.dataset.lat);
    var lng = parseCoord(el.dataset.lng);
    if (Number.isNaN(lat) || Number.isNaN(lng)) return;

    destroyMap(el);

    var map = L.map(el, {
      scrollWheelZoom: false,
      attributionControl: true,
    }).setView([lat, lng], 16);

    /* Carto CDN: dados OSM; não exige Referer como tile.openstreetmap.org (evita 403). */
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

    var foto = (el.dataset.fotoUrl || '').trim();
    var marker;
    if (foto) {
      var html =
        '<div class="membro-map-pin-inner"><img src="' +
        escapeAttr(foto) +
        '" alt="" width="44" height="44" loading="lazy" decoding="async" /></div>';
      var icon = L.divIcon({
        className: 'membro-map-pin',
        html: html,
        iconSize: [48, 56],
        iconAnchor: [24, 56],
        popupAnchor: [0, -52],
      });
      marker = L.marker([lat, lng], { icon: icon }).addTo(map);
    } else {
      marker = L.marker([lat, lng]).addTo(map);
    }

    var nome = (el.dataset.membroNome || '').trim();
    if (nome) {
      marker.bindPopup(escapeAttr(nome));
    }

    el._membroLeafletMap = map;

    window.setTimeout(function () {
      if (el._membroLeafletMap) {
        el._membroLeafletMap.invalidateSize(true);
      }
    }, 150);
  }

  function teardown(root) {
    if (!root) return;
    var mounts = root.querySelectorAll('.membro-localidade-map--mount');
    for (var i = 0; i < mounts.length; i++) {
      destroyMap(mounts[i]);
    }
  }

  function scan(root) {
    if (!root || !window.L) return;
    var mounts = root.querySelectorAll('.membro-localidade-map--mount');
    for (var i = 0; i < mounts.length; i++) {
      initMount(mounts[i]);
    }
  }

  window.membroLocalidadeMapScan = scan;
  window.membroLocalidadeMapTeardown = teardown;

  document.addEventListener('DOMContentLoaded', function () {
    var main = document.getElementById('membro-detalhe-main');
    if (main) scan(main);
  });

  document.body.addEventListener('htmx:beforeSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (t && t.id === 'membro-detalhe-main') {
      teardown(t);
    }
  });

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (!t || t.id !== 'membro-detalhe-main') return;
    scan(t);
  });
})();
