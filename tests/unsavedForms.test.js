const test = require('node:test');
const assert = require('node:assert/strict');
const { JSDOM } = require('jsdom');
const { snapshotForm, initUnsavedForms } = require('../static/unsaved-forms.js');

/** Create an opted-in form and expose a simulated cancelable unload event. */
function fixture(content = '<input name="name" value="Original">') {
  const dom = new JSDOM(`<form data-unsaved-form>${content}</form>`);
  const doc = dom.window.document;
  const form = doc.querySelector('form');
  initUnsavedForms(doc);
  return { doc, form, win: dom.window, unload() {
    const event = new dom.window.Event('beforeunload', {cancelable:true});
    dom.window.dispatchEvent(event);
    return event.defaultPrevented;
  }};
}

/** Dispatch a submit without invoking jsdom's unimplemented navigation. */
function submit(f) {
  const event = new f.win.Event('submit', {bubbles:true, cancelable:true});
  f.form.dispatchEvent(event);
  return event;
}

test('clean and reverted forms do not warn; changed values warn', () => {
  const f = fixture();
  assert.equal(f.unload(), false);
  f.form.elements.name.value = 'Edited';
  assert.equal(f.unload(), true);
  f.form.elements.name.value = 'Original';
  assert.equal(f.unload(), false);
});

test('checkboxes, radios and disabled controls are compared', () => {
  const f = fixture('<input name="flag" type="checkbox"><input name="theme" type="radio" value="light" checked><input name="theme" type="radio" value="dark"><input name="disabled" disabled value="A">');
  f.form.elements.flag.checked = true;
  assert.equal(f.unload(), true);
  f.form.elements.flag.checked = false;
  f.form.elements.theme[1].checked = true;
  assert.equal(f.unload(), true);
  f.form.elements.theme[0].checked = true;
  f.form.elements.disabled.value = 'B';
  assert.equal(f.unload(), true);
});

test('dynamic field changes and repeated row order are protected', () => {
  const f = fixture('<input name="rank_id" value="1"><input name="rank_id" value="2">');
  const baseline = snapshotForm(f.form);
  const added = f.doc.createElement('input');
  added.name = 'new';
  f.form.append(added);
  assert.equal(f.unload(), true);
  added.remove();
  assert.equal(f.unload(), false);
  f.form.prepend(f.form.lastElementChild);
  assert.notEqual(snapshotForm(f.form), baseline);
  assert.equal(f.unload(), true);
});

test('programmatic changes warn without dispatched input events', () => {
  const f = fixture('<input name="tags" value="">');
  f.form.elements.tags.value = 'praise';
  assert.equal(f.unload(), true);
});

test('button values and read-only output do not affect dirty state', () => {
  const f = fixture('<button name="button" value="A">Save</button><input type="submit" name="submit" value="Save"><textarea name="result" readonly>Old</textarea>');
  f.form.elements.button.value = 'B';
  f.form.elements.result.value = 'New';
  assert.equal(f.unload(), false);
});

test('inactive new-template name is ignored until saving is selected', () => {
  const f = fixture('<input type="radio" name="mode" id="once" value="once" checked><input type="radio" name="mode" value="save"><input name="new_name" value="Suggested" data-unsaved-ignore-if="#once:checked">');
  f.form.elements.new_name.value = 'Changed';
  assert.equal(f.unload(), false);
  f.form.elements.mode[1].checked = true;
  assert.equal(f.unload(), true);
  f.form.elements.mode[0].checked = true;
  assert.equal(f.unload(), false);
});

test('accepted submits suppress discard warning; canceled submits retain it', () => {
  const f = fixture();
  f.form.elements.name.value = 'Edited';
  submit(f);
  assert.equal(f.unload(), false);
  f.form.addEventListener('submit', event => event.preventDefault());
  submit(f);
  assert.equal(f.unload(), true);
});

test('invalid or subsequently edited forms still warn', () => {
  const f = fixture('<input name="name" required value="Original">');
  f.form.elements.name.value = '';
  assert.equal(f.form.checkValidity(), false);
  assert.equal(f.unload(), true);
  f.form.elements.name.value = 'Valid';
  submit(f);
  f.form.elements.name.value = 'Later edit';
  assert.equal(f.unload(), true);
});

test('pageshow restores protection without replacing the original baseline', () => {
  const f = fixture();
  f.form.elements.name.value = 'Edited';
  submit(f);
  assert.equal(f.unload(), false);
  f.win.dispatchEvent(new f.win.Event('pageshow'));
  assert.equal(f.unload(), true);
});

test('fresh result page starts clean and later edits warn', () => {
  const f = fixture('<textarea name="body">Edited {name}</textarea><input name="ph_name" value="Ana">');
  assert.equal(f.unload(), false);
  f.form.elements.ph_name.value = 'Tom';
  assert.equal(f.unload(), true);
});

test('unmarked forms do not warn', () => {
  const dom = new JSDOM('<form><input name="name"></form>');
  initUnsavedForms(dom.window.document);
  dom.window.document.querySelector('input').value = 'Edited';
  const event = new dom.window.Event('beforeunload', {cancelable:true});
  dom.window.dispatchEvent(event);
  assert.equal(event.defaultPrevented, false);
});
