(function () {
  var DEBOUNCE_MS = 280;
  var state = { timer: null, abort: null };

  function byId(id) {
    return document.getElementById(id);
  }

  function form() {
    return byId('relatorio-participante-form');
  }

  function input() {
    return byId('relatorio-participante-q');
  }

  function results() {
    return byId('relatorio-participante-results');
  }

  function tipoHidden() {
    return byId('relatorio-participante-tipo');
  }

  function idHidden() {
    return byId('relatorio-participante-id');
  }

  function clearPending() {
    if (state.timer !== null) {
      clearTimeout(state.timer);
      state.timer = null;
    }
    if (state.abort) {
      state.abort.abort();
      state.abort = null;
    }
  }

  function clearSelection() {
    var t = tipoHidden();
    var id = idHidden();
    var q = input();
    var r = results();
    if (t) t.value = '';
    if (id) id.value = '';
    if (q) q.value = '';
    if (r) r.innerHTML = '';
  }

  function runAutocomplete(qInput) {
    var url = qInput.getAttribute('data-relatorio-participante-autocomplete-url') || '';
    var r = results();
    if (!url || !r) return;

    clearPending();
    var q = (qInput.value || '').trim();
    state.timer = setTimeout(function () {
      state.timer = null;
      state.abort = new AbortController();
      var params = new URLSearchParams();
      params.set('tesouraria_membro_q', q);
      r.innerHTML = '<p class="text-muted small mb-0 px-3 py-2">...</p>';

      fetch(url + '?' + params.toString(), {
        method: 'GET',
        credentials: 'same-origin',
        signal: state.abort.signal,
        headers: { Accept: 'text/html' },
      })
        .then(function (response) {
          if (!response.ok) throw new Error('autocomplete http ' + response.status);
          return response.text();
        })
        .then(function (html) {
          r.innerHTML = html;
        })
        .catch(function (err) {
          if (err.name === 'AbortError') return;
          r.innerHTML = '<p class="text-danger small mb-0 px-3 py-2">Erro ao buscar membro ou visitante.</p>';
        })
        .finally(function () {
          state.abort = null;
        });
    }, DEBOUNCE_MS);
  }

  document.body.addEventListener('input', function (event) {
    if (event.target !== input()) return;
    var t = tipoHidden();
    var id = idHidden();
    if (t) t.value = '';
    if (id) id.value = '';
    runAutocomplete(event.target);
  });

  document.body.addEventListener('click', function (event) {
    if (event.target.closest('#relatorio-participante-clear')) {
      event.preventDefault();
      clearPending();
      clearSelection();
      return;
    }

    var pick = event.target.closest('.js-autocomplete-pick');
    var r = results();
    if (!pick || !r || !r.contains(pick)) return;
    event.preventDefault();

    var tipo = pick.getAttribute('data-participante-tipo') || '';
    var id = pick.getAttribute('data-participante-id') || '';
    var label = (pick.getAttribute('data-participante-label') || '').split(' —')[0].trim();
    if (tipoHidden()) tipoHidden().value = tipo;
    if (idHidden()) idHidden().value = id;
    if (input()) input().value = label;
    r.innerHTML = '';
    if (form()) form().submit();
  });
})();
