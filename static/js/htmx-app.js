(function () {
  function getCookie(name) {
    var m = document.cookie.match(new RegExp('(^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[2]) : '';
  }

  document.body.addEventListener('htmx:configRequest', function (event) {
    var token = getCookie('csrftoken');
    if (token) {
      event.detail.headers['X-CSRFToken'] = token;
    }
  });

  document.body.addEventListener('htmx:beforeSwap', function (evt) {
    var status = evt.detail.xhr.status;
    if (status === 422) {
      evt.detail.shouldSwap = true;
    }
    if (status === 204) {
      evt.detail.shouldSwap = false;
    }
  });

  function appModalApplySize(modalContent) {
    var dlg = document.getElementById('app-modal-dialog');
    if (!dlg || !modalContent) return;
    var isSm = modalContent.querySelector('[data-app-modal-size="sm"]');
    dlg.classList.remove(
      'modal-xl',
      'modal-sm',
      'modal-lg',
      'modal-dialog-scrollable',
      'app-modal-dialog--novo'
    );
    if (isSm) {
      dlg.classList.add('app-modal-dialog--novo');
    } else {
      dlg.classList.add('modal-xl', 'modal-dialog-scrollable');
    }
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail.target;
    if (t && t.id === 'app-modal-content') {
      appModalApplySize(t);
      var el = document.getElementById('appModal');
      if (el) {
        window.bootstrap.Modal.getOrCreateInstance(el).show();
      }
    }
    if (t && t.id === 'membro-lista-wrap') {
      var base = t.getAttribute('data-lista-url');
      if (base) {
        var root = t.querySelector('.membro-lista-root');
        var qs = root && root.getAttribute('data-list-query');
        t.setAttribute('hx-get', qs ? base + '?' + qs : base);
      }
    }
  });

  var appModalEl = document.getElementById('appModal');
  if (appModalEl) {
    appModalEl.addEventListener('hidden.bs.modal', function () {
      var dlg = document.getElementById('app-modal-dialog');
      if (dlg) {
        dlg.classList.remove('modal-sm', 'modal-lg', 'app-modal-dialog--novo');
        dlg.classList.add('modal-xl', 'modal-dialog-scrollable');
      }
    });
  }

  document.body.addEventListener('appModalHide', function () {
    var el = document.getElementById('appModal');
    if (el) {
      var inst = window.bootstrap.Modal.getInstance(el);
      if (inst) inst.hide();
    }
  });

  document.body.addEventListener('membrosListaRefresh', function () {
    var w = document.getElementById('membro-lista-wrap');
    if (w && window.htmx) {
      window.htmx.trigger(w, 'refresh');
    }
  });
})();
