(function () {
  function sortableButton(target) {
    return target && target.closest ? target.closest('.tesouraria-sort-btn') : null;
  }

  function tableRows(table) {
    var tbody = table && table.tBodies ? table.tBodies[0] : null;
    if (!tbody) return [];
    return Array.prototype.slice.call(tbody.querySelectorAll('tr[data-sortable-row]'));
  }

  function cellValue(row, index) {
    var cell = row.children[index];
    if (!cell) return '';
    return cell.getAttribute('data-sort-value') || cell.textContent.trim();
  }

  function numberValue(value) {
    var text = String(value || '').replace(/[^\d,.-]/g, '');
    if (text.indexOf(',') > -1 && text.lastIndexOf(',') > text.lastIndexOf('.')) {
      text = text.replace(/\./g, '').replace(',', '.');
    }
    var parsed = Number.parseFloat(text);
    return Number.isFinite(parsed) ? parsed : 0;
  }

  function compareValues(a, b, type) {
    if (type === 'number') return numberValue(a) - numberValue(b);
    return String(a || '').localeCompare(String(b || ''), 'pt-BR', {
      numeric: true,
      sensitivity: 'base',
    });
  }

  function resetSortState(table, activeButton, dir) {
    table.querySelectorAll('th[aria-sort]').forEach(function (th) {
      th.setAttribute('aria-sort', 'none');
    });
    table.querySelectorAll('.tesouraria-sort-btn').forEach(function (button) {
      button.classList.remove('is-asc', 'is-desc');
      if (button !== activeButton) button.removeAttribute('data-sort-dir');
    });

    var th = activeButton.closest('th');
    if (th) th.setAttribute('aria-sort', dir === 'asc' ? 'ascending' : 'descending');
    activeButton.setAttribute('data-sort-dir', dir);
    activeButton.classList.add(dir === 'asc' ? 'is-asc' : 'is-desc');
  }

  document.body.addEventListener('click', function (event) {
    var button = sortableButton(event.target);
    if (!button) return;

    var table = button.closest('table[data-tesouraria-sortable-table]');
    var th = button.closest('th');
    var rows = tableRows(table);
    if (!table || !th || !rows.length) return;

    event.preventDefault();
    event.stopPropagation();

    var index = Number(button.getAttribute('data-sort-index'));
    var type = button.getAttribute('data-sort-type') || 'text';
    var current = button.getAttribute('data-sort-dir');
    var next = current === 'asc' ? 'desc' : 'asc';

    rows.sort(function (rowA, rowB) {
      var result = compareValues(cellValue(rowA, index), cellValue(rowB, index), type);
      return next === 'asc' ? result : -result;
    });

    rows.forEach(function (row) {
      row.parentNode.appendChild(row);
    });
    resetSortState(table, button, next);
  });
})();
