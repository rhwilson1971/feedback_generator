# Light / Dark / System Theme Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a light theme alongside the existing dark theme, and a **Theme** setting on `/settings` with three choices — Light, Dark, System — persisted like every other setting.

**Architecture:** The preference (`light` | `dark` | `system`) is stored in the existing Mongo `settings` document and exposed to templates through the existing `settings` context processor. `base.html` stamps it on `<html data-theme-pref="…">`. A tiny **blocking** script in `<head>` (`static/theme.js`) resolves the preference (using `prefers-color-scheme` for `system`) and sets `data-theme` and Bootstrap's `data-bs-theme` on `<html>` before first paint, so there is no flash of the wrong theme. `static/style.css` defines dark tokens on `:root` and light tokens on `:root[data-theme="light"]`; every hard-coded colour in the stylesheet moves into a token so a theme is *only* a token block.

**Tech Stack:** Flask/Jinja2, PyMongo, Bootstrap 5.3.3 (`data-bs-theme`), vanilla CSS custom properties, `node --test` + jsdom (JS tests), stdlib `unittest` (Flask tests — no new dependencies).

**Decisions already made (do not re-litigate):**
- Storage: existing Mongo `settings` doc, new key `theme`. Server-side, not `localStorage`, for consistency with the settings page and so the server can pre-render explicit choices.
- Default: `system`. (The app is dark today, so a dark-mode OS sees no change. Flip `DEFAULT_SETTINGS["theme"]` to `"dark"` if you want zero change for everyone.)
- `system` follows the OS **live** — changing OS appearance while the app is open updates it without a reload.
- The radio group on the settings page **previews instantly**; it is only persisted when the user clicks Save Settings.
- No `@media (prefers-color-scheme)` CSS fallback for the JS-disabled case. With JS off, `system` renders dark. (Avoids duplicating the light token block.)
- Palette: keep the warm mauve accent (`#715A5A`) and teal success; light theme is a warm off-white with dark charcoal text.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `static/theme.js` | **New** | `resolveTheme`, `applyTheme`, `initTheme`, `initThemePicker`; auto-runs in the browser |
| `tests/theme.test.js` | **New** | jsdom tests for the above |
| `app.py` | Modify | `THEME_CHOICES`, `DEFAULT_SETTINGS["theme"]`, validation in `get_settings()` and `update_settings()` |
| `tests/test_settings_theme.py` | **New** | `unittest` tests for the setting (defaults, sanitising, save, render) |
| `templates/base.html` | Modify | `<html>` attributes, blocking `<script src=theme.js>` in `<head>`, drop `navbar-dark` |
| `templates/settings.html` | Modify | "Appearance" card with Light / Dark / System radios |
| `static/style.css` | Modify | Tokenise all literal colours; add `:root[data-theme="light"]` block |
| `README.md` | Modify | One-line feature mention |

---

## Task 1: `theme.js` (pure logic, test first)

**Files:**
- Create: `static/theme.js`
- Test: `tests/theme.test.js`

- [ ] **Step 1: Write the failing tests**

Create `tests/theme.test.js`:

```js
const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const {
  resolveTheme,
  applyTheme,
  initTheme,
  initThemePicker,
} = require("../static/theme.js");

/**
 * Build a jsdom window with a controllable prefers-color-scheme media query.
 *
 * @param {string} pref - Value for data-theme-pref on <html>.
 * @param {boolean} prefersDark - Initial OS dark-mode state.
 * @returns {{window: object, setOsDark: function(boolean): void}}
 */
function buildWindow(pref, prefersDark) {
  const dom = new JSDOM(`<!DOCTYPE html>
    <html data-theme-pref="${pref}"><body>
      <input type="radio" name="theme" value="light">
      <input type="radio" name="theme" value="dark">
      <input type="radio" name="theme" value="system">
    </body></html>`);
  const { window } = dom;
  const listeners = [];
  const mql = {
    matches: prefersDark,
    addEventListener: (_type, fn) => listeners.push(fn),
  };
  window.matchMedia = () => mql;
  return {
    window,
    setOsDark(value) {
      mql.matches = value;
      listeners.forEach((fn) => fn({ matches: value }));
    },
  };
}

test("resolveTheme returns explicit choices unchanged", () => {
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("dark", false), "dark");
});

test("resolveTheme follows the OS for system", () => {
  assert.equal(resolveTheme("system", true), "dark");
  assert.equal(resolveTheme("system", false), "light");
});

test("resolveTheme treats unknown values as system", () => {
  assert.equal(resolveTheme("purple", true), "dark");
  assert.equal(resolveTheme(undefined, false), "light");
});

test("applyTheme sets data-theme and data-bs-theme", () => {
  const { window } = buildWindow("light", false);
  const root = window.document.documentElement;
  const theme = applyTheme(root, "dark", false);
  assert.equal(theme, "dark");
  assert.equal(root.getAttribute("data-theme"), "dark");
  assert.equal(root.getAttribute("data-bs-theme"), "dark");
});

test("initTheme applies the stored preference immediately", () => {
  const { window } = buildWindow("system", true);
  initTheme(window);
  assert.equal(window.document.documentElement.getAttribute("data-theme"), "dark");
});

test("initTheme live-updates when the OS changes and pref is system", () => {
  const { window, setOsDark } = buildWindow("system", true);
  initTheme(window);
  setOsDark(false);
  assert.equal(window.document.documentElement.getAttribute("data-theme"), "light");
});

test("initTheme ignores OS changes when pref is explicit", () => {
  const { window, setOsDark } = buildWindow("light", false);
  initTheme(window);
  setOsDark(true);
  assert.equal(window.document.documentElement.getAttribute("data-theme"), "light");
});

test("initThemePicker previews the chosen radio immediately", () => {
  const { window } = buildWindow("light", false);
  const apply = initTheme(window);
  initThemePicker(window.document, apply);

  const dark = window.document.querySelector('input[value="dark"]');
  dark.checked = true;
  dark.dispatchEvent(new window.Event("change", { bubbles: true }));

  const root = window.document.documentElement;
  assert.equal(root.getAttribute("data-theme"), "dark");
  assert.equal(root.getAttribute("data-theme-pref"), "dark");
});
```

- [ ] **Step 2: Run to verify it fails**

Run: `npm test`
Expected: FAIL — `Cannot find module '../static/theme.js'` (the existing `templateFilter` tests still pass).

- [ ] **Step 3: Write the implementation**

Create `static/theme.js`:

```js
// Theme resolution. Loaded as a blocking <script> in <head> so the theme is
// set before first paint. Exports mirror the pattern used in app.js.

const THEME_QUERY = "(prefers-color-scheme: dark)";

/**
 * Resolve a stored preference to a concrete theme.
 *
 * @param {string} pref - "light", "dark", or "system" (anything else = system).
 * @param {boolean} prefersDark - Whether the OS currently prefers dark.
 * @returns {"light"|"dark"} The theme to render.
 */
function resolveTheme(pref, prefersDark) {
  if (pref === "light" || pref === "dark") return pref;
  return prefersDark ? "dark" : "light";
}

/**
 * Stamp the resolved theme on the root element for our CSS and Bootstrap's.
 *
 * @param {Element} root - The <html> element.
 * @param {string} pref - Stored preference.
 * @param {boolean} prefersDark - Current OS preference.
 * @returns {"light"|"dark"} The theme that was applied.
 */
function applyTheme(root, pref, prefersDark) {
  const theme = resolveTheme(pref, prefersDark);
  root.setAttribute("data-theme", theme);
  root.setAttribute("data-bs-theme", theme);
  return theme;
}

/**
 * Apply the preference found on <html data-theme-pref> and keep `system`
 * in sync with the OS.
 *
 * @param {Window} win - Window to read from (injectable for tests).
 * @returns {function(string): string} apply(pref) — re-applies a preference.
 */
function initTheme(win) {
  const root = win.document.documentElement;
  const mql = win.matchMedia(THEME_QUERY);
  const apply = (pref) => applyTheme(root, pref, mql.matches);

  apply(root.getAttribute("data-theme-pref") || "system");
  mql.addEventListener("change", () => {
    if (root.getAttribute("data-theme-pref") === "system") apply("system");
  });
  return apply;
}

/**
 * Preview a theme as soon as a settings radio is chosen (saved on submit).
 *
 * @param {Document} doc - Document containing input[name="theme"] radios.
 * @param {function(string): string} apply - Function returned by initTheme.
 */
function initThemePicker(doc, apply) {
  doc.querySelectorAll('input[name="theme"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      if (!radio.checked) return;
      doc.documentElement.setAttribute("data-theme-pref", radio.value);
      apply(radio.value);
    });
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { resolveTheme, applyTheme, initTheme, initThemePicker };
} else {
  const applyPref = initTheme(window);
  document.addEventListener("DOMContentLoaded", () =>
    initThemePicker(document, applyPref)
  );
}
```

- [ ] **Step 4: Run to verify it passes**

Run: `npm test`
Expected: PASS — all `theme.test.js` tests plus the existing `templateFilter` tests.

- [ ] **Step 5: Commit**

```bash
git checkout -b feature/theme-support
git add static/theme.js tests/theme.test.js
git commit -m "feat: add theme resolution script with tests"
```

---

## Task 2: `theme` setting on the backend

**Files:**
- Modify: `app.py` (imports/constants near line 19-25, `get_settings` ~line 63, `update_settings` ~line 346)
- Test: `tests/test_settings_theme.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_settings_theme.py`:

```python
import unittest
from unittest.mock import patch

import app as app_module


class FakeCollection:
    """Minimal stand-in for the Mongo settings collection."""

    def __init__(self, doc=None):
        self.doc = doc

    def find_one(self, _query):
        return self.doc

    def update_one(self, _query, update, upsert=False):
        self.doc = {**(self.doc or {}), **update["$set"]}


class ThemeSettingTests(unittest.TestCase):
    def setUp(self):
        self.collection = FakeCollection()
        patcher = patch.object(
            app_module, "get_settings_collection", return_value=self.collection
        )
        patcher.start()
        self.addCleanup(patcher.stop)
        self.client = app_module.app.test_client()

    def test_default_is_system(self):
        self.assertEqual(app_module.get_settings()["theme"], "system")

    def test_stored_value_is_returned(self):
        self.collection.doc = {"theme": "dark"}
        self.assertEqual(app_module.get_settings()["theme"], "dark")

    def test_corrupt_stored_value_falls_back_to_default(self):
        self.collection.doc = {"theme": "purple"}
        self.assertEqual(app_module.get_settings()["theme"], "system")

    def test_post_saves_valid_theme(self):
        self.client.post("/settings", data={"theme": "light"})
        self.assertEqual(self.collection.doc["theme"], "light")

    def test_post_ignores_invalid_theme(self):
        self.collection.doc = {"theme": "dark"}
        self.client.post("/settings", data={"theme": "purple"})
        self.assertEqual(self.collection.doc["theme"], "dark")

    def test_post_without_theme_keeps_existing(self):
        self.collection.doc = {"theme": "light"}
        self.client.post("/settings", data={})
        self.assertEqual(self.collection.doc["theme"], "light")

    def test_html_carries_preference_and_explicit_theme(self):
        self.collection.doc = {"theme": "light"}
        html = self.client.get("/settings").get_data(as_text=True)
        self.assertIn('data-theme-pref="light"', html)
        self.assertIn('data-theme="light"', html)

    def test_system_pref_leaves_data_theme_to_script(self):
        html = self.client.get("/settings").get_data(as_text=True)
        self.assertIn('data-theme-pref="system"', html)
        self.assertNotIn('data-theme="', html)


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python -m unittest tests.test_settings_theme -v`
Expected: FAIL — `KeyError: 'theme'` (and the HTML tests fail; the `<html>` attributes come in Task 3, so those two stay red until then).

- [ ] **Step 3: Implement the setting**

In `app.py`, replace the `DEFAULT_SETTINGS` block:

```python
THEME_CHOICES = ("light", "dark", "system")

# Every setting must have an entry here. get_settings() layers stored values
# over these defaults, so a missing key never raises.
DEFAULT_SETTINGS = {
    "disable_password_manager_autofill": False,
    "theme": "system",
}
```

(Keep the existing comment above `DEFAULT_SETTINGS` as-is; only add `THEME_CHOICES` above it and the `"theme"` entry.)

In `get_settings()`, before `return settings`, add:

```python
    if settings["theme"] not in THEME_CHOICES:
        settings["theme"] = DEFAULT_SETTINGS["theme"]
```

Replace the body of `update_settings()`:

```python
@app.route("/settings", methods=["POST"])
def update_settings():
    updates = {
        "disable_password_manager_autofill":
            "disable_password_manager_autofill" in request.form,
    }
    theme = request.form.get("theme", "")
    if theme in THEME_CHOICES:
        updates["theme"] = theme
    save_settings(updates)
    flash("Settings saved.", "success")
    return redirect(url_for("settings_page"))
```

- [ ] **Step 4: Run to verify it passes (except the two HTML tests)**

Run: `.venv/bin/python -m unittest tests.test_settings_theme -v`
Expected: 6 pass; `test_html_carries_preference_and_explicit_theme` and `test_system_pref_leaves_data_theme_to_script` FAIL (fixed in Task 3).

- [ ] **Step 5: Commit**

```bash
git add app.py tests/test_settings_theme.py
git commit -m "feat: add theme setting with validation"
```

---

## Task 3: Wire the theme into `base.html` and the settings page

**Files:**
- Modify: `templates/base.html` (line 2 `<html>`, `<head>`, navbar class)
- Modify: `templates/settings.html`

- [ ] **Step 1: Update `base.html`**

Replace `<html lang="en">` with:

```html
<html lang="en" data-theme-pref="{{ settings.theme }}"{% if settings.theme != 'system' %} data-theme="{{ settings.theme }}" data-bs-theme="{{ settings.theme }}"{% endif %}>
```

In `<head>`, immediately **after** the `style.css` `<link>`, add (no `defer`/`async` — it must block so the theme is set before paint):

```html
  <script src="{{ url_for('static', filename='theme.js') }}"></script>
```

On the `<nav>`, change `navbar navbar-expand-sm navbar-dark bg-app mb-4` to `navbar navbar-expand-sm bg-app mb-4` (`navbar-dark` forces light text variables that are wrong in the light theme; the navbar colours are already set by our tokens).

- [ ] **Step 2: Add the Appearance card to `settings.html`**

Insert **above** the existing "Privacy & Forms" card, inside the `<form>`:

```html
  <div class="card mb-4">
    <div class="card-header">Appearance</div>
    <div class="card-body">
      <div class="settings-row" role="radiogroup" aria-labelledby="theme-label">
        <div id="theme-label" class="form-label">Theme</div>
        {% for value, label in [("light", "Light"), ("dark", "Dark"), ("system", "System (match my device)")] %}
        <div class="form-check">
          <input class="form-check-input" type="radio" name="theme"
                 id="theme_{{ value }}" value="{{ value }}"
                 {% if settings.theme == value %}checked{% endif %}>
          <label class="form-check-label" for="theme_{{ value }}">{{ label }}</label>
        </div>
        {% endfor %}
        <div class="form-text ms-0">
          System follows your operating system's light/dark setting and updates
          automatically when it changes.
        </div>
      </div>
    </div>
  </div>
```

- [ ] **Step 3: Run tests**

Run: `.venv/bin/python -m unittest tests.test_settings_theme -v && npm test`
Expected: all PASS, including the two HTML tests that were red after Task 2.

- [ ] **Step 4: Commit**

```bash
git add templates/base.html templates/settings.html
git commit -m "feat: apply theme on <html> and add appearance setting UI"
```

---

## Task 4: Tokenise `style.css` (dark must look identical)

This task is a **pure refactor**: after it, the app is pixel-for-pixel the same in dark. No light theme yet.

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Capture the "before" state**

Run the app (`.venv/bin/flask --app app run --port 5010`), open `/`, `/settings`, a template's Generate page, and the template form. Take a screenshot of each (or note them) to compare against after Step 4.

- [ ] **Step 2: Add the new tokens to the `:root` block**

Append inside the existing `:root { … }` (after `--transition`):

```css
  /* Derived colours (formerly literals in rules below) */
  --on-accent:          #D3DAD9;
  --surface-tint:       rgba(0, 0, 0, 0.15);
  --code-bg:            rgba(211, 218, 217, 0.08);
  --code-fg:            #a8c0be;
  --border-faint:       rgba(211, 218, 217, 0.08);
  --check-border:       rgba(211, 218, 217, 0.30);
  --focus-ring:         rgba(113, 90, 90, 0.20);
  --success:            #4e7268;
  --success-hover:      #5d877c;
  --success-ring:       rgba(78, 114, 104, 0.25);
  --btn-secondary-hover:#5a586a;
  --outline-border:     rgba(211, 218, 217, 0.25);
  --outline-border-hover: rgba(211, 218, 217, 0.35);
  --accent-text:        #c49e9e;
  --danger-border:      rgba(180, 80, 80, 0.40);
  --danger-text:        rgba(210, 110, 110, 0.80);
  --danger-bg-hover:    rgba(180, 80, 80, 0.15);
  --danger-border-hover:rgba(180, 80, 80, 0.60);
  --danger-text-hover:  rgba(230, 130, 130, 0.95);
  --danger-accent:      rgba(180, 80, 80, 0.70);
  --warning:            #9e8a4a;
  --icon-invert:        1;  /* 1 = flip dark glyph images to light */
  --select-arrow: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23D3DAD9' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m2 5 6 6 6-6'/%3e%3c/svg%3e");
  --switch-knob:    url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%23D3DAD9' fill-opacity='0.55'/%3e%3c/svg%3e");
  --switch-knob-on: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%23D3DAD9'/%3e%3c/svg%3e");
```

- [ ] **Step 3: Replace literals with tokens via a script**

Save as `scripts_tmp/tokenise.py` in the scratchpad (do **not** commit it) and run `python3 tokenise.py` from the repo root. It asserts the expected number of replacements so a mismatch fails loudly.

```python
import re

PATH = "static/style.css"
css = open(PATH).read()

# Only touch the region after the :root block so the token definitions
# themselves are not rewritten.
head_end = css.index("}", css.index(":root")) + 1
head, body = css[:head_end], css[head_end:]

# (old, new, expected_count)
simple = [
    ("background-color: rgba(211, 218, 217, 0.08);", "background-color: var(--code-bg);", 2),
    ("border-color: rgba(211, 218, 217, 0.08);", "border-color: var(--border-faint);", 1),
    ("color: #a8c0be;", "color: var(--code-fg);", 2),
    ("background-color: rgba(0, 0, 0, 0.15);", "background-color: var(--surface-tint);", 2),
    ("rgba(113, 90, 90, 0.20)", "var(--focus-ring)", 3),
    ("rgba(113, 90, 90, 0.25)", "var(--focus-ring)", 1),
    ("border-color: rgba(211, 218, 217, 0.30);", "border-color: var(--check-border);", 1),
    ("#4e7268", "var(--success)", 3),
    ("#5d877c", "var(--success-hover)", 2),
    ("rgba(78, 114, 104, 0.25)", "var(--success-ring)", 1),
    ("#5a586a", "var(--btn-secondary-hover)", 1),
    ("rgba(211, 218, 217, 0.25)", "var(--outline-border)", 1),
    ("rgba(211, 218, 217, 0.35)", "var(--outline-border-hover)", 1),
    ("#c49e9e", "var(--accent-text)", 1),
    ("rgba(180, 80, 80, 0.40)", "var(--danger-border)", 1),
    ("rgba(210, 110, 110, 0.80)", "var(--danger-text)", 1),
    ("rgba(180, 80, 80, 0.15)", "var(--danger-bg-hover)", 1),
    ("rgba(180, 80, 80, 0.60)", "var(--danger-border-hover)", 1),
    ("rgba(230, 130, 130, 0.95)", "var(--danger-text-hover)", 1),
    ("rgba(180, 80, 80, 0.70)", "var(--danger-accent)", 1),
    ("#9e8a4a", "var(--warning)", 1),
    # icon filters: invert amount now comes from a token
    ("filter: invert(1) opacity(0.55);", "filter: invert(var(--icon-invert)) opacity(0.55);", 1),
    ("filter: invert(1) opacity(0.90);", "filter: invert(var(--icon-invert)) opacity(0.90);", 1),
    ("filter: invert(1) opacity(0.5);", "filter: invert(var(--icon-invert)) opacity(0.5);", 1),
]
for old, new, expected in simple:
    found = body.count(old)
    assert found == expected, f"{old!r}: expected {expected}, found {found}"
    body = body.replace(old, new)

# Select arrow and switch-knob data URIs -> tokens.
uri_re = re.compile(r'url\("data:image/svg\+xml,[^"]*"\)')
def swap_uri(selector_re, token):
    global body
    pattern = re.compile(
        r"(" + selector_re + r"\s*\{[^}]*?background-image:\s*)" + uri_re.pattern,
        re.M,
    )
    body, n = pattern.subn(r"\1var(" + token + ")", body)
    assert n == 1, f"{selector_re}: expected 1, found {n}"

swap_uri(r"^\.form-select", "--select-arrow")
swap_uri(r"^\.form-switch \.form-check-input", "--switch-knob")
swap_uri(r"^\.form-switch \.form-check-input:checked", "--switch-knob-on")

# Text that sits ON an accent/success fill uses --on-accent, not --text-primary.
for sel in [r"\.btn-primary", r"\.btn-primary:focus", r"\.btn-success",
            r"\.btn-success:focus", r"\.btn-outline-primary:focus"]:
    pat = re.compile(r"(^" + sel + r" \{[^}]*?\bcolor:\s*)var\(--text-primary\)", re.M)
    body, n = pat.subn(r"\1var(--on-accent)", body)
    assert n == 1, f"{sel}: expected 1, found {n}"

open(PATH, "w").write(head + body)
print("ok")
```

- [ ] **Step 4: Replace the now-stale switch comment and verify no literals remain**

Delete the comment block above `.form-switch .form-check-input` that starts `/* Bootstrap draws the switch knob from an inline SVG…` (it explained the hex-sync problem that tokens now solve).

Run:
```bash
grep -nE "#[0-9a-fA-F]{3,8}\b|rgba?\(" static/style.css
```
Expected: every hit is on a line inside the `:root { … }` block (tokens, shadows). Anything outside is a missed literal — tokenise it.

Reload the pages from Step 1 in **dark** and compare. Expected: identical except focus rings on `.btn-primary:hover` (0.25 → 0.20 alpha, imperceptible).

- [ ] **Step 5: Commit**

```bash
git add static/style.css
git commit -m "refactor: move hard-coded colours into CSS tokens"
```

---

## Task 5: Light theme token block

**Files:**
- Modify: `static/style.css` (add directly after the `:root { … }` block)

- [ ] **Step 1: Add the light tokens**

```css
/* ── Light theme ────────────────────────────────────────── */
:root[data-theme="light"] {
  --bg-primary:    #F3F1F2;
  --bg-surface:    #FFFFFF;
  --bg-elevated:   #EAE6E8;
  --accent:        #715A5A;
  --accent-hover:  #5c4848;
  --accent-muted:  rgba(113, 90, 90, 0.12);
  --text-primary:  #2B2830;
  --text-muted:    rgba(43, 40, 48, 0.62);
  --border-color:  rgba(43, 40, 48, 0.14);
  --shadow-sm:     0 1px 3px rgba(43, 40, 48, 0.10);
  --shadow-md:     0 4px 12px rgba(43, 40, 48, 0.14);

  --on-accent:          #FFFFFF;
  --surface-tint:       rgba(43, 40, 48, 0.04);
  --code-bg:            rgba(43, 40, 48, 0.07);
  --code-fg:            #4a6b67;
  --border-faint:       rgba(43, 40, 48, 0.08);
  --check-border:       rgba(43, 40, 48, 0.35);
  --focus-ring:         rgba(113, 90, 90, 0.25);
  --success:            #3f6b5f;
  --success-hover:      #34594f;
  --success-ring:       rgba(63, 107, 95, 0.25);
  --btn-secondary-hover:#DDD8DB;
  --outline-border:     rgba(43, 40, 48, 0.25);
  --outline-border-hover: rgba(43, 40, 48, 0.40);
  --accent-text:        #715A5A;
  --danger-border:      rgba(176, 58, 58, 0.45);
  --danger-text:        #b03a3a;
  --danger-bg-hover:    rgba(176, 58, 58, 0.10);
  --danger-border-hover:rgba(176, 58, 58, 0.70);
  --danger-text-hover:  #8f2a2a;
  --danger-accent:      rgba(176, 58, 58, 0.80);
  --warning:            #8a7430;
  --icon-invert:        0;
  --select-arrow: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%232B2830' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m2 5 6 6 6-6'/%3e%3c/svg%3e");
  --switch-knob:    url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%232B2830' fill-opacity='0.45'/%3e%3c/svg%3e");
  --switch-knob-on: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='-4 -4 8 8'%3e%3ccircle r='3' fill='%23FFFFFF'/%3e%3c/svg%3e");
}
```

- [ ] **Step 2: Manually verify every page in light**

Start the app, go to `/settings`, pick **Light** (should switch instantly), Save, then check each page:

| Page | Check |
|---|---|
| `/` | Accordion headers, category badge, count text, icon buttons (edit/trash), drag handles, filter input, `+ New Container` |
| `/settings` | Radio + switch visible, switch knob visible on and off, card header tint |
| `/generate/<id>` | Inputs, selects (arrow visible), result textarea, Copy button |
| Template form | `code` chips, placeholder cards, `<select>` arrow |
| Flash message | Save a setting: alert left border visible, close ✕ visible |

Expected: no unreadable text (aim for ≥4.5:1 contrast), no white-on-white or dark-on-dark, no leftover dark rectangles.

- [ ] **Step 3: Verify System mode**

Set **System**, Save. Toggle macOS *System Settings → Appearance* between Light and Dark **with the app open**.
Expected: the app follows within a moment, without reload. Then hard-reload in each OS mode: no flash of the wrong theme.

- [ ] **Step 4: Verify persistence and no-flash for explicit choices**

Set **Light**, Save, hard-reload repeatedly with OS set to Dark.
Expected: never flashes dark. Repeat for **Dark** with OS Light.

- [ ] **Step 5: Commit**

```bash
git add static/style.css
git commit -m "feat: add light theme"
```

---

## Task 6: Docs and final verification

**Files:**
- Modify: `README.md`

- [ ] **Step 1:** Add to the Features list in `README.md`:

```markdown
- **Light, dark, or system theme** — Choose in Settings; System follows your device
```

- [ ] **Step 2: Run everything**

Run: `npm test && .venv/bin/python -m unittest tests.test_settings_theme -v`
Expected: all pass.

- [ ] **Step 3: Commit and open PR**

```bash
git add README.md
git commit -m "docs: mention theme setting"
git push -u origin feature/theme-support
gh pr create --base main --title "Add light/dark/system theme setting"
```

---

## Self-Review

**Spec coverage:** light theme (Tasks 4-5), dark retained (Task 4 refactor keeps it identical), settings option with light / dark / system (Tasks 2-3), system-defined follows OS incl. live changes (Task 1 `initTheme`, verified Task 5 Step 3). Persistence (Task 2). No gap found.

**Placeholder scan:** none — every code step has full code; the tokenise script asserts counts so a drifted stylesheet fails loudly instead of silently mis-replacing.

**Consistency:** `THEME_CHOICES` (Task 2) matches the radio values (`light`/`dark`/`system`, Task 3) and `resolveTheme` (Task 1). `data-theme-pref` is written by `base.html` (Task 3), read by `initTheme`, and updated by `initThemePicker` (Task 1). Token names in the Task 4 script match the `:root` additions in Step 2 and the light block in Task 5 (same 30 names in both; `--on-accent`, `--icon-invert`, `--select-arrow`, `--switch-knob`, `--switch-knob-on` included).

**Known risks:**
- The tokenise script's expected counts were taken from the current `style.css`; if it changes before execution, the assertion tells you which line drifted.
- `.accordion-button::after` and `.btn-close` rely on `filter: invert(var(--icon-invert))` — confirm the chevron and ✕ are visible in light (Task 5 Step 2 covers it).
