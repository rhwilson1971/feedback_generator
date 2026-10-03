/**
 * Populate rank choices for a scale. Restore an existing rank once, then reset
 * it whenever the scale changes. Text content keeps user-authored labels safe.
 */
function initRankSelector(scaleSelect, rankSelect, scales, filterMode = false) {
  if (!scaleSelect || !rankSelect) return;
  const doc = rankSelect.ownerDocument;

  /** Rebuild choices for the selected scale and restore a valid rank when supplied. */
  function populate(selected = '') {
    const scale = scales.find(s => s.id === scaleSelect.value);
    rankSelect.replaceChildren();
    const placeholder = doc.createElement('option');
    placeholder.value = '';
    placeholder.textContent = filterMode ? 'All ranks' : 'Choose a rank…';
    rankSelect.appendChild(placeholder);
    for (const rank of scale ? scale.ranks : []) {
      const option = doc.createElement('option');
      option.value = String(rank.id);
      option.textContent = `${rank.id} — ${rank.description}`;
      rankSelect.appendChild(option);
    }
    rankSelect.disabled = !scale;
    rankSelect.required = Boolean(scale) && !filterMode;
    rankSelect.value = selected;
    if (rankSelect.selectedIndex < 0) rankSelect.value = '';
  }

  populate(rankSelect.value);
  scaleSelect.addEventListener('change', () => {
    populate();
    rankSelect.dispatchEvent(new doc.defaultView.Event('change', { bubbles: true }));
  });
}

/** Add/remove rank rows while retaining one row and accessible unique labels. */
function initRankRows(doc = document, confirmFn = message => doc.defaultView.confirm(message)) {
  const rows = doc.getElementById('rankRows');
  const add = doc.getElementById('addRank');
  const template = doc.getElementById('rankRowTemplate');
  if (!rows || !add || !template) return;
  let serial = 0;

  /** Associate row labels with unique input IDs and prevent removing the last row. */
  function updateRows() {
    const current = rows.querySelectorAll('.rank-row');
    current.forEach((row, index) => {
      const inputs = row.querySelectorAll('input');
      const labels = row.querySelectorAll('label');
      inputs.forEach((input, i) => {
        if (!input.id) input.id = `rankingInput${++serial}`;
        if (labels[i]) labels[i].htmlFor = input.id;
      });
      const button = row.querySelector('.remove-rank');
      button.disabled = current.length === 1;
      button.setAttribute('aria-label', `Remove rank row ${index + 1}`);
    });
  }

  add.addEventListener('click', () => {
    const existing = [...rows.querySelectorAll('[name="rank_id"]')]
      .map(input => Number(input.value)).filter(Number.isInteger);
    const next = Math.min(2147483647, Math.max(0, ...existing) + 1);
    const fragment = template.content.cloneNode(true);
    const number = fragment.querySelector('[name="rank_id"]');
    number.value = String(next);
    rows.appendChild(fragment);
    updateRows();
    number.focus();
  });

  rows.addEventListener('click', event => {
    const button = event.target.closest('.remove-rank');
    if (!button || rows.querySelectorAll('.rank-row').length <= 1) return;
    const row = button.closest('.rank-row');
    if (row.dataset.persisted === 'true' && !confirmFn('Remove this rank? The change takes effect when you save the scale.')) return;
    const neighbor = row.nextElementSibling || row.previousElementSibling;
    row.remove();
    updateRows();
    neighbor?.querySelector('input')?.focus();
  });
  updateRows();
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initRankSelector, initRankRows };
}
