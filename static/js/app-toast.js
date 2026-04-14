(function (global) {
  var DEFAULT_DURATION = 5000;

  var VARIANTS = {
    success: { className: 'app-toast--success', icon: 'bi-check-circle-fill' },
    danger: { className: 'app-toast--danger', icon: 'bi-exclamation-octagon-fill' },
    warning: { className: 'app-toast--warning', icon: 'bi-exclamation-triangle-fill' },
    info: { className: 'app-toast--info', icon: 'bi-info-circle-fill' },
  };

  function escapeHtml(s) {
    var d = document.createElement('div');
    d.textContent = s == null ? '' : String(s);
    return d.innerHTML;
  }

  function show(message, options) {
    options = options || {};
    var variant = options.variant || 'info';
    var duration =
      options.duration === undefined || options.duration === null
        ? DEFAULT_DURATION
        : options.duration;
    var v = VARIANTS[variant] || VARIANTS.info;
    var container = document.getElementById('app-toast-container');
    if (!container) return;

    var el = document.createElement('div');
    el.className = 'app-toast ' + v.className;
    el.setAttribute('role', 'status');

    el.innerHTML =
      '<div class="app-toast__inner">' +
      '<i class="bi ' +
      v.icon +
      ' app-toast__icon" aria-hidden="true"></i>' +
      '<div class="app-toast__body">' +
      escapeHtml(message) +
      '</div>' +
      '<button type="button" class="btn-close app-toast__close" aria-label="Fechar"></button>' +
      '</div>';

    var timer;
    function removeToast() {
      if (timer) clearTimeout(timer);
      el.classList.add('app-toast--leave');
      window.setTimeout(function () {
        if (el.parentNode) el.parentNode.removeChild(el);
      }, 220);
    }

    el.querySelector('.app-toast__close').addEventListener('click', removeToast);
    if (duration > 0) timer = window.setTimeout(removeToast, duration);

    container.appendChild(el);
    window.requestAnimationFrame(function () {
      el.classList.add('app-toast--show');
    });
  }

  global.AppToast = { show: show };

  /**
   * HTMX: cabeçalho HX-Trigger como JSON, ex.:
   * { "appToast": { "message": "Salvo.", "variant": "success" } }
   * O HTMX dispara o evento nomeado com o objeto em detail.
   */
  document.body.addEventListener('appToast', function (e) {
    var d = e.detail;
    if (d == null) return;
    if (typeof d === 'string') {
      show(d, {});
      return;
    }
    if (d.message != null) {
      show(d.message, {
        variant: d.variant,
        duration: d.duration,
      });
    }
  });
})(window);
