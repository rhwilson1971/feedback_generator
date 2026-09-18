# Settings Page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a `/settings` page to the Feedback Generator. Ship it with one setting — **Disable password manager autofill** — implemented in a way that new settings can be added later by touching one dict and one template block.

**Architecture:** Settings persist as a single document in a new Mongo `settings` collection (`_id: "app"`), read through `get_settings()`, which merges stored values over a `DEFAULT_SETTINGS` dict so a missing key never raises. A Flask **context processor** injects `settings` into every template render, and a Jinja **macro** (`autofill_guard`) emits the autofill-suppression attributes into each form/input tag. Because the attributes are rendered server-side, they are present in the initial HTML — password managers scan the DOM before page JS runs, so a JS-stamped approach would be unreliable.

**Tech Stack:** Flask/Jinja2, PyMongo, Bootstrap 5.3.3 (`form-switch`), vanilla CSS with the existing dark-theme tokens in `static/style.css`

**Decisions already made (do not re-litigate):**
- Storage: Mongo `settings` collection — consistent with `templates`/`containers`, survives cache clears, works across devices.
- Scope: **all** text inputs and textareas app-wide, via one shared macro.
- Default: **Off** (autofill left enabled) so existing installs see no behavior change until the user opts in.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `database.py` | Modify | Add `get_settings_collection()` |
| `app.py` | Modify | `DEFAULT_SETTINGS`, `get_settings()`, `save_settings()`, context processor, `GET/POST /settings` |
| `templates/_macros.html` | **New** | `autofill_guard()` macro |
| `templates/settings.html` | **New** | Settings page UI |
| `templates/base.html` | Modify | Nav link to Settings |
| `templates/generate.html` | Modify | Apply macro to placeholder inputs + form tag |
| `templates/template_form.html` | Modify | Apply macro to name input, body textarea, options textareas + form tag |
| `templates/container_form.html` | Modify | Apply macro to name/category inputs + form tag |
| `static/style.css` | Modify | Dark-theme `.form-switch` knob + `.settings-*` layout |
| `static/app.js` | No change | Setting needs no client-side logic |
| `templates/index.html` | No change | `#templateFilter` already hardcodes `autocomplete="off"` |

---

## Data Model

New collection `settings`, exactly one document, fixed `_id` so concurrent upserts can't create duplicates:

```json
{
  "_id": "app",
  "disable_password_manager_autofill": false,
  "updated_at": "2026-09-17T00:00:00Z"
}
```

No migration is needed: a fresh install has no document, and `get_settings()` returns `DEFAULT_SETTINGS` in that case.

---

## Attribute Reference (used by Task 2)

When the setting is **on**, each guarded form/input receives:

| Attribute | Target |
|---|---|
| `autocomplete="off"` | Browser-native autofill (Chrome may still override on fields its heuristics read as username/email — hence the vendor hooks below) |
| `data-1p-ignore` | 1Password |
| `data-lpignore="true"` | LastPass |
| `data-bwignore="true"` | Bitwarden |
| `data-protonpass-ignore="true"` | Proton Pass |
| `data-form-type="other"` | Dashlane |

Two things to know before implementing:

1. **`autocomplete="off"` does not disable `<datalist>`.** The category field in `container_form.html` keeps its own suggestion list — that is the app's feature, not password-manager autofill, and it must keep working.
2. **Field names still leak heuristics.** A user-authored placeholder named `email` or `name` renders as `name="ph_email"`, which is exactly what Chrome's heuristics latch onto. The `ph_` prefix helps; the vendor attributes are what actually close the gap. Verify empirically in Task 6 rather than assuming.

---

## Task 1: Settings Storage Layer

**Files:**
- Modify: `database.py`
- Modify: `app.py`

- [ ] **Step 1: Add the collection accessor**

  In `database.py`, after `get_containers_collection()`, matching the existing style:

  ```python
  def get_settings_collection():
      return get_db()["settings"]
  ```

- [ ] **Step 2: Import it in `app.py`**

  Extend the existing import:

  ```python
  from database import (
      get_containers_collection,
      get_settings_collection,
      get_templates_collection,
  )
  ```

- [ ] **Step 3: Declare defaults next to `PLACEHOLDER_RE`**

  ```python
  SETTINGS_DOC_ID = "app"

  # Every setting must have an entry here. get_settings() layers stored values
  # over these, so adding a key never breaks an existing install.
  DEFAULT_SETTINGS = {
      "disable_password_manager_autofill": False,
  }
  ```

- [ ] **Step 4: Add `get_settings()` / `save_settings()` to the Helpers section**

  ```python
  def get_settings() -> dict:
      """Return app settings with stored values layered over the defaults."""
      stored = get_settings_collection().find_one({"_id": SETTINGS_DOC_ID}) or {}
      settings = dict(DEFAULT_SETTINGS)
      for key in DEFAULT_SETTINGS:
          if key in stored:
              settings[key] = stored[key]
      return settings


  def save_settings(updates: dict) -> None:
      """Upsert the known settings keys found in `updates`."""
      changes = {k: v for k, v in updates.items() if k in DEFAULT_SETTINGS}
      if not changes:
          return
      changes["updated_at"] = datetime.now(timezone.utc)
      get_settings_collection().update_one(
          {"_id": SETTINGS_DOC_ID},
          {"$set": changes},
          upsert=True,
      )
  ```

  Note the deliberate filtering in both functions: only keys declared in `DEFAULT_SETTINGS` are ever read out or written in, so a stale document field or a crafted form post cannot inject arbitrary keys.

---

## Task 2: Expose Settings to Templates

**Files:**
- Modify: `app.py`
- Create: `templates/_macros.html`

- [ ] **Step 1: Add the context processor below the helpers**

  ```python
  @app.context_processor
  def inject_settings():
      """Make `settings` available to every template."""
      return {"settings": get_settings()}
  ```

  This costs one small indexed `find_one` per render. The app already issues several queries per page, so this is acceptable; do **not** add caching yet — a cache would need invalidation on save and there is no measured problem to solve.

- [ ] **Step 2: Create `templates/_macros.html`**

  ```jinja
  {#
    Emit attributes that opt a field out of browser and password-manager
    autofill. Renders nothing unless the setting is enabled.
    Usage: <input type="text" ... {{ autofill_guard(settings) }}>
  #}
  {% macro autofill_guard(settings) -%}
    {%- if settings.disable_password_manager_autofill -%}
      autocomplete="off" data-1p-ignore data-lpignore="true" data-bwignore="true" data-protonpass-ignore="true" data-form-type="other"
    {%- endif -%}
  {%- endmacro %}
  ```

  The `{%-`/`-%}` whitespace control matters — without it the macro injects stray newlines inside the tag. Always leave a literal space before `{{ autofill_guard(settings) }}` in the calling tag.

---

## Task 3: Settings Page + Route

**Files:**
- Modify: `app.py`
- Create: `templates/settings.html`
- Modify: `templates/base.html`

- [ ] **Step 1: Add the routes in a new section above the `__main__` block**

  ```python
  # ---------------------------------------------------------------------------
  # Settings routes
  # ---------------------------------------------------------------------------

  @app.route("/settings")
  def settings_page():
      return render_template("settings.html")


  @app.route("/settings", methods=["POST"])
  def update_settings():
      # An unchecked checkbox is absent from the form body, so absence == False.
      save_settings({
          "disable_password_manager_autofill":
              "disable_password_manager_autofill" in request.form,
      })
      flash("Settings saved.", "success")
      return redirect(url_for("settings_page"))
  ```

  The view function is `settings_page`, not `settings` — the context processor already binds the name `settings` in templates, and a same-named endpoint invites confusion in `url_for` calls.

- [ ] **Step 2: Create `templates/settings.html`**

  ```jinja
  {% extends "base.html" %}

  {% block content %}
  <h2 class="mb-3">Settings</h2>

  <form method="post" action="{{ url_for('update_settings') }}">
    <div class="card mb-4">
      <div class="card-header">Privacy &amp; Forms</div>
      <div class="card-body">
        <div class="form-check form-switch settings-row">
          <input class="form-check-input" type="checkbox" role="switch"
                 id="disable_password_manager_autofill"
                 name="disable_password_manager_autofill"
                 {% if settings.disable_password_manager_autofill %}checked{% endif %}>
          <label class="form-check-label" for="disable_password_manager_autofill">
            Disable password manager autofill
          </label>
          <div class="form-text">
            Stops browsers and password managers (1Password, LastPass, Bitwarden,
            Proton Pass, Dashlane) from offering saved logins in template,
            container, and placeholder fields. Your own category suggestions are
            unaffected.
          </div>
        </div>
      </div>
    </div>

    <button type="submit" class="btn btn-primary">Save Settings</button>
    <a href="{{ url_for('index') }}" class="btn btn-outline-secondary ms-2">Back</a>
  </form>
  {% endblock %}
  ```

  Each future setting is one more `.form-check.form-switch` block inside a `card` — group related ones under a new `card-header` section.

- [ ] **Step 3: Add the nav link in `base.html`**

  In the `navbar-nav ms-auto` div, after the New Template link:

  ```jinja
  <a class="nav-link" href="{{ url_for('settings_page') }}">Settings</a>
  ```

---

## Task 4: Apply the Guard to Every Form

Each template needs the import at the top of the file (after `{% extends %}`), then the macro call inside each tag:

```jinja
{% from "_macros.html" import autofill_guard %}
```

Put `autocomplete="off"` on the `<form>` element itself as well as the fields — some managers decide at form level. The macro handles both.

- [ ] **Step 1: `templates/generate.html`**

  Add the import. Then add ` {{ autofill_guard(settings) }}` to:
  - the `<form method="post" action="...">` tag
  - the placeholder `<input type="text" ...>` tag

  Leave the `<select>` alone — password managers do not autofill dropdowns, and the existing `required`/`disabled selected` behavior should not be disturbed.

- [ ] **Step 2: `templates/template_form.html`**

  Add the import. Apply the macro to:
  - the `<form id="templateForm">` tag
  - the `#name` input
  - the `#body` textarea

  Leave `#container_id` (a select) alone.

- [ ] **Step 3: Guard the JS-generated options textareas**

  `initPlaceholderDetection()` in `static/app.js` builds `ph_options_*` textareas as an HTML string, so the Jinja macro cannot reach them. Rather than duplicating the attribute list in JS, pass the flag in from the template's existing `{% block scripts %}`:

  ```jinja
  <script>
    const existingPlaceholders = {{ template.placeholders | tojson | safe if template else '[]' }};
    const autofillGuard = {{ settings.disable_password_manager_autofill | tojson }};
    initPlaceholderDetection(existingPlaceholders, autofillGuard);
  </script>
  ```

  In `app.js`, give `initPlaceholderDetection` a second parameter `guard` defaulting to `false`, build a module-level constant for the attribute string, and interpolate it into the `<textarea>` in the template literal. Keep the two attribute lists (macro and JS) adjacent in a comment referencing each other so they don't drift.

  Confirm `tests/templateFilter.test.js` still passes — it imports `static/app.js` and exercises `initTemplateFilter`, not this function, but the module must stay loadable.

- [ ] **Step 4: `templates/container_form.html`**

  Add the import. Apply the macro to the `<form>` tag, the `#name` input, and the `#category` input. **Verify the datalist still drops suggestions** after this change — that is the one regression this task could plausibly cause.

---

## Task 5: Dark-Theme Switch Styling

**Files:**
- Modify: `static/style.css`

- [ ] **Step 1: Check what already exists**

  `style.css` styles `.form-check-input` (line ~207) and `:checked` (~212) with the accent token, but has no `.form-switch` rules. Bootstrap's switch draws its knob with an embedded SVG `background-image` whose fill is a dark gray — on the `#44444E` surface it will be nearly invisible in the unchecked state.

- [ ] **Step 2: Add a switch block near the existing form-check rules**

  Override the unchecked knob to a muted light fill and the checked knob to white, using `--text-muted` / `--text-primary` values. Bootstrap needs a literal color inside the inline SVG data URI, so the hex cannot be a `var()` — add a comment noting the hardcoded value mirrors `--text-primary` (`#D3DAD9`) and must be updated with it.

- [ ] **Step 3: Add `.settings-row` spacing**

  Give the row comfortable vertical padding, a `--border-color` divider between adjacent rows (`.settings-row + .settings-row`), and indent `.form-text` to align under the label rather than the switch.

---

## Task 6: Verification

There is no Python test harness in this repo (`npm test` runs `node --test` over `tests/`), so the Python side is verified manually. Adding pytest is a reasonable follow-up but is **out of scope** for this plan.

- [ ] **Step 1: Run the JS suite** — `npm test` must stay green after the `app.js` change.

- [ ] **Step 2: Start the app** — `python app.py` (note the working tree currently defaults `PORT` to **5010**, not 5000). Requires a running Mongo at `MONGO_URI`.

- [ ] **Step 3: Default state** — visit `/settings` with no settings document present. The switch renders **off**. View source on `/containers/new`: no `autocomplete` or `data-*` guard attributes. Confirm nothing about the app changed for an existing user.

- [ ] **Step 4: Toggle on** — flip the switch, Save, confirm the flash message and that the switch stays on after the redirect. Check Mongo: `db.settings.findOne({_id: "app"})` shows `true` plus `updated_at`.

- [ ] **Step 5: Verify attributes on all four surfaces** — view source on `/containers/new`, `/templates/new`, a template edit page, and a `/generate` page. Every text input, every textarea (including a JS-generated `ph_options_*` one), and every `<form>` tag carries the full attribute set. Nothing is malformed — no attributes fused to a neighbor, which is the symptom of missing whitespace control.

- [ ] **Step 6: Real-browser check** — with an actual password manager extension installed, click into the container Name field and the generate placeholder fields. No saved-login dropdown should appear. Test at least one placeholder deliberately named `email` or `username`, since that is the case browser heuristics fight hardest; if Chrome still offers a suggestion there, report it rather than piling on hacks like the `readonly`-until-focus trick, which breaks keyboard and screen-reader use.

- [ ] **Step 7: Datalist regression** — with the setting **on**, the category field in `/containers/new` must still show existing categories.

- [ ] **Step 8: Toggle back off** — attributes disappear from the rendered HTML.

---

## Risks

| Risk | Mitigation |
|---|---|
| Chrome ignores `autocomplete="off"` on heuristically-detected fields | Vendor `data-*` attributes cover the major managers; Step 6 measures what's left instead of guessing |
| Vendor opt-out attribute names change between extension versions | They are additive and inert when unrecognized; Step 6 is the real check |
| Attribute list drifts between the Jinja macro and `app.js` | Cross-referencing comments in both places (Task 4 Step 3) |
| Context processor adds a DB read to every render, including error pages | One small `find_one` on a single-document collection; revisit only with a measured problem |
| Mongo unavailable makes every page fail, not just `/settings` | Pre-existing condition — `index()` already queries Mongo unconditionally. Not addressed here |

---

## Rollback

Revert the commit. The `settings` collection can be left in place — nothing else reads it, and `get_settings()` no longer exists to interpret it.
