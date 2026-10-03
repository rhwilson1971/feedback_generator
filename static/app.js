// ---------------------------------------------------------------------------
// Clipboard copy
// ---------------------------------------------------------------------------

function copyToClipboard() {
  const text = document.getElementById("resultText").value;
  navigator.clipboard.writeText(text).then(() => {
    const btn = document.getElementById("copyBtn");
    const original = btn.textContent;
    btn.textContent = "Copied!";
    btn.classList.replace("btn-outline-primary", "btn-success");
    setTimeout(() => {
      btn.textContent = original;
      btn.classList.replace("btn-success", "btn-outline-primary");
    }, 2000);
  });
}

// ---------------------------------------------------------------------------
// Placeholder detection (template create/edit form)
// ---------------------------------------------------------------------------

const PLACEHOLDER_RE = /\{(\w+)\}/g;

// Attribute string mirroring the autofill_guard() macro in
// templates/_macros.html — the ph_options_* textarea is built here in JS, so
// Jinja can't reach it. Keep this list in sync with the macro's.
const AUTOFILL_GUARD_ATTRS =
  'autocomplete="off" data-1p-ignore data-lpignore="true" data-bwignore="true" data-protonpass-ignore="true" data-form-type="other"';

function initPlaceholderDetection(existing, autofillGuard) {
  const bodyEl = document.getElementById("body");
  if (!bodyEl) return;

  const guardAttrs = autofillGuard ? AUTOFILL_GUARD_ATTRS : "";

  // Build lookup from existing placeholder config (edit mode)
  const existingMap = {};
  (existing || []).forEach((ph) => {
    existingMap[ph.name] = ph;
  });

  function render() {
    const container = document.getElementById("placeholderConfig");
    const body = bodyEl.value;
    const seen = new Set();
    const names = [];

    let match;
    PLACEHOLDER_RE.lastIndex = 0;
    while ((match = PLACEHOLDER_RE.exec(body)) !== null) {
      if (!seen.has(match[1])) {
        seen.add(match[1]);
        names.push(match[1]);
      }
    }

    if (names.length === 0) {
      container.innerHTML =
        '<p class="text-muted fst-italic">No placeholders detected yet.</p>';
      return;
    }

    container.innerHTML = names
      .map((name) => {
        const ex = existingMap[name];
        const isFreeform = !ex || ex.input_type === "freeform";
        const options =
          ex && ex.options ? ex.options.join("\n") : "";

        return `
      <div class="card mb-3">
        <div class="card-body">
          <h6 class="card-title"><code>{${name}}</code></h6>
          <div class="form-check form-check-inline">
            <input class="form-check-input" type="radio"
                   name="ph_type_${name}" id="ph_free_${name}"
                   value="freeform" ${isFreeform ? "checked" : ""}
                   onchange="toggleOptions('${name}')">
            <label class="form-check-label" for="ph_free_${name}">Freeform</label>
          </div>
          <div class="form-check form-check-inline">
            <input class="form-check-input" type="radio"
                   name="ph_type_${name}" id="ph_dd_${name}"
                   value="dropdown" ${!isFreeform ? "checked" : ""}
                   onchange="toggleOptions('${name}')">
            <label class="form-check-label" for="ph_dd_${name}">Dropdown</label>
          </div>
          <div id="opts_${name}" class="mt-2" style="display: ${!isFreeform ? "block" : "none"}">
            <label class="form-label small">Options (one per line)</label>
            <textarea class="form-control form-control-sm" name="ph_options_${name}"
                      rows="3" placeholder="Good&#10;Great&#10;Needs improvement"
                      ${guardAttrs}>${options}</textarea>
          </div>
        </div>
      </div>`;
      })
      .join("");
  }

  bodyEl.addEventListener("input", render);
  // Initial render (for edit mode or pre-filled body)
  render();
}

// ---------------------------------------------------------------------------
// Container reordering
// ---------------------------------------------------------------------------

function initContainerReorder() {
  const list = document.getElementById("containerList");
  if (!list) return;

  Sortable.create(list, {
    handle: ".container-drag-handle",
    animation: 150,
    filter: ".no-drag",
    onEnd: function () {
      const order = Array.from(
        list.querySelectorAll(".accordion-item:not(.no-drag)")
      ).map((el) => el.dataset.id);
      fetch("/containers/reorder", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(order),
      });
    },
  });
}

// ---------------------------------------------------------------------------
// Template list reordering (scoped per accordion section)
// ---------------------------------------------------------------------------

function initTemplateReorder() {
  const lists = document.querySelectorAll(".template-list");
  lists.forEach((list) => {
    Sortable.create(list, {
      handle: ".drag-handle",
      animation: 150,
      onEnd: function () {
        const order = Array.from(list.children).map((el) => el.dataset.id);
        fetch("/templates/reorder", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(order),
        });
      },
    });
  });
}

function toggleOptions(name) {
  const isDropdown = document.getElementById(`ph_dd_${name}`).checked;
  document.getElementById(`opts_${name}`).style.display = isDropdown
    ? "block"
    : "none";
}

// ---------------------------------------------------------------------------
// Template name filter
// ---------------------------------------------------------------------------

/**
 * Check whether a template name contains a case-insensitive filter query.
 *
 * @param {string} name - Template name to search.
 * @param {string} query - Filter text entered by the user.
 * @returns {boolean} Whether the template matches the query.
 */
function templateMatchesFilter(name, query) {
  if (!query) return true;
  return name.toLowerCase().includes(query.toLowerCase());
}

/**
 * Check whether a template's tags include any of the applied tags.
 *
 * @param {string[]} tags - Template tags.
 * @param {string[]} applied - Tags chosen in the filter.
 * @returns {boolean} True when no tags are applied or any tag matches
 *   (case-insensitive).
 */
function templateMatchesTags(tags, applied) {
  if (!applied.length) return true;
  const wanted = new Set(applied.map((t) => t.toLowerCase()));
  return tags.some((t) => wanted.has(t.toLowerCase()));
}

/**
 * Read a template row's tags from its data-tags JSON attribute.
 *
 * @param {Element} row - Template list row.
 * @returns {string[]} Tags, or an empty list.
 */
function rowTags(row) {
  try {
    const tags = JSON.parse(row.dataset.tags || "[]");
    return Array.isArray(tags) ? tags : [];
  } catch (_) {
    return [];
  }
}

/** Combine template name, container, tag, and ranking filters when present. */
function initTemplateFilter() {
  const input = document.getElementById("templateFilter");
  const clearBtn = document.getElementById("clearFilterBtn");
  const noResults = document.getElementById("noFilterResults");
  const containerSelect = document.getElementById("containerFilter");
  const rankingSelect = document.getElementById("rankingFilter");
  const rankSelect = document.getElementById("rankFilter");
  const tagForm = document.getElementById("tagFilterForm");
  const tagToggle = document.getElementById("tagFilterToggle");
  const tagReset = document.getElementById("tagFilterReset");
  let appliedTags = [];
  if (!input || !clearBtn || !noResults) return;

  /** Restore all accordion sections to their collapsed state. */
  function collapseAll() {
    document
      .querySelectorAll(".accordion-collapse")
      .forEach((el) => el.classList.remove("show"));
    document.querySelectorAll(".accordion-button").forEach((btn) => {
      btn.classList.add("collapsed");
      btn.setAttribute("aria-expanded", "false");
    });
  }

  /**
   * Expand an accordion item so its matching templates are visible.
   *
   * @param {Element} accordionItem - Accordion item containing a match.
   */
  function expandContainer(accordionItem) {
    const collapseEl = accordionItem.querySelector(".accordion-collapse");
    const button = accordionItem.querySelector(".accordion-button");
    if (collapseEl) collapseEl.classList.add("show");
    if (button) {
      button.classList.remove("collapsed");
      button.setAttribute("aria-expanded", "true");
    }
  }

  /**
   * Key identifying an accordion item for the container dropdown.
   *
   * @param {Element} item - Accordion item.
   * @returns {string} Container id, or "uncategorized".
   */
  function containerKey(item) {
    return item.dataset.id || "uncategorized";
  }

  /** Apply name, container, tag, and ranking filters to templates and containers. */
  function applyFilter() {
    const query = input.value.trim();
    const hasQuery = query.length > 0;
    const selected = containerSelect ? containerSelect.value : "";
    const hasTags = appliedTags.length > 0;
    // Name, tag, and ranking filters narrow down to matching templates.
    const ranking = rankingSelect ? rankingSelect.value : "";
    const rank = rankSelect ? rankSelect.value : "";
    const narrowing = hasQuery || hasTags || Boolean(ranking);
    clearBtn.classList.toggle("d-none", !narrowing && !selected);

    if (!narrowing && !selected) {
      document
        .querySelectorAll(".list-group-item[data-name]")
        .forEach((row) => row.classList.remove("d-none"));
      document
        .querySelectorAll(".accordion-item")
        .forEach((item) => item.classList.remove("d-none"));
      collapseAll();
      noResults.classList.add("d-none");
      return;
    }

    collapseAll();
    let anyMatch = false;

    document.querySelectorAll(".accordion-item").forEach((item) => {
      const inContainer = !selected || containerKey(item) === selected;
      const rows = item.querySelectorAll(".list-group-item[data-name]");
      let itemHasMatch = false;

      rows.forEach((row) => {
        const matches =
          inContainer &&
          templateMatchesFilter(row.dataset.name, query) &&
          templateMatchesTags(rowTags(row), appliedTags) &&
          (!ranking || (ranking === "unranked"
            ? !row.dataset.rankingScale
            : row.dataset.rankingScale === ranking && (!rank || row.dataset.rankingRank === rank)));
        row.classList.toggle("d-none", !matches);
        if (matches) itemHasMatch = true;
      });

      // A chosen container stays visible (with its content) even when empty,
      // unless a name or tag filter rules out all of its templates.
      const visible = inContainer && (narrowing ? itemHasMatch : true);
      item.classList.toggle("d-none", !visible);
      if (visible) {
        expandContainer(item);
        anyMatch = true;
      }
    });

    noResults.classList.toggle("d-none", anyMatch);
  }

  /** Show how many tags are applied on the Tags button. */
  function updateTagToggle() {
    if (!tagToggle) return;
    tagToggle.textContent = appliedTags.length ? `Tags (${appliedTags.length})` : "Tags";
    tagToggle.classList.toggle("btn-primary", appliedTags.length > 0);
    tagToggle.classList.toggle("btn-outline-secondary", appliedTags.length === 0);
  }

  /** Apply the checked tags from the tag form. */
  function applyTags() {
    appliedTags = Array.from(
      tagForm.querySelectorAll(".tag-filter-option:checked"),
      (box) => box.value
    );
    updateTagToggle();
    applyFilter();
  }

  /** Uncheck every tag and drop the tag filter. */
  function resetTags() {
    if (tagForm) {
      tagForm
        .querySelectorAll(".tag-filter-option")
        .forEach((box) => { box.checked = false; });
    }
    appliedTags = [];
    updateTagToggle();
  }

  /** Clear all filters, restore the list, and return focus to the name query. */
  function clearFilter() {
    input.value = "";
    if (containerSelect) containerSelect.value = "";
    if (rankingSelect) {
      rankingSelect.value = "";
      rankingSelect.dispatchEvent(new rankingSelect.ownerDocument.defaultView.Event("change"));
    }
    if (rankSelect) rankSelect.value = "";
    resetTags();
    applyFilter();
    input.focus();
  }

  input.addEventListener("input", applyFilter);
  clearBtn.addEventListener("click", clearFilter);
  if (containerSelect) containerSelect.addEventListener("change", applyFilter);
  if (rankingSelect) rankingSelect.addEventListener("change", applyFilter);
  if (rankSelect) rankSelect.addEventListener("change", applyFilter);
  if (tagForm) {
    tagForm.addEventListener("submit", (event) => {
      event.preventDefault();
      applyTags();
    });
  }
  if (tagReset) {
    tagReset.addEventListener("click", () => {
      resetTags();
      applyFilter();
    });
  }
}

/**
 * Let the existing-tag buttons on the template form add their tag to the
 * comma-separated tags field (once).
 *
 * @param {Document} [doc] - Document containing the form.
 */
function initTagSuggestions(doc = document) {
  const input = doc.getElementById("tags");
  if (!input) return;
  doc.querySelectorAll(".tag-suggestion").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tags = input.value.split(",").map((t) => t.trim()).filter(Boolean);
      const tag = btn.dataset.tag;
      if (!tags.some((t) => t.toLowerCase() === tag.toLowerCase())) tags.push(tag);
      input.value = tags.join(", ");
      input.focus();
    });
  });
}

/**
 * Wire the "copy template" modal so it targets whichever template's Copy
 * button opened it.
 *
 * @param {Document} [doc] - Document containing the modal.
 */
function initCopyModal(doc = document) {
  const modal = doc.getElementById("copyTemplateModal");
  const form = doc.getElementById("copyTemplateForm");
  const nameEl = doc.getElementById("copyTemplateName");
  const select = doc.getElementById("copyTemplateContainer");
  if (!modal || !form || !nameEl || !select) return;

  modal.addEventListener("show.bs.modal", (event) => {
    const trigger = event.relatedTarget;
    if (!trigger) return;
    form.setAttribute(
      "action",
      modal.dataset.actionTemplate.replace("__ID__", trigger.dataset.templateId)
    );
    nameEl.textContent = trigger.dataset.templateName;
    select.value = trigger.dataset.containerId || "";
  });
}

/**
 * Wire the "copy container" modal so it targets whichever container's Copy
 * button opened it and suggests a default name for the new container.
 *
 * @param {Document} [doc] - Document containing the modal.
 */
function initCopyContainerModal(doc = document) {
  const modal = doc.getElementById("copyContainerModal");
  const form = doc.getElementById("copyContainerForm");
  const sourceEl = doc.getElementById("copyContainerSource");
  const nameInput = doc.getElementById("copyContainerName");
  if (!modal || !form || !sourceEl || !nameInput) return;

  modal.addEventListener("show.bs.modal", (event) => {
    const trigger = event.relatedTarget;
    if (!trigger) return;
    form.setAttribute(
      "action",
      modal.dataset.actionTemplate.replace("__ID__", trigger.dataset.containerId)
    );
    sourceEl.textContent = trigger.dataset.containerName;
    nameInput.value = `${trigger.dataset.containerName} (copy)`;
  });
}

// ---------------------------------------------------------------------------
// Missing-placeholder confirmation
// ---------------------------------------------------------------------------

/**
 * Check whether a template body contains at least one {placeholder}.
 *
 * @param {string} body - Template body text.
 * @returns {boolean} Whether a placeholder is present.
 */
function bodyHasPlaceholder(body) {
  return /\{\w+\}/.test(body);
}

/**
 * Ask for confirmation before saving a template that has no placeholders.
 *
 * @param {Document} [doc] - Document containing the template form.
 * @param {function(string): boolean} [confirmFn] - Confirmation prompt.
 */
function initPlaceholderConfirm(doc = document, confirmFn = (msg) => window.confirm(msg)) {
  const form = doc.getElementById("templateForm");
  const body = doc.getElementById("body");
  if (!form || !body) return;

  form.addEventListener("submit", (event) => {
    if (bodyHasPlaceholder(body.value)) return;
    const ok = confirmFn(
      "This template has no placeholders (e.g. {name}), so every generated feedback will be identical. Save it anyway?"
    );
    if (!ok) event.preventDefault();
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = {
    templateMatchesFilter,
    templateMatchesTags,
    initTemplateFilter,
    initTagSuggestions,
    initCopyModal,
    initCopyContainerModal,
    bodyHasPlaceholder,
    initPlaceholderConfirm,
  };
}
