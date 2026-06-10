(function () {
  function refreshLista() {
    var w = document.getElementById('visitante-lista-wrap');
    if (w && window.htmx) {
      window.htmx.trigger(w, 'refresh');
    }
  }

  document.body.addEventListener('visitantesListaRefresh', refreshLista);

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail.target;
    if (t && t.id === 'visitante-lista-wrap') {
      var base = t.getAttribute('data-lista-url');
      if (base) {
        var root = t.querySelector('.visitante-lista-root');
        var qs = root && root.getAttribute('data-list-query');
        t.setAttribute('hx-get', qs ? base + '?' + qs : base);
      }
    }
  });
})();
