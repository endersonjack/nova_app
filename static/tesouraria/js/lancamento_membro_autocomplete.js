(function () {
  var DEBOUNCE_MS = 280;
  var state = { timer: null, abort: null };

  function membroHidden() {
    return document.querySelector('#form-lancamento-entrada #id_membro');
  }

  function membroSearch() {
    return document.getElementById('lancamento-membro-q');
  }

  function membroResults() {
    return document.getElementById('lancamento-membro-results');
  }

  function autocompleteUrl(input) {
    return (input && input.getAttribute('data-tesouraria-membro-autocomplete-url')) || '';
  }

  function clearMembro() {
    var h = membroHidden();
    var q = membroSearch();
    var r = membroResults();
    if (h) h.value = '';
    if (q) q.value = '';
    if (r) r.innerHTML = '';
  }

  function cancelPendingAutocomplete() {
    if (state.timer !== null) {
      clearTimeout(state.timer);
      state.timer = null;
    }
    if (state.abort) {
      state.abort.abort();
      state.abort = null;
    }
  }

  function runAutocomplete(input) {
    var url = autocompleteUrl(input);
    var results = membroResults();
    if (!url || !results) return;

    cancelPendingAutocomplete();

    var q = (input.value || '').trim();
    state.timer = setTimeout(function () {
      state.timer = null;
      state.abort = new AbortController();
      var signal = state.abort.signal;
      var params = new URLSearchParams();
      params.set('tesouraria_membro_q', q);
      results.innerHTML =
        '<p class="text-muted small mb-0 px-3 py-2">…</p>';

      fetch(url + '?' + params.toString(), {
        method: 'GET',
        credentials: 'same-origin',
        signal: signal,
        headers: { Accept: 'text/html' },
      })
        .then(function (r) {
          if (!r.ok) throw new Error('autocomplete http ' + r.status);
          return r.text();
        })
        .then(function (html) {
          results.innerHTML = html;
        })
        .catch(function (err) {
          if (err.name === 'AbortError') return;
          results.innerHTML =
            '<p class="text-danger small mb-0 px-3 py-2">Erro ao buscar membros.</p>';
        })
        .finally(function () {
          state.abort = null;
        });
    }, DEBOUNCE_MS);
  }

  document.body.addEventListener('input', function (e) {
    var t = e.target;
    if (!t || t.id !== 'lancamento-membro-q') return;
    var modal = document.getElementById('appModal');
    if (!modal || !modal.contains(t)) return;
    runAutocomplete(t);
  });

  document.body.addEventListener('click', function (e) {
    var modal = document.getElementById('appModal');
    if (!modal || !modal.contains(e.target)) return;

    if (e.target.closest('#lancamento-membro-clear')) {
      e.preventDefault();
      cancelPendingAutocomplete();
      clearMembro();
      return;
    }

    var pick = e.target.closest('.js-autocomplete-pick');
    if (!pick || !modal.contains(pick)) return;
    e.preventDefault();
    var id = pick.getAttribute('data-membro-id');
    var label = (pick.getAttribute('data-membro-label') || '').trim();
    var h = membroHidden();
    var q = membroSearch();
    var r = membroResults();
    if (h) h.value = id || '';
    if (q) {
      var shortLabel = label.split(' —')[0].trim();
      q.value = shortLabel || label;
    }
    if (r) r.innerHTML = '';
  });

  var appModalEl = document.getElementById('appModal');
  if (appModalEl) {
    appModalEl.addEventListener('hidden.bs.modal', function () {
      cancelPendingAutocomplete();
    });
  }
})();
