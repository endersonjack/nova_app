(function () {
  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (!t || !window.htmx) return;
    if (t.id === 'membro-detalhe-main' || t.id === 'membro-detalhe-topbar') {
      window.htmx.process(t);
    }
  });

})();
