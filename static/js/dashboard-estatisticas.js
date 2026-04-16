(function () {
  function parseCount(s) {
    var n = parseInt(s, 10);
    return Number.isFinite(n) ? n : 0;
  }

  function destroyIfAny(el) {
    if (!el || !el._novaChart) return;
    try {
      el._novaChart.destroy();
    } catch (e) {
      /* ignore */
    }
    el._novaChart = null;
  }

  function mountPieSexo() {
    var el = document.getElementById('dashboardChartSexo');
    if (!el || !window.Chart) return;
    destroyIfAny(el);
    var m = parseCount(el.getAttribute('data-membros-m'));
    var f = parseCount(el.getAttribute('data-membros-f'));
    if (m === 0 && f === 0) return;
    el._novaChart = new Chart(el, {
      type: 'pie',
      data: {
        labels: ['Masculino', 'Feminino'],
        datasets: [
          {
            data: [m, f],
            backgroundColor: ['#2563eb', '#db2777'],
            borderWidth: 2,
            borderColor: '#ffffff',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: { usePointStyle: true, padding: 16, font: { size: 13 } },
          },
        },
      },
    });
    window.setTimeout(function () {
      if (el._novaChart) el._novaChart.resize();
    }, 100);
  }

  function mountPieLocomocao() {
    var el = document.getElementById('dashboardChartLocomocao');
    if (!el || !window.Chart) return;
    destroyIfAny(el);
    var scriptEl = document.getElementById('dashboard-locomocao-data');
    if (!scriptEl) return;
    var payload;
    try {
      payload = JSON.parse(scriptEl.textContent);
    } catch (e) {
      return;
    }
    if (
      !payload ||
      !payload.labels ||
      !payload.counts ||
      !payload.colors ||
      payload.labels.length === 0
    ) {
      return;
    }
    el._novaChart = new Chart(el, {
      type: 'pie',
      data: {
        labels: payload.labels,
        datasets: [
          {
            data: payload.counts,
            backgroundColor: payload.colors,
            borderWidth: 2,
            borderColor: '#ffffff',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              usePointStyle: true,
              padding: 10,
              font: { size: 11 },
              boxWidth: 10,
            },
          },
        },
      },
    });
    window.setTimeout(function () {
      if (el._novaChart) el._novaChart.resize();
    }, 100);
  }

  function mountPieIdade() {
    var el = document.getElementById('dashboardChartIdade');
    if (!el || !window.Chart) return;
    destroyIfAny(el);
    var scriptEl = document.getElementById('dashboard-idade-data');
    if (!scriptEl) return;
    var payload;
    try {
      payload = JSON.parse(scriptEl.textContent);
    } catch (e) {
      return;
    }
    if (
      !payload ||
      !payload.labels ||
      !payload.counts ||
      !payload.colors ||
      payload.labels.length === 0
    ) {
      return;
    }
    el._novaChart = new Chart(el, {
      type: 'pie',
      data: {
        labels: payload.labels,
        datasets: [
          {
            data: payload.counts,
            backgroundColor: payload.colors,
            borderWidth: 2,
            borderColor: '#ffffff',
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: true,
        plugins: {
          legend: {
            position: 'bottom',
            labels: {
              usePointStyle: true,
              padding: 10,
              font: { size: 11 },
              boxWidth: 10,
            },
          },
        },
      },
    });
    window.setTimeout(function () {
      if (el._novaChart) el._novaChart.resize();
    }, 100);
  }

  function scheduleMount() {
    window.requestAnimationFrame(function () {
      mountPieSexo();
      mountPieIdade();
      mountPieLocomocao();
    });
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (!t || t.id !== 'dashboard-estatistica-wrap') return;
    scheduleMount();
  });

  window.setTimeout(function () {
    if (
      document.getElementById('dashboardChartSexo') ||
      document.getElementById('dashboardChartIdade') ||
      document.getElementById('dashboardChartLocomocao')
    ) {
      scheduleMount();
    }
  }, 0);

  window.mountDashboardEstatisticaCharts = scheduleMount;
})();
