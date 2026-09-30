const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const {
  templateMatchesTags,
  initTemplateFilter,
  initTagSuggestions,
} = require("../static/app.js");

/**
 * Build the index filters and two containers of tagged templates.
 *
 * @returns {JSDOM} DOM with name, container and tag filters.
 */
function buildFixture() {
  const dom = new JSDOM(`<!DOCTYPE html><body>
    <select id="containerFilter">
      <option value="">All</option><option value="c1">One</option><option value="c2">Two</option>
    </select>
    <input type="text" id="templateFilter">
    <button id="tagFilterToggle" class="btn-outline-secondary">Tags</button>
    <form id="tagFilterForm">
      <input type="checkbox" class="tag-filter-option" value="praise">
      <input type="checkbox" class="tag-filter-option" value="late">
      <button type="button" id="tagFilterReset"></button>
    </form>
    <button id="clearFilterBtn" class="d-none">Clear</button>
    <p id="noFilterResults" class="d-none"></p>
    <div id="containerList">
      <div class="accordion-item" data-id="c1">
        <button class="accordion-button collapsed"></button>
        <div class="accordion-collapse collapse">
          <div class="list-group-item" data-id="t1" data-name="Great essay" data-tags='["Praise"]'></div>
          <div class="list-group-item" data-id="t2" data-name="Late essay" data-tags='["late"]'></div>
          <div class="list-group-item" data-id="t3" data-name="Untagged" data-tags='[]'></div>
        </div>
      </div>
      <div class="accordion-item" data-id="c2">
        <button class="accordion-button collapsed"></button>
        <div class="accordion-collapse collapse">
          <div class="list-group-item" data-id="t4" data-name="Great lab" data-tags='["praise","lab"]'></div>
        </div>
      </div>
    </div>
  </body>`);
  global.document = dom.window.document;
  initTemplateFilter();
  return dom;
}

/**
 * Tick the given tag boxes and submit the tag form (the Apply button).
 *
 * @param {JSDOM} dom - Fixture DOM.
 * @param {string[]} tags - Tag values to check.
 */
function applyTags(dom, tags) {
  const doc = dom.window.document;
  doc.querySelectorAll(".tag-filter-option").forEach((box) => {
    box.checked = tags.includes(box.value);
  });
  doc.getElementById("tagFilterForm").dispatchEvent(
    new dom.window.Event("submit", { cancelable: true })
  );
}

/**
 * Ids of template rows currently visible.
 *
 * @param {JSDOM} dom - Fixture DOM.
 * @returns {string[]} Visible row ids.
 */
function visibleRows(dom) {
  return Array.from(
    dom.window.document.querySelectorAll(".list-group-item:not(.d-none)"),
    (row) => row.dataset.id
  );
}

test("templateMatchesTags: any applied tag matches, case-insensitive", () => {
  assert.equal(templateMatchesTags(["Praise"], []), true);
  assert.equal(templateMatchesTags(["Praise"], ["praise", "late"]), true);
  assert.equal(templateMatchesTags(["lab"], ["praise"]), false);
  assert.equal(templateMatchesTags([], ["praise"]), false);
});

test("checking tags does nothing until Apply", () => {
  const dom = buildFixture();
  dom.window.document.querySelector(".tag-filter-option").checked = true;
  assert.deepEqual(visibleRows(dom), ["t1", "t2", "t3", "t4"]);
});

test("Apply shows templates with any selected tag across containers", () => {
  const dom = buildFixture();
  applyTags(dom, ["praise"]);

  assert.deepEqual(visibleRows(dom), ["t1", "t4"]);
  const doc = dom.window.document;
  doc.querySelectorAll(".accordion-item").forEach((item) => {
    assert.equal(item.classList.contains("d-none"), false);
    assert.equal(item.querySelector(".accordion-collapse").classList.contains("show"), true);
  });
  assert.equal(doc.getElementById("tagFilterToggle").textContent, "Tags (1)");
  assert.equal(doc.getElementById("clearFilterBtn").classList.contains("d-none"), false);
});

test("tags combine with the container filter", () => {
  const dom = buildFixture();
  const doc = dom.window.document;
  const select = doc.getElementById("containerFilter");
  select.value = "c2";
  select.dispatchEvent(new dom.window.Event("change"));
  applyTags(dom, ["praise"]);

  assert.deepEqual(visibleRows(dom), ["t4"]);
  assert.equal(doc.querySelector('[data-id="c1"]').classList.contains("d-none"), true);
});

test("tags combine with the name filter", () => {
  const dom = buildFixture();
  const input = dom.window.document.getElementById("templateFilter");
  applyTags(dom, ["praise", "late"]);
  input.value = "essay";
  input.dispatchEvent(new dom.window.Event("input"));

  assert.deepEqual(visibleRows(dom), ["t1", "t2"]);
});

test("no matching tags shows the empty message", () => {
  const dom = buildFixture();
  const doc = dom.window.document;
  const select = doc.getElementById("containerFilter");
  select.value = "c2";
  select.dispatchEvent(new dom.window.Event("change"));
  applyTags(dom, ["late"]);

  assert.equal(doc.getElementById("noFilterResults").classList.contains("d-none"), false);
});

test("Clear tags drops only the tag filter", () => {
  const dom = buildFixture();
  const doc = dom.window.document;
  const select = doc.getElementById("containerFilter");
  select.value = "c1";
  select.dispatchEvent(new dom.window.Event("change"));
  applyTags(dom, ["late"]);
  doc.getElementById("tagFilterReset").dispatchEvent(new dom.window.Event("click"));

  assert.deepEqual(visibleRows(dom), ["t1", "t2", "t3"]);
  assert.equal(doc.querySelector('[data-id="c2"]').classList.contains("d-none"), true);
  assert.equal(select.value, "c1");
  assert.equal(doc.getElementById("tagFilterToggle").textContent, "Tags");
  assert.equal(doc.querySelectorAll(".tag-filter-option:checked").length, 0);
});

test("main Clear resets tags, container and name", () => {
  const dom = buildFixture();
  const doc = dom.window.document;
  applyTags(dom, ["praise"]);
  doc.getElementById("clearFilterBtn").dispatchEvent(new dom.window.Event("click"));

  assert.deepEqual(visibleRows(dom), ["t1", "t2", "t3", "t4"]);
  assert.equal(doc.querySelectorAll(".tag-filter-option:checked").length, 0);
  assert.equal(doc.getElementById("tagFilterToggle").textContent, "Tags");
  assert.equal(doc.getElementById("clearFilterBtn").classList.contains("d-none"), true);
});

test("tag suggestion buttons add a tag once", () => {
  const dom = new JSDOM(`<!DOCTYPE html><body>
    <input id="tags" value="praise">
    <button class="tag-suggestion" data-tag="late">late</button>
    <button class="tag-suggestion" data-tag="Praise">Praise</button></body>`);
  const doc = dom.window.document;
  initTagSuggestions(doc);
  const [late, praise] = doc.querySelectorAll(".tag-suggestion");

  late.dispatchEvent(new dom.window.Event("click"));
  praise.dispatchEvent(new dom.window.Event("click"));

  assert.equal(doc.getElementById("tags").value, "praise, late");
});
