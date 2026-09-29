const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const { captureFeedback } = require("../extension/capture.js");

function run(html) {
  const doc = new JSDOM(`<!DOCTYPE html><body>${html}</body>`).window.document;
  const sent = [];
  const found = captureFeedback(doc, { sendMessage: (m) => sent.push(m) });
  return { found, sent };
}

test("sends the generated feedback to the extension", () => {
  const { found, sent } = run(
    `<textarea id="resultText" data-feedback-generated>Well done, Tom.</textarea>`
  );
  assert.equal(found, true);
  assert.deepEqual(sent, [{ type: "feedback", text: "Well done, Tom." }]);
});

test("does nothing on pages without generated feedback", () => {
  assert.deepEqual(run(`<textarea id="resultText"></textarea>`), { found: false, sent: [] });
  assert.deepEqual(run(`<p>index</p>`), { found: false, sent: [] });
});

test("ignores an empty result", () => {
  assert.deepEqual(
    run(`<textarea id="resultText" data-feedback-generated>  </textarea>`),
    { found: false, sent: [] }
  );
});
