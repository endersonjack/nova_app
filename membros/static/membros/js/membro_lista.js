(function () {
  function getModal() {
    return document.getElementById('membro-lista-map-modal');
  }

  function getMapEl() {
    return document.getElementById('membro-lista-map-mount');
  }

  function openMapModal(btn) {
    var modal = getModal();
    var mapEl = getMapEl();
    var titleEl = document.getElementById('membro-lista-map-modal-label');
    if (!modal || !mapEl || !window.bootstrap) return;

    var lat = (btn.getAttribute('data-lat') || '').trim();
    var lng = (btn.getAttribute('data-lng') || '').trim();
    var foto = (btn.getAttribute('data-foto-url') || '').trim();
    var nome = (btn.getAttribute('data-membro-nome') || '').trim();

    if (!lat || !lng) return;

    if (titleEl) {
      titleEl.textContent = nome ? 'Local no mapa — ' + nome : 'Local no mapa';
    }

    if (window.membroLocalidadeMapTeardown) {
      window.membroLocalidadeMapTeardown(modal);
    }

    mapEl.dataset.lat = lat;
    mapEl.dataset.lng = lng;
    if (foto) mapEl.dataset.fotoUrl = foto;
    else delete mapEl.dataset.fotoUrl;
    if (nome) mapEl.dataset.membroNome = nome;
    else delete mapEl.dataset.membroNome;

    var inst = window.bootstrap.Modal.getOrCreateInstance(modal);
    inst.show();
  }

  function rowNavUrl(tr) {
    var u = tr && tr.getAttribute('data-href');
    return (u || '').trim();
  }

  document.addEventListener('DOMContentLoaded', function () {
    var modal = getModal();
    var mapEl = getMapEl();
    if (modal && mapEl) {
      modal.addEventListener('shown.bs.modal', function () {
        if (window.membroLocalidadeMapScan) {
          window.membroLocalidadeMapScan(modal);
        }
      });

      modal.addEventListener('hidden.bs.modal', function () {
        if (window.membroLocalidadeMapTeardown) {
          window.membroLocalidadeMapTeardown(modal);
        }
      });
    }

    document.body.addEventListener('click', function (e) {
      var btn = e.target && e.target.closest('.membro-lista-map-btn--ok');
      if (btn && !btn.disabled) {
        e.preventDefault();
        e.stopPropagation();
        openMapModal(btn);
        return;
      }

      var tr = e.target && e.target.closest('.membro-lista-row');
      if (!tr) return;
      if (e.target.closest('[data-no-row-nav]')) return;
      if (e.target.closest('button')) return;
      var url = rowNavUrl(tr);
      if (url) window.location.href = url;
    });

    document.body.addEventListener('keydown', function (e) {
      if (e.key !== 'Enter' && e.key !== ' ') return;
      var tr = e.target && e.target.closest('.membro-lista-row');
      if (!tr || tr !== e.target) return;
      e.preventDefault();
      var url = rowNavUrl(tr);
      if (url) window.location.href = url;
    });
  });
})();
