const test = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const { initTemplateFilter } = require('../static/app.js');
const rankings = require('../static/rankings.js');

/** Initialize ranking and template filters on a DOM with ranked and legacy templates. */
function fixture() {
  const dom = new JSDOM(`<select id="containerFilter"><option value="">All</option><option value="c1">Essays</option><option value="c2">Labs</option></select>
    <select id="rankingFilter"><option value="">All rankings</option><option value="unranked">Unranked</option><option value="s1">Completion</option><option value="s2">Quality</option></select>
    <select id="rankFilter"><option value="">All ranks</option><option value="1">Completed</option><option value="3">Retry</option></select>
    <input id="templateFilter"><button id="clearFilterBtn" class="d-none">Clear</button><p id="noFilterResults" class="d-none">None</p>
    <form id="tagFilterForm"><input type="checkbox" class="tag-filter-option" value="praise"></form><button id="tagFilterToggle">Tags</button>
    <div class="accordion-item" data-id="c1"><button class="accordion-button collapsed"></button><div class="accordion-collapse collapse">
      <div class="list-group-item" data-id="t1" data-name="Great essay" data-tags='["praise"]' data-ranking-scale="s1" data-ranking-rank="1"></div>
      <div class="list-group-item" data-id="t2" data-name="Retry essay" data-tags='[]' data-ranking-scale="s1" data-ranking-rank="3"></div>
      <div class="list-group-item" data-id="t3" data-name="Legacy essay" data-tags='[]'></div>
    </div></div>
    <div class="accordion-item" data-id="c2"><button class="accordion-button collapsed"></button><div class="accordion-collapse collapse">
      <div class="list-group-item" data-id="t4" data-name="Great lab" data-tags='["praise"]' data-ranking-scale="s2" data-ranking-rank="1"></div>
      <div class="list-group-item" data-id="t5" data-name="Plain lab" data-tags='[]' data-ranking-scale="" data-ranking-rank=""></div>
    </div></div>`);
  global.document = dom.window.document;
  rankings.initRankSelector(document.getElementById('rankingFilter'), document.getElementById('rankFilter'), [
    { id: 's1', ranks: [{ id: 1, description: 'Completed' }, { id: 3, description: 'Retry' }] },
    { id: 's2', ranks: [{ id: 1, description: 'Great' }] },
  ], true);
  initTemplateFilter();
  return dom;
}
/** Select a filter value and dispatch the change event that applies it. */
function choose(dom, id, value) {
  const el = dom.window.document.getElementById(id);
  el.value = value;
  el.dispatchEvent(new dom.window.Event('change', { bubbles: true }));
}
/** Return IDs of template rows currently visible in the fixture. */
function visible(dom) {
  return [...dom.window.document.querySelectorAll('.list-group-item:not(.d-none)')].map(el => el.dataset.id);
}

test('scale filtering shows its templates and expands matching containers', () => {
  const dom = fixture();
  choose(dom, 'rankingFilter', 's1');
  assert.deepEqual(visible(dom), ['t1', 't2']);
  assert.ok(document.querySelector('[data-id="c1"] .accordion-collapse').classList.contains('show'));
  assert.ok(document.querySelector('[data-id="c2"]').classList.contains('d-none'));
  assert.equal(document.getElementById('clearFilterBtn').classList.contains('d-none'), false);
});

test('a specific rank matches only within its scale', () => {
  const dom = fixture();
  choose(dom, 'rankingFilter', 's1');
  choose(dom, 'rankFilter', '1');
  assert.deepEqual(visible(dom), ['t1']);
});

test('Unranked includes old templates and explicitly unranked templates', () => {
  const dom = fixture();
  choose(dom, 'rankingFilter', 'unranked');
  assert.deepEqual(visible(dom), ['t3', 't5']);
});

test('rankings combine with name, container, and tag filters', () => {
  const dom = fixture();
  choose(dom, 'rankingFilter', 's1');
  choose(dom, 'containerFilter', 'c1');
  document.querySelector('.tag-filter-option').checked = true;
  document.getElementById('tagFilterForm').dispatchEvent(new dom.window.Event('submit', { cancelable: true }));
  assert.deepEqual(visible(dom), ['t1']);
  document.getElementById('templateFilter').value = 'Retry';
  document.getElementById('templateFilter').dispatchEvent(new dom.window.Event('input'));
  assert.deepEqual(visible(dom), []);
  assert.equal(document.getElementById('noFilterResults').classList.contains('d-none'), false);
});

test('changing scale clears previous rank and Clear resets all controls', () => {
  const dom = fixture();
  choose(dom, 'rankingFilter', 's1');
  choose(dom, 'rankFilter', '3');
  choose(dom, 'rankingFilter', 's2');
  assert.equal(document.getElementById('rankFilter').value, '');
  assert.deepEqual(visible(dom), ['t4']);
  choose(dom, 'containerFilter', 'c2');
  document.getElementById('clearFilterBtn').click();
  assert.equal(document.getElementById('rankingFilter').value, '');
  assert.equal(document.getElementById('rankFilter').value, '');
  assert.equal(document.getElementById('rankFilter').disabled, true);
  assert.equal(document.getElementById('containerFilter').value, '');
  assert.deepEqual(visible(dom), ['t1', 't2', 't3', 't4', 't5']);
  assert.equal(document.querySelectorAll('.accordion-collapse.show').length, 0);
});
