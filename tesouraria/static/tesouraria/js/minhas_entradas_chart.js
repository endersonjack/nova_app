(function () {
  function destroyIfAny(el) {
    if (!el || !el._novaChart) return;
    try {
      el._novaChart.destroy();
    } catch (e) {
      /* ignore */
    }
    el._novaChart = null;
  }

  function moeda(value) {
    var n = Number(value || 0);
    return n.toLocaleString('pt-BR', {
      style: 'currency',
      currency: 'BRL',
    });
  }

  function mountMinhasEntradasChart() {
    var el = document.getElementById('minhasEntradasChart');
    var script = document.getElementById('minhas-entradas-chart-data');
    if (!el || !script || !window.Chart) return;
    destroyIfAny(el);
    var payload;
    try {
      payload = JSON.parse(script.textContent);
    } catch (e) {
      return;
    }
    if (!payload || !payload.labels || !payload.values) return;
    el._novaChart = new Chart(el, {
      type: 'line',
      data: {
        labels: payload.labels,
        datasets: [
          {
            label: 'Entradas',
            data: payload.values,
            borderColor: '#2563eb',
            backgroundColor: 'rgba(37, 99, 235, 0.12)',
            pointBackgroundColor: '#ffffff',
            pointBorderColor: '#2563eb',
            pointBorderWidth: 2,
            pointRadius: 4,
            pointHoverRadius: 5,
            fill: true,
            tension: 0.35,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: 'index', intersect: false },
        scales: {
          x: {
            grid: { display: false },
            ticks: { color: '#64748b', font: { size: 11, weight: 700 } },
          },
          y: {
            beginAtZero: true,
            grid: { color: 'rgba(148, 163, 184, 0.22)' },
            ticks: {
              color: '#64748b',
              callback: function (value) {
                return moeda(value);
              },
            },
          },
        },
        plugins: {
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: function (ctx) {
                return 'Entradas: ' + moeda(ctx.parsed.y);
              },
            },
          },
        },
      },
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', mountMinhasEntradasChart);
  } else {
    mountMinhasEntradasChart();
  }

  document.body.addEventListener('htmx:afterSwap', function (evt) {
    var t = evt.detail && evt.detail.target;
    if (!t) return;
    if (
      t.id === 'minhas-entradas-table-wrap' ||
      t.id === 'minhas-entradas-chart-card'
    ) {
      window.requestAnimationFrame(mountMinhasEntradasChart);
    }
  });

  window.mountMinhasEntradasChart = mountMinhasEntradasChart;
})();
