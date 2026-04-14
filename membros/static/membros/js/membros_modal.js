(function () {
  function clearHost(host) {
    if (host) host.innerHTML = '';
  }

  function updateFilhoCancelState() {
    var container = document.getElementById('filhos-rows-container');
    var cancel = document.getElementById('js-filho-cancel');
    if (!container || !cancel) return;
    var n = container.querySelectorAll('.js-filho-row').length;
    cancel.disabled = n <= 1;
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (t && (t.id === 'app-modal-content' || t.id === 'membro-detalhe-main'))
      updateFilhoCancelState();
  });

  document.body.addEventListener('click', function (e) {
    var pick = e.target.closest('.js-autocomplete-pick');
    if (pick) {
      e.preventDefault();
      var id = pick.getAttribute('data-membro-id');
      var label = pick.getAttribute('data-membro-label') || '';
      var host = pick.closest('.js-autocomplete-host');
      if (!host) return;

      if (host.id === 'casado_com_results') {
        var hid = document.getElementById('id_casado_com');
        var inp = document.getElementById('casado_com_search');
        if (hid) hid.value = id;
        if (inp) inp.value = label;
        clearHost(host);
        return;
      }

      var row = pick.closest('.js-filho-row');
      if (row) {
        var hidden = row.querySelector('.js-filho-hidden');
        var search = row.querySelector('.js-filho-search');
        if (hidden) hidden.value = id;
        if (search) search.value = label;
        clearHost(host);
      }
      return;
    }

    var cancel = e.target.closest('#js-filho-cancel');
    if (cancel) {
      e.preventDefault();
      var container = document.getElementById('filhos-rows-container');
      if (!container) return;
      var rows = container.querySelectorAll('.js-filho-row');
      if (rows.length <= 1) return;
      rows[rows.length - 1].remove();
      updateFilhoCancelState();
      return;
    }

    var add = e.target.closest('#js-filho-add');
    if (!add) return;
    e.preventDefault();
    var container = document.getElementById('filhos-rows-container');
    if (!container) return;
    var rows = container.querySelectorAll('.js-filho-row');
    var last = rows[rows.length - 1];
    if (!last) return;
    var idx = rows.length;
    var clone = last.cloneNode(true);
    clone.setAttribute('data-idx', String(idx));

    var hid = clone.querySelector('.js-filho-hidden');
    var search = clone.querySelector('.js-filho-search');
    var res = clone.querySelector('.js-autocomplete-host');
    if (hid) {
      hid.id = 'filho_hidden_' + idx;
      hid.value = '';
    }
    if (search) {
      search.id = 'filho_search_' + idx;
      search.value = '';
      search.setAttribute('hx-target', '#filho_results_' + idx);
      search.setAttribute(
        'hx-vals',
        "js:{q: document.getElementById('filho_search_" +
          idx +
          "').value, exclude: document.getElementById('autocomplete_exclude').value}"
      );
    }
    if (res) {
      res.id = 'filho_results_' + idx;
      res.innerHTML = '';
    }
    container.appendChild(clone);
    if (window.htmx) window.htmx.process(clone);
    updateFilhoCancelState();
  });
})();
