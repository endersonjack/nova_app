(function () {
  var DISMISS_KEY = 'nova:pwa-install-dismissed-at';
  var DISMISS_MS = 7 * 24 * 60 * 60 * 1000;
  var deferredPrompt = null;

  function isStandalone() {
    return window.matchMedia('(display-mode: standalone)').matches ||
      window.navigator.standalone === true;
  }

  function isMobile() {
    return window.matchMedia('(max-width: 991.98px)').matches;
  }

  function isIos() {
    return /iphone|ipad|ipod/i.test(window.navigator.userAgent);
  }

  function wasDismissed() {
    var raw;
    try {
      raw = window.localStorage.getItem(DISMISS_KEY);
    } catch (error) {
      return false;
    }
    if (!raw) return false;

    var time = Number(raw);
    return Number.isFinite(time) && Date.now() - time < DISMISS_MS;
  }

  function markDismissed() {
    try {
      window.localStorage.setItem(DISMISS_KEY, String(Date.now()));
    } catch (error) {
      // Local storage can be unavailable in private browsing.
    }
  }

  function getPrompt() {
    return document.getElementById('pwa-install-prompt');
  }

  function getText() {
    return document.getElementById('pwa-install-prompt-text');
  }

  function getAction() {
    return document.getElementById('pwa-install-action');
  }

  function showPrompt(options) {
    var prompt = getPrompt();
    var text = getText();
    var action = getAction();

    if (!prompt || !text || !action || isStandalone() || !isMobile() || wasDismissed()) {
      return;
    }

    text.textContent = options.text;
    action.textContent = options.actionText;
    prompt.hidden = false;
  }

  function hidePrompt(remember) {
    var prompt = getPrompt();
    if (prompt) prompt.hidden = true;
    if (remember) markDismissed();
  }

  function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return;

    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/service-worker.js').catch(function () {});
    });
  }

  function showIosHelp() {
    var message = 'No iPhone, toque em Compartilhar e depois em Adicionar a Tela de Inicio.';
    if (window.AppToast) {
      window.AppToast.show(message, { variant: 'info' });
    } else {
      window.alert(message);
    }
  }

  function wirePromptButtons() {
    var action = getAction();
    var close = document.getElementById('pwa-install-close');

    if (action) {
      action.addEventListener('click', function () {
        if (!deferredPrompt) {
          showIosHelp();
          return;
        }

        deferredPrompt.prompt();
        deferredPrompt.userChoice.finally(function () {
          deferredPrompt = null;
          hidePrompt(true);
        });
      });
    }

    if (close) {
      close.addEventListener('click', function () {
        hidePrompt(true);
      });
    }
  }

  registerServiceWorker();

  window.addEventListener('beforeinstallprompt', function (event) {
    event.preventDefault();
    deferredPrompt = event;
    showPrompt({
      text: 'Adicione o app a tela inicial do celular.',
      actionText: 'Instalar',
    });
  });

  window.addEventListener('appinstalled', function () {
    hidePrompt(true);
  });

  document.addEventListener('DOMContentLoaded', function () {
    wirePromptButtons();

    if (isIos() && !isStandalone()) {
      window.setTimeout(function () {
        showPrompt({
          text: 'No iPhone, toque em Compartilhar e em Adicionar a Tela de Inicio.',
          actionText: 'Como instalar',
        });
      }, 1200);
    }
  });
})();
