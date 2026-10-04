const test = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const { initCustomFeedback } = require('../static/generate.js');

function fixture() {
  const dom = new JSDOM(`<form id="generationForm">
    <textarea id="feedbackBody">Hi {name} {grade}</textarea>
    <div id="generationPlaceholders"><div data-placeholder="name"><input name="ph_name" value="Ana"></div>
    <div data-placeholder="grade"><select name="ph_grade"><option value="Good">Good</option><option selected value="Great">Great</option></select></div></div>
    <input type="radio" name="save_mode" value="once" checked><input type="radio" name="save_mode" value="save">
    <div id="newTemplateNameGroup"><input id="newTemplateName"></div></form>`);
  const doc = dom.window.document;
  initCustomFeedback(doc, [{name: 'name', input_type: 'freeform', options: []},
    {name: 'grade', input_type: 'dropdown', options: ['Good', 'Great']}], {name: ['Tom']}, true);
  return {doc, edit(body) {
    doc.getElementById('feedbackBody').value = body;
    doc.getElementById('feedbackBody').dispatchEvent(new dom.window.Event('input'));
  }, dom};
}

test('fields follow body order, deduplicate, and restore values after removal', () => {
  const f = fixture();
  f.edit('{new} {name} {new}');
  const fields = () => [...f.doc.querySelectorAll('#generationPlaceholders input, #generationPlaceholders select')];
  assert.deepEqual(fields().map(x => x.name), ['ph_new', 'ph_name']);
  assert.equal(fields()[1].value, 'Ana');
  fields()[0].value = 'Keep';
  f.edit('Plain text');
  assert.equal(fields().length, 0);
  f.edit('{grade} {new} {name}');
  assert.deepEqual(fields().map(x => x.value), ['Great', 'Keep', 'Ana']);
  assert.deepEqual([...fields()[0].options].map(x => x.value), ['Good', 'Great']);
});

test('new fields support Unicode names and receive autofill guards', () => {
  const f = fixture();
  f.edit('{élève} {学生} {𝔘} {a_1} {not-valid}');
  const fields = [...f.doc.querySelectorAll('#generationPlaceholders input')];
  assert.deepEqual(fields.map(x => x.name), ['ph_élève', 'ph_学生', 'ph_𝔘', 'ph_a_1']);
  assert.ok(fields.every(x => x.required && x.getAttribute('data-1p-ignore') === 'true'));
});

test('restored dropdown keeps configuration even if absent on initial render', () => {
  const f = fixture();
  f.doc.getElementById('generationPlaceholders').replaceChildren();
  initCustomFeedback(f.doc, [{name: 'grade', input_type: 'dropdown', options: ['Good', 'Great']}]);
  f.edit('{grade}');
  const select = f.doc.querySelector('select');
  assert.deepEqual([...select.options].map(x => x.value), ['', 'Good', 'Great']);
});

test('name is visible and required only when saving', () => {
  const f = fixture();
  const group = f.doc.getElementById('newTemplateNameGroup');
  const name = f.doc.getElementById('newTemplateName');
  assert.equal(group.hidden, true);
  assert.equal(name.required, false);
  const save = f.doc.querySelector('[value="save"]');
  save.checked = true;
  save.dispatchEvent(new f.dom.window.Event('change', {bubbles: true}));
  assert.equal(group.hidden, false);
  assert.equal(name.required, true);
  f.doc.querySelector('[value="once"]').click();
  assert.equal(group.hidden, true);
  assert.equal(name.required, false);
});

test('placeholder names matching object properties remain usable', () => {
  const f = fixture();
  assert.doesNotThrow(() => f.edit('{hasOwnProperty} {constructor} {__proto__}'));
  assert.equal(f.doc.querySelectorAll('#generationPlaceholders input').length, 3);
});
