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

function initPlaceholderDetection(existing) {
  const bodyEl = document.getElementById("body");
  if (!bodyEl) return;

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
                      rows="3" placeholder="Good&#10;Great&#10;Needs improvement">${options}</textarea>
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
// Template list reordering
// ---------------------------------------------------------------------------

function initTemplateReorder() {
  const list = document.getElementById("templateList");
  if (!list) return;

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
}

function toggleOptions(name) {
  const isDropdown = document.getElementById(`ph_dd_${name}`).checked;
  document.getElementById(`opts_${name}`).style.display = isDropdown
    ? "block"
    : "none";
}
