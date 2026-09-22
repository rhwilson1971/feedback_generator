const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const { initCopyModal } = require("../static/app.js");

/**
 * Build the copy modal and a template row trigger for DOM tests.
 *
 * @returns {JSDOM} DOM containing the modal, its form, and a Copy button.
 */
function buildFixture() {
  return new JSDOM(`<!DOCTYPE html><body>
    <button id="trigger" data-template-id="abc123"
            data-template-name="Great work" data-container-id="c2"></button>
    <button id="uncategorizedTrigger" data-template-id="def456"
            data-template-name="Loose note" data-container-id=""></button>
    <div id="copyTemplateModal" data-action-template="/templates/__ID__/copy">
      <form id="copyTemplateForm" method="post">
        <strong id="copyTemplateName"></strong>
        <select id="copyTemplateContainer" name="container_id">
          <option value="">Uncategorized</option>
          <option value="c1">Essays</option>
          <option value="c2">Labs</option>
        </select>
      </form>
    </div>
  </body>`);
}

/** Fire Bootstrap's show event on the modal as if `trigger` opened it. */
function openModal(dom, trigger) {
  const { document, Event } = dom.window;
  const event = new Event("show.bs.modal");
  event.relatedTarget = trigger;
  document.getElementById("copyTemplateModal").dispatchEvent(event);
}

test("opening the modal points the form at the source template", () => {
  const dom = buildFixture();
  initCopyModal(dom.window.document);
  openModal(dom, dom.window.document.getElementById("trigger"));

  const form = dom.window.document.getElementById("copyTemplateForm");
  assert.equal(form.getAttribute("action"), "/templates/abc123/copy");
});

test("opening the modal shows the template name", () => {
  const dom = buildFixture();
  initCopyModal(dom.window.document);
  openModal(dom, dom.window.document.getElementById("trigger"));

  assert.equal(
    dom.window.document.getElementById("copyTemplateName").textContent,
    "Great work"
  );
});

test("the dropdown preselects the template's current container", () => {
  const dom = buildFixture();
  initCopyModal(dom.window.document);
  const select = dom.window.document.getElementById("copyTemplateContainer");

  openModal(dom, dom.window.document.getElementById("trigger"));
  assert.equal(select.value, "c2");

  openModal(dom, dom.window.document.getElementById("uncategorizedTrigger"));
  assert.equal(select.value, "");
});

test("reopening for another template replaces the previous target", () => {
  const dom = buildFixture();
  initCopyModal(dom.window.document);
  openModal(dom, dom.window.document.getElementById("trigger"));
  openModal(dom, dom.window.document.getElementById("uncategorizedTrigger"));

  const form = dom.window.document.getElementById("copyTemplateForm");
  assert.equal(form.getAttribute("action"), "/templates/def456/copy");
});

test("does nothing when the modal is absent", () => {
  const dom = new JSDOM("<!DOCTYPE html><body></body>");
  assert.doesNotThrow(() => initCopyModal(dom.window.document));
});
