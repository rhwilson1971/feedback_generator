const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const { isEditable, insertFeedback, initPasteTarget } = require("../extension/paste.js");

function page(html) {
  const dom = new JSDOM(`<!DOCTYPE html><body>${html}</body>`);
  // jsdom has no execCommand; make sure the manual fallback is exercised.
  dom.window.document.execCommand = undefined;
  return dom;
}

test("isEditable accepts text fields and contenteditable only", () => {
  const dom = page(`
    <textarea id="ta"></textarea><input id="plain"><input id="email" type="email">
    <input id="pw" type="password"><input id="cb" type="checkbox">
    <textarea id="ro" readonly></textarea><input id="dis" disabled>
    <div id="ce" contenteditable="true"></div><div id="div"></div>`);
  const $ = (id) => dom.window.document.getElementById(id);
  ["ta", "plain", "email", "ce"].forEach((id) => assert.equal(isEditable($(id)), true, id));
  ["pw", "cb", "ro", "dis", "div"].forEach((id) => assert.equal(isEditable($(id)), false, id));
  assert.equal(isEditable(null), false);
});

test("insertFeedback replaces the selection in a textarea and fires input", () => {
  const dom = page(`<textarea id="ta">Hello XX world</textarea>`);
  const ta = dom.window.document.getElementById("ta");
  let inputs = 0;
  ta.addEventListener("input", () => inputs++);
  ta.setSelectionRange(6, 8);

  insertFeedback(ta, "Great");

  assert.equal(ta.value, "Hello Great world");
  assert.equal(inputs, 1);
});

test("insertFeedback appends to an empty contenteditable with line breaks", () => {
  const dom = page(`<div id="ce" contenteditable="true"></div>`);
  const ce = dom.window.document.getElementById("ce");

  insertFeedback(ce, "Line one\nLine two");

  assert.equal(ce.innerHTML, "Line one<br>Line two");
});

test("insertFeedback uses execCommand when the browser supports it", () => {
  const dom = page(`<textarea id="ta"></textarea>`);
  const doc = dom.window.document;
  const calls = [];
  doc.execCommand = (...args) => { calls.push(args); return true; };

  insertFeedback(doc.getElementById("ta"), "Hi");

  assert.deepEqual(calls, [["insertText", false, "Hi"]]);
});

test("focus tracker remembers the last editable and answers paste requests", () => {
  const dom = page(`<textarea id="ta"></textarea><button id="btn"></button>
    <div contenteditable="true" id="ce"><p id="inner">x</p></div>`);
  const doc = dom.window.document;
  const sent = [];
  let listener;
  const runtime = {
    sendMessage: (m) => { sent.push(m); return Promise.resolve(); },
    onMessage: { addListener: (fn) => { listener = fn; } },
  };
  const tracker = initPasteTarget(doc, runtime);

  const reply = (msg) => { let r; listener(msg, {}, (x) => { r = x; }); return r; };
  assert.deepEqual(reply({ type: "paste", text: "x" }), { ok: false, reason: "no-target" });

  doc.getElementById("ta").dispatchEvent(new dom.window.FocusEvent("focusin", { bubbles: true }));
  doc.getElementById("btn").dispatchEvent(new dom.window.FocusEvent("focusin", { bubbles: true }));
  assert.equal(tracker.lastEditable().id, "ta", "non-editable focus is ignored");
  assert.deepEqual(sent, [{ type: "focus" }]);

  assert.deepEqual(reply({ type: "paste", text: "Done" }), { ok: true });
  assert.equal(doc.getElementById("ta").value, "Done");
  assert.equal(reply({ type: "other" }), undefined);
});

test("focus inside a rich editor child resolves to the editable root", () => {
  const dom = page(`<div contenteditable="true" id="ce"><p id="inner">x</p></div>`);
  const doc = dom.window.document;
  // jsdom doesn't compute isContentEditable; mimic the browser.
  Object.defineProperty(doc.getElementById("inner"), "isContentEditable", { value: true });
  Object.defineProperty(doc.getElementById("ce"), "isContentEditable", { value: true });
  const tracker = initPasteTarget(doc, null);

  doc.getElementById("inner").dispatchEvent(new dom.window.FocusEvent("focusin", { bubbles: true }));

  assert.equal(tracker.lastEditable().id, "ce");
});
