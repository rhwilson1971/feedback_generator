const test = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const { initReturnContainer, initTemplateFilter } = require('../static/app.js');

/** Build an accordion DOM, set global.document, and track scroll calls. */
function fixture(query = '?return_template=t1', uncategorized = false) {
  const dom = new JSDOM(`<input id="templateFilter"><button id="clearFilterBtn"></button>
    <p id="noFilterResults"></p><div class="accordion-item" ${uncategorized ? '' : 'data-id="current-container"'}>
    <button class="accordion-button collapsed" aria-expanded="false"></button>
    <div class="accordion-collapse collapse"><div class="list-group-item" data-name="Example" data-id="t1"></div></div></div>
    <div class="accordion-item"><div class="accordion-collapse collapse"></div></div>`,
    { url: `https://example.test/${query}` });
  global.document = dom.window.document;
  const item = document.querySelector('.accordion-item');
  let scrolled = 0;
  item.scrollIntoView = () => scrolled++;
  return { dom, item, scrolled: () => scrolled };
}

test('return opens the current container and scrolls it into view', () => {
  const f = fixture();
  initReturnContainer(f.dom.window.document);
  assert.ok(f.item.querySelector('.accordion-collapse').classList.contains('show'));
  assert.equal(f.item.querySelector('button').getAttribute('aria-expanded'), 'true');
  assert.equal(f.item.querySelector('button').classList.contains('collapsed'), false);
  assert.equal(f.scrolled(), 1);
  assert.equal(document.querySelectorAll('.accordion-collapse.show').length, 1);
});

test('return opens Uncategorized', () => {
  const f = fixture('?return_template=t1', true);
  initReturnContainer(f.dom.window.document);
  assert.ok(f.item.querySelector('.accordion-collapse').classList.contains('show'));
  assert.equal(f.scrolled(), 1);
});

test('scroll offset accounts for a tall mobile navigation bar', () => {
  const f = fixture();
  const nav = document.createElement('nav');
  nav.className = 'sticky-top';
  nav.getBoundingClientRect = () => ({ height: 218 });
  document.body.prepend(nav);
  initReturnContainer(f.dom.window.document);
  assert.equal(f.item.style.scrollMarginTop, '234px');
});

test('ordinary visits and missing or malformed targets leave containers collapsed', () => {
  for (const query of ['', '?return_template=deleted', '?return_template=%22%5D', '?return_template=']) {
    const f = fixture(query);
    initReturnContainer(f.dom.window.document);
    assert.equal(document.querySelectorAll('.accordion-collapse.show').length, 0);
    assert.equal(f.scrolled(), 0);
  }
});

test('subsequent filtering and Clear retain their existing behavior', () => {
  const f = fixture();
  initTemplateFilter();
  initReturnContainer(f.dom.window.document);
  const input = document.getElementById('templateFilter');
  input.value = 'absent';
  input.dispatchEvent(new f.dom.window.Event('input'));
  assert.ok(f.item.classList.contains('d-none'));
  document.getElementById('clearFilterBtn').click();
  assert.equal(f.item.classList.contains('d-none'), false);
  assert.equal(document.querySelectorAll('.accordion-collapse.show').length, 0);
  assert.equal(f.scrolled(), 1);
});
