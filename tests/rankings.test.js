const test = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const rankings = require('../static/rankings.js');
const scales = [
  { id: 'one', name: 'Completion', ranks: [{ id: 1, description: 'Completed' }, { id: 3, description: '<script>Retry</script>' }] },
  { id: 'two', name: 'Quality', ranks: [{ id: 2, description: 'Great' }] },
];

/** Create scale and rank controls with a saved rank for selector tests. */
function selectorFixture() {
  const dom = new JSDOM('<select id="scale"><option value="">Unranked</option><option value="unranked">Unranked filter</option><option value="one">Completion</option><option value="two">Quality</option></select><select id="rank"><option value="">Choose</option><option value="3" selected>Old</option></select>');
  return { dom, scale: dom.window.document.getElementById('scale'), rank: dom.window.document.getElementById('rank') };
}

/** Select a value and notify dependent controls with a bubbling change event. */
function change(dom, select, value) {
  select.value = value;
  select.dispatchEvent(new dom.window.Event('change', { bubbles: true }));
}

test('rank selectors restore an existing selection and escape descriptions', () => {
  const { dom, scale, rank } = selectorFixture();
  scale.value = 'one';
  rankings.initRankSelector(scale, rank, scales, false);
  assert.equal(rank.value, '3');
  assert.equal(rank.required, true);
  assert.equal(rank.disabled, false);
  assert.equal(rank.querySelector('script'), null);
  assert.equal(rank.options[2].textContent, '3 — <script>Retry</script>');
});

test('changing a scale resets its rank; unranked disables the rank', () => {
  const { dom, scale, rank } = selectorFixture();
  scale.value = 'one';
  rankings.initRankSelector(scale, rank, scales, false);
  change(dom, scale, 'two');
  assert.equal(rank.value, '');
  assert.equal(rank.options.length, 2);
  change(dom, scale, '');
  assert.equal(rank.disabled, true);
  assert.equal(rank.required, false);
  assert.equal(rank.value, '');
});

test('filter selectors offer All ranks, never require a rank, and handle Unranked', () => {
  const { dom, scale, rank } = selectorFixture();
  rankings.initRankSelector(scale, rank, scales, true);
  change(dom, scale, 'one');
  assert.equal(rank.options[0].textContent, 'All ranks');
  assert.equal(rank.required, false);
  change(dom, scale, 'unranked');
  assert.equal(rank.disabled, true);
});

test('selector initialization tolerates pages without controls', () => {
  assert.doesNotThrow(() => rankings.initRankSelector(null, null, scales, false));
});

test('scale form adds numbered rows with unique label associations, removes rows, keeps one', () => {
  const dom = new JSDOM(`<div id="rankRows"><div class="rank-row"><label>Number</label><input name="rank_id" value="3"><label>Description</label><input name="rank_description"><button class="remove-rank">Remove</button></div></div><button id="addRank">Add</button><template id="rankRowTemplate"><div class="rank-row"><label>Number</label><input name="rank_id"><label>Description</label><input name="rank_description"><button class="remove-rank">Remove</button></div></template>`);
  const doc = dom.window.document;
  rankings.initRankRows(doc);
  assert.equal(doc.querySelector('.remove-rank').disabled, true);
  doc.getElementById('addRank').click();
  assert.equal(doc.querySelectorAll('.rank-row').length, 2);
  const numbers = doc.querySelectorAll('[name="rank_id"]');
  assert.equal(numbers[1].value, '4');
  assert.equal(doc.activeElement, numbers[1]);
  for (const label of doc.querySelectorAll('#rankRows label')) {
    assert.ok(doc.getElementById(label.htmlFor));
  }
  const ids = [...doc.querySelectorAll('#rankRows input')].map(el => el.id);
  assert.equal(new Set(ids).size, ids.length);
  doc.querySelector('.remove-rank').click();
  assert.equal(doc.querySelectorAll('.rank-row').length, 1);
  assert.equal(doc.querySelector('.remove-rank').disabled, true);
});

test('removing a persisted rank asks for confirmation and cancellation preserves it', () => {
  const dom = new JSDOM('<div id="rankRows"><div class="rank-row" data-persisted="true"><input name="rank_id" value="1"><button class="remove-rank">Remove</button></div><div class="rank-row"><input name="rank_id" value="2"><button class="remove-rank">Remove</button></div></div><button id="addRank">Add</button><template id="rankRowTemplate"></template>');
  let approved = false;
  let asks = 0;
  rankings.initRankRows(dom.window.document, () => { asks++; return approved; });
  const button = dom.window.document.querySelector('.remove-rank');
  button.click();
  assert.equal(asks, 1);
  assert.equal(dom.window.document.querySelectorAll('.rank-row').length, 2);
  approved = true;
  button.click();
  assert.equal(asks, 2);
  assert.equal(dom.window.document.querySelectorAll('.rank-row').length, 1);
});
