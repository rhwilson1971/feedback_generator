const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const { initCopyContainerModal } = require("../static/app.js");

test("opening the modal targets the container and suggests a copy name", () => {
  const dom = new JSDOM(`<!DOCTYPE html><body>
    <button id="trigger" data-container-id="abc" data-container-name="Essays"></button>
    <div id="copyContainerModal" data-action-template="/containers/__ID__/copy">
      <form id="copyContainerForm"></form>
      <strong id="copyContainerSource"></strong>
      <input id="copyContainerName">
    </div></body>`);
  const doc = dom.window.document;
  initCopyContainerModal(doc);

  const event = new dom.window.Event("show.bs.modal");
  event.relatedTarget = doc.getElementById("trigger");
  doc.getElementById("copyContainerModal").dispatchEvent(event);

  assert.equal(doc.getElementById("copyContainerForm").getAttribute("action"), "/containers/abc/copy");
  assert.equal(doc.getElementById("copyContainerSource").textContent, "Essays");
  assert.equal(doc.getElementById("copyContainerName").value, "Essays (copy)");
});
