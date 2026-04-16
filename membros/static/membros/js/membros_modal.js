(function () {
  function updateFilhoCancelState() {
    var container = document.getElementById('filhos-rows-container');
    var cancel = document.getElementById('js-filho-cancel');
    if (!container || !cancel) return;
    var n = container.querySelectorAll('.js-filho-row').length;
    cancel.disabled = n <= 1;
  }

  function familiaConjugeSync(est, wrap) {
    if (!est || !wrap) return;
    var conj = wrap.querySelector('.js-familia-casado-com-select');
    var dateInput = document.getElementById('id_data_casamento');
    if (!conj || !dateInput) return;
    var ok = est.value === 'casado';
    var shells = wrap.querySelectorAll('.membro-field-shell');
    var shellCasado = shells[0];
    var shellDate = shells[1];
    if (ok) {
      dateInput.removeAttribute('readonly');
      dateInput.classList.remove('bg-light', 'text-muted');
      if (shellCasado) shellCasado.classList.remove('bg-light', 'bg-opacity-50');
      if (shellDate) shellDate.classList.remove('bg-light', 'bg-opacity-50');
      conj.disabled = false;
    } else {
      conj.value = '';
      conj.disabled = true;
      dateInput.value = '';
      dateInput.setAttribute('readonly', 'readonly');
      dateInput.classList.add('bg-light', 'text-muted');
      if (shellCasado) shellCasado.classList.add('bg-light', 'bg-opacity-50');
      if (shellDate) shellDate.classList.add('bg-light', 'bg-opacity-50');
    }
  }

  function familiaConjugeBind(root) {
    var est = root.querySelector('#id_estado_civil');
    var wrap = root.querySelector('#js-familia-conjuge-fields');
    var form = root.querySelector('form.membro-secao-form');
    if (!est || !wrap) return;
    var initial = true;
    function onChange() {
      var prev = est.getAttribute('data-prev-estado');
      var v = est.value;
      familiaConjugeSync(est, wrap);
      var cb = form && form.querySelector('#id_adicionar_filhos_conjuge');
      if (cb) {
        if (v === 'casado') {
          cb.disabled = false;
          if (!initial && prev != 'casado') {
            cb.checked = true;
          }
        } else {
          cb.checked = false;
          cb.disabled = true;
        }
      }
      est.setAttribute('data-prev-estado', v);
      initial = false;
    }
    if (est._conjugeFamiliaChange) {
      est.removeEventListener('change', est._conjugeFamiliaChange);
    }
    est._conjugeFamiliaChange = onChange;
    est.addEventListener('change', onChange);
    onChange();
  }

  function scheduleFamiliaConjugeBind(root) {
    if (!root || !root.querySelector('#js-familia-conjuge-fields')) return;
    var modal = document.getElementById('appModal');
    function run() {
      familiaConjugeBind(root);
    }
    if (modal && modal.classList.contains('show')) {
      window.setTimeout(run, 50);
    } else if (modal) {
      function onShown() {
        modal.removeEventListener('shown.bs.modal', onShown);
        window.setTimeout(run, 50);
      }
      modal.addEventListener('shown.bs.modal', onShown);
    } else {
      window.setTimeout(run, 0);
    }
  }

  document.body.addEventListener('htmx:configRequest', function (evt) {
    var form = evt.detail && evt.detail.elt;
    if (!form || !form.classList || !form.classList.contains('membro-secao-form'))
      return;
    var est = form.querySelector('#id_estado_civil');
    var conj = form.querySelector('.js-familia-casado-com-select');
    if (!est || !conj) return;
    if (est.value === 'casado') {
      conj.disabled = false;
    }
    var filhosCb = form.querySelector('#id_adicionar_filhos_conjuge');
    if (filhosCb && est.value === 'casado') {
      filhosCb.disabled = false;
    }
  });

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (!t) return;
    if (t.id === 'app-modal-content' || t.id === 'membro-detalhe-main')
      updateFilhoCancelState();
    if (t.id === 'app-modal-content') scheduleFamiliaConjugeBind(t);
  });

  document.body.addEventListener('click', function (e) {
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

    var sel = clone.querySelector('.js-filho-select');
    if (sel) {
      sel.id = 'filho_select_' + idx;
      sel.value = '';
    }
    container.appendChild(clone);
    updateFilhoCancelState();
  });
})();
