(function () {
  var STORAGE_KEY = 'nova.sidebarCollapsed';
  var shell = document.getElementById('appShell');
  var trigger = document.getElementById('app-sidebar-user-trigger');
  if (!shell || !trigger) return;

  function isDesktopSidebar() {
    return window.matchMedia('(min-width: 992px)').matches;
  }

  function apply(collapsed) {
    if (!isDesktopSidebar()) {
      shell.classList.remove('sidebar-collapsed');
      trigger.setAttribute('aria-expanded', 'true');
      trigger.setAttribute('aria-label', 'Recolher menu lateral');
      trigger.setAttribute('title', 'Recolher menu');
      return;
    }
    shell.classList.toggle('sidebar-collapsed', collapsed);
    trigger.setAttribute('aria-expanded', collapsed ? 'false' : 'true');
    trigger.setAttribute(
      'aria-label',
      collapsed ? 'Expandir menu lateral' : 'Recolher menu lateral'
    );
    trigger.setAttribute('title', collapsed ? 'Expandir menu' : 'Recolher menu');
    try {
      localStorage.setItem(STORAGE_KEY, collapsed ? '1' : '0');
    } catch (e) {}
  }

  try {
    if (isDesktopSidebar() && localStorage.getItem(STORAGE_KEY) === '1') {
      apply(true);
    }
  } catch (e) {}

  trigger.addEventListener('click', function () {
    if (!isDesktopSidebar()) return;
    apply(!shell.classList.contains('sidebar-collapsed'));
  });

  window.addEventListener('resize', function () {
    if (!isDesktopSidebar()) {
      shell.classList.remove('sidebar-collapsed');
      trigger.setAttribute('aria-expanded', 'true');
      trigger.setAttribute('aria-label', 'Recolher menu lateral');
      trigger.setAttribute('title', 'Recolher menu');
      return;
    }
    try {
      var c = localStorage.getItem(STORAGE_KEY) === '1';
      shell.classList.toggle('sidebar-collapsed', c);
      trigger.setAttribute('aria-expanded', c ? 'false' : 'true');
      trigger.setAttribute(
        'aria-label',
        c ? 'Expandir menu lateral' : 'Recolher menu lateral'
      );
      trigger.setAttribute('title', c ? 'Expandir menu' : 'Recolher menu');
    } catch (e) {}
  });
})();
