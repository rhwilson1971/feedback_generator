const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const { bodyHasPlaceholder, initPlaceholderConfirm } = require("../static/app.js");

/**
 * Build a template form, wire the confirmation, and submit it.
 *
 * @param {string} body - Template body to submit.
 * @param {boolean} answer - What the confirm prompt returns.
 * @returns {{prevented: boolean, asked: number}} Submit outcome.
 */
function submitWith(body, answer) {
  const dom = new JSDOM(`<!DOCTYPE html><body>
    <form id="templateForm"><textarea id="body"></textarea></form></body>`);
  const doc = dom.window.document;
  doc.getElementById("body").value = body;
  let asked = 0;
  initPlaceholderConfirm(doc, () => { asked++; return answer; });
  const event = new dom.window.Event("submit", { cancelable: true });
  doc.getElementById("templateForm").dispatchEvent(event);
  return { prevented: event.defaultPrevented, asked };
}

test("bodyHasPlaceholder detects {name} style placeholders", () => {
  assert.equal(bodyHasPlaceholder("Hello, {name}."), true);
  assert.equal(bodyHasPlaceholder("Hello there."), false);
  assert.equal(bodyHasPlaceholder("Braces {} only"), false);
});

test("body with a placeholder submits without asking", () => {
  assert.deepEqual(submitWith("Hi {name}", false), { prevented: false, asked: 0 });
});

test("body without a placeholder asks and cancels when declined", () => {
  assert.deepEqual(submitWith("Great work.", false), { prevented: true, asked: 1 });
});

test("body without a placeholder submits when confirmed", () => {
  assert.deepEqual(submitWith("Great work.", true), { prevented: false, asked: 1 });
});
