(function () {
  var MAX_CENTS_DIGITS = 12;

  function onlyDigits(s) {
    return (s || '').replace(/\D/g, '');
  }

  function formatFromCentsDigits(digits) {
    if (!digits) return '';
    var cents = parseInt(digits, 10);
    if (!isFinite(cents) || cents < 0) return '';
    var intPart = String(Math.floor(cents / 100));
    var decPart = String(cents % 100).padStart(2, '0');
    intPart = intPart.replace(/\B(?=(\d{3})+(?!\d))/g, '.');
    return intPart + ',' + decPart;
  }

  function bind(el) {
    if (!el || el.dataset.tesourariaValorBrlBound) return;
    el.dataset.tesourariaValorBrlBound = '1';
    el.setAttribute('inputmode', 'numeric');
    el.setAttribute('autocomplete', 'off');

    el.addEventListener('input', function () {
      var d = onlyDigits(el.value);
      if (d.length > MAX_CENTS_DIGITS) d = d.slice(0, MAX_CENTS_DIGITS);
      el.value = formatFromCentsDigits(d);
    });

    el.addEventListener('blur', function () {
      var d = onlyDigits(el.value);
      el.value = d ? formatFromCentsDigits(d) : '';
    });
  }

  function scan(root) {
    (root || document).querySelectorAll('.js-tesouraria-valor-brl').forEach(bind);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', function () {
      scan(document);
    });
  } else {
    scan(document);
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (t && t.id === 'app-modal-content') scan(t);
  });
})();
