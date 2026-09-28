const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const { templateMatchesFilter, initTemplateFilter } = require("../static/app.js");

/**
 * Build accordion markup matching the template-list page for DOM tests.
 *
 * @returns {JSDOM} DOM containing filter controls and template containers.
 */
function buildFixture() {
  const dom = new JSDOM(`<!DOCTYPE html><body>
    <input type="text" id="templateFilter">
    <button id="clearFilterBtn" class="d-none">Clear</button>
    <p id="noFilterResults" class="d-none">No templates match your filter.</p>

    <div class="accordion" id="containerList">
      <div class="accordion-item" data-id="c1">
        <button class="accordion-button collapsed" aria-expanded="false"></button>
        <div class="accordion-collapse collapse">
          <div class="list-group-item" data-id="t1" data-name="Positive Feedback"></div>
          <div class="list-group-item" data-id="t2" data-name="Constructive Feedback"></div>
        </div>
      </div>

      <div class="accordion-item" data-id="c2">
        <button class="accordion-button collapsed" aria-expanded="false"></button>
        <div class="accordion-collapse collapse">
          <div class="list-group-item" data-id="t3" data-name="Attendance Note"></div>
        </div>
      </div>

      <div class="accordion-item no-drag">
        <button class="accordion-button collapsed" aria-expanded="false"></button>
        <div class="accordion-collapse collapse">
          <div class="list-group-item" data-id="t4" data-name="Quick Praise"></div>
        </div>
      </div>
    </div>
  </body>`);

  global.document = dom.window.document;
  return dom;
}

/**
 * Collect commonly used elements and query helpers from a test DOM.
 *
 * @param {JSDOM} dom - DOM returned by {@link buildFixture}.
 * @returns {object} Filter controls and template lookup helpers.
 */
function getters(dom) {
  const doc = dom.window.document;
  return {
    input: doc.getElementById("templateFilter"),
    clearBtn: doc.getElementById("clearFilterBtn"),
    noResults: doc.getElementById("noFilterResults"),
    row: (id) => doc.querySelector(`[data-id="${id}"]`),
    container: (dataId) => doc.querySelector(`.accordion-item[data-id="${dataId}"]`),
    uncategorized: () => doc.querySelector(".accordion-item.no-drag"),
  };
}

/**
 * Enter a filter value and dispatch the same event as browser input.
 *
 * @param {JSDOM} dom - DOM that owns the input element.
 * @param {HTMLInputElement} input - Template filter input.
 * @param {string} value - Filter value to enter.
 */
function type(dom, input, value) {
  input.value = value;
  input.dispatchEvent(new dom.window.Event("input"));
}

// ---------------------------------------------------------------------------
// Pure matching logic
// ---------------------------------------------------------------------------

test("templateMatchesFilter: empty query matches everything", () => {
  assert.equal(templateMatchesFilter("Positive Feedback", ""), true);
});

test("templateMatchesFilter: case-insensitive substring match", () => {
  assert.equal(templateMatchesFilter("Positive Feedback", "positive"), true);
  assert.equal(templateMatchesFilter("Positive Feedback", "FEED"), true);
});

test("templateMatchesFilter: non-matching substring returns false", () => {
  assert.equal(templateMatchesFilter("Positive Feedback", "xyz"), false);
});

// ---------------------------------------------------------------------------
// DOM behavior
// ---------------------------------------------------------------------------

test("typing a query shows only matching templates and expands their container", () => {
  const dom = buildFixture();
  const { input, row, container } = getters(dom);
  initTemplateFilter();

  type(dom, input, "positive");

  assert.equal(row("t1").classList.contains("d-none"), false, "matching row stays visible");
  assert.equal(row("t2").classList.contains("d-none"), true, "non-matching sibling row hides");

  const c1 = container("c1");
  assert.equal(c1.classList.contains("d-none"), false, "container with a match stays visible");
  assert.equal(
    c1.querySelector(".accordion-collapse").classList.contains("show"),
    true,
    "container with a match auto-expands"
  );
  assert.equal(
    c1.querySelector(".accordion-button").classList.contains("collapsed"),
    false
  );
  assert.equal(
    c1.querySelector(".accordion-button").getAttribute("aria-expanded"),
    "true"
  );
});

test("containers with no matching templates are hidden entirely", () => {
  const dom = buildFixture();
  const { input, container } = getters(dom);
  initTemplateFilter();

  type(dom, input, "positive");

  const c2 = container("c2");
  assert.equal(c2.classList.contains("d-none"), true);
  assert.equal(c2.querySelector(".accordion-collapse").classList.contains("show"), false);
});

test("filter matches templates inside the uncategorized section too", () => {
  const dom = buildFixture();
  const { input, row, uncategorized } = getters(dom);
  initTemplateFilter();

  type(dom, input, "quick");

  assert.equal(row("t4").classList.contains("d-none"), false);
  const uncategorizedItem = uncategorized();
  assert.equal(uncategorizedItem.classList.contains("d-none"), false);
  assert.equal(
    uncategorizedItem.querySelector(".accordion-collapse").classList.contains("show"),
    true
  );
});

test("no matches shows the empty-results message and hides every container", () => {
  const dom = buildFixture();
  const { input, noResults, container, uncategorized } = getters(dom);
  initTemplateFilter();

  type(dom, input, "nonexistent");

  assert.equal(noResults.classList.contains("d-none"), false);
  assert.equal(container("c1").classList.contains("d-none"), true);
  assert.equal(container("c2").classList.contains("d-none"), true);
  assert.equal(uncategorized().classList.contains("d-none"), true);
});

test("clear button appears while filtering and clears the filter when clicked", () => {
  const dom = buildFixture();
  const { input, clearBtn, row, container, noResults } = getters(dom);
  initTemplateFilter();

  assert.equal(clearBtn.classList.contains("d-none"), true, "hidden with no query");

  type(dom, input, "attendance");
  assert.equal(clearBtn.classList.contains("d-none"), false, "shown while filtering");

  clearBtn.dispatchEvent(new dom.window.Event("click"));

  assert.equal(input.value, "", "input is cleared");
  assert.equal(clearBtn.classList.contains("d-none"), true, "hidden again after clear");
  assert.equal(noResults.classList.contains("d-none"), true);

  ["t1", "t2", "t3", "t4"].forEach((id) => {
    assert.equal(row(id).classList.contains("d-none"), false, `${id} visible again`);
  });
  ["c1", "c2"].forEach((id) => {
    assert.equal(container(id).classList.contains("d-none"), false, `${id} visible again`);
  });
});

test("clearing the filter collapses containers back to their default state", () => {
  const dom = buildFixture();
  const { input, container, clearBtn } = getters(dom);
  initTemplateFilter();

  type(dom, input, "positive");
  assert.equal(
    container("c1").querySelector(".accordion-collapse").classList.contains("show"),
    true,
    "expanded while filtering"
  );

  clearBtn.dispatchEvent(new dom.window.Event("click"));

  assert.equal(
    container("c1").querySelector(".accordion-collapse").classList.contains("show"),
    false,
    "collapsed again after clearing"
  );
  assert.equal(
    container("c1").querySelector(".accordion-button").classList.contains("collapsed"),
    true
  );
});

// ---------------------------------------------------------------------------
// Container dropdown filter
// ---------------------------------------------------------------------------

/**
 * Add a container dropdown to the fixture, as rendered on the index page.
 *
 * @param {JSDOM} dom - DOM returned by {@link buildFixture}.
 * @returns {HTMLSelectElement} The container select.
 */
function addContainerSelect(dom) {
  const doc = dom.window.document;
  const select = doc.createElement("select");
  select.id = "containerFilter";
  select.innerHTML = `<option value="">All containers</option>
    <option value="c1">One</option><option value="c2">Two</option>
    <option value="uncategorized">Uncategorized</option>`;
  doc.body.prepend(select);
  return select;
}

/**
 * Choose a container in the dropdown and dispatch a change event.
 *
 * @param {JSDOM} dom - DOM that owns the select.
 * @param {HTMLSelectElement} select - Container select.
 * @param {string} value - Option value to choose.
 */
function choose(dom, select, value) {
  select.value = value;
  select.dispatchEvent(new dom.window.Event("change"));
}

test("choosing a container shows only that container, expanded with all its templates", () => {
  const dom = buildFixture();
  const select = addContainerSelect(dom);
  const { row, container, uncategorized, clearBtn } = getters(dom);
  initTemplateFilter();

  choose(dom, select, "c1");

  assert.equal(container("c1").classList.contains("d-none"), false);
  assert.equal(container("c1").querySelector(".accordion-collapse").classList.contains("show"), true);
  assert.equal(row("t1").classList.contains("d-none"), false);
  assert.equal(row("t2").classList.contains("d-none"), false);
  assert.equal(container("c2").classList.contains("d-none"), true);
  assert.equal(uncategorized().classList.contains("d-none"), true);
  assert.equal(clearBtn.classList.contains("d-none"), false, "clear shown");
});

test("choosing uncategorized shows only the uncategorized section", () => {
  const dom = buildFixture();
  const select = addContainerSelect(dom);
  const { container, uncategorized } = getters(dom);
  initTemplateFilter();

  choose(dom, select, "uncategorized");

  assert.equal(uncategorized().classList.contains("d-none"), false);
  assert.equal(container("c1").classList.contains("d-none"), true);
  assert.equal(container("c2").classList.contains("d-none"), true);
});

test("container choice combines with the name query", () => {
  const dom = buildFixture();
  const select = addContainerSelect(dom);
  const { input, row, noResults } = getters(dom);
  initTemplateFilter();

  choose(dom, select, "c1");
  type(dom, input, "constructive");
  assert.equal(row("t1").classList.contains("d-none"), true);
  assert.equal(row("t2").classList.contains("d-none"), false);

  type(dom, input, "attendance");
  assert.equal(noResults.classList.contains("d-none"), false, "match is in another container");
});

test("clear resets the container choice back to all containers", () => {
  const dom = buildFixture();
  const select = addContainerSelect(dom);
  const { container, clearBtn, uncategorized } = getters(dom);
  initTemplateFilter();

  choose(dom, select, "c2");
  clearBtn.dispatchEvent(new dom.window.Event("click"));

  assert.equal(select.value, "");
  assert.equal(clearBtn.classList.contains("d-none"), true);
  ["c1", "c2"].forEach((id) => {
    assert.equal(container(id).classList.contains("d-none"), false);
    assert.equal(container(id).querySelector(".accordion-collapse").classList.contains("show"), false);
  });
  assert.equal(uncategorized().classList.contains("d-none"), false);
});
