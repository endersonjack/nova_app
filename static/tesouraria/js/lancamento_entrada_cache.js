(function () {
  var KEY = 'nova:tesouraria:lancamentoEntrada:dia';
  var TTL_MS = 12 * 60 * 60 * 1000;

  function formIsEntrada(form) {
    return form && form.getAttribute('data-tesouraria-entrada-form') === '1';
  }

  function dayInput(form) {
    return form ? form.querySelector('[name="dia"]') : null;
  }

  function parseStoredDay() {
    try {
      var raw = window.localStorage.getItem(KEY);
      if (!raw) return null;
      var data = JSON.parse(raw);
      if (!data || !data.expiresAt || Date.now() > data.expiresAt) {
        window.localStorage.removeItem(KEY);
        return null;
      }
      return data.value || null;
    } catch (err) {
      return null;
    }
  }

  function fitsInputRange(input, value) {
    var numberValue = Number(value);
    if (!Number.isFinite(numberValue)) return false;
    var min = input.min ? Number(input.min) : null;
    var max = input.max ? Number(input.max) : null;
    if (min !== null && numberValue < min) return false;
    if (max !== null && numberValue > max) return false;
    return true;
  }

  function restoreDay(form) {
    if (!formIsEntrada(form)) return;
    if (form.getAttribute('data-tesouraria-entrada-edit') === '1') return;
    if (form.getAttribute('data-tesouraria-entrada-bound') === '1') return;

    var input = dayInput(form);
    var cached = parseStoredDay();
    if (!input || !cached || !fitsInputRange(input, cached)) return;
    input.value = cached;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
  }

  function storeDay(form) {
    if (!formIsEntrada(form)) return;
    var input = dayInput(form);
    if (!input || !input.value || !fitsInputRange(input, input.value)) return;
    try {
      window.localStorage.setItem(
        KEY,
        JSON.stringify({
          value: input.value,
          expiresAt: Date.now() + TTL_MS,
        })
      );
    } catch (err) {
      // Sem localStorage disponível, o lançamento segue normalmente.
    }
  }

  document.body.addEventListener('htmx:afterSwap', function (event) {
    var target = event.detail && event.detail.target;
    if (!target || target.id !== 'app-modal-content') return;
    restoreDay(target.querySelector('[data-tesouraria-entrada-form="1"]'));
  });

  document.body.addEventListener('htmx:afterRequest', function (event) {
    var form = event.detail && event.detail.elt;
    var xhr = event.detail && event.detail.xhr;
    if (!formIsEntrada(form) || !xhr || xhr.status !== 204) return;
    storeDay(form);
  });
})();
