(function () {
  function formatCpf(digits) {
    var v = digits.replace(/\D/g, '').slice(0, 11);
    var p = '';
    if (v.length > 0) p += v.slice(0, 3);
    if (v.length > 3) p += '.' + v.slice(3, 6);
    if (v.length > 6) p += '.' + v.slice(6, 9);
    if (v.length > 9) p += '-' + v.slice(9, 11);
    return p;
  }

  function formatPhone(raw) {
    var v = raw.replace(/\D/g, '').slice(0, 11);
    if (v.length === 0) return '';
    if (v.length <= 2) return '(' + v + (v.length === 2 ? ')' : '');
    var rest = v.slice(2);
    var p = '(' + v.slice(0, 2) + ') ';
    if (v.length <= 10) {
      if (rest.length <= 4) return p + rest;
      return p + rest.slice(0, 4) + '-' + rest.slice(4, 8);
    }
    if (rest.length <= 5) return p + rest;
    return p + rest.slice(0, 5) + '-' + rest.slice(5, 9);
  }

  function bindCpf(el) {
    if (!el || el.dataset.cpfMaskBound) return;
    el.dataset.cpfMaskBound = '1';
    el.setAttribute('inputmode', 'numeric');
    el.setAttribute('autocomplete', 'off');
    el.addEventListener('input', function () {
      var cur = el.value;
      var pos = el.selectionStart;
      var before = cur.slice(0, pos).replace(/\D/g, '').length;
      el.value = formatCpf(cur);
      var newPos = el.value.length;
      var d = 0;
      for (var i = 0; i < el.value.length; i++) {
        if (/\d/.test(el.value[i])) {
          d++;
          if (d === before) {
            newPos = i + 1;
            break;
          }
        }
      }
      el.setSelectionRange(newPos, newPos);
    });
  }

  function bindTelefone(el) {
    if (!el || el.dataset.telefoneMaskBound) return;
    el.dataset.telefoneMaskBound = '1';
    el.setAttribute('inputmode', 'tel');
    el.setAttribute('autocomplete', 'tel');
    el.addEventListener('input', function () {
      var cur = el.value;
      var pos = el.selectionStart;
      var before = cur.slice(0, pos).replace(/\D/g, '').length;
      el.value = formatPhone(cur);
      var newPos = el.value.length;
      var d = 0;
      for (var i = 0; i < el.value.length; i++) {
        if (/\d/.test(el.value[i])) {
          d++;
          if (d === before) {
            newPos = i + 1;
            break;
          }
        }
      }
      el.setSelectionRange(newPos, newPos);
    });
  }

  function initMasks() {
    bindCpf(document.getElementById('id_cpf'));
    bindTelefone(document.getElementById('id_telefone'));
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMasks);
  } else {
    initMasks();
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (t && (t.id === 'app-modal-content' || t.id === 'membro-detalhe-main')) initMasks();
  });
})();
