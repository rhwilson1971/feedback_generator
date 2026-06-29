# UI Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the Feedback Generator UI to a dark, sleek aesthetic using the palette `#37353E / #44444E / #715A5A / #D3DAD9` while keeping Bootstrap 5.3.3 as the layout foundation.

**Architecture:** Override Bootstrap's default styles via CSS custom properties and targeted class overrides in `static/style.css`. Add the Inter typeface via Google Fonts in `base.html`. All visual changes are confined to CSS and the navbar markup in `base.html` — no Python/logic files are touched.

**Tech Stack:** Flask/Jinja2 templates, Bootstrap 5.3.3, vanilla CSS (no preprocessor), Google Fonts (Inter)

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `static/style.css` | Full rewrite | All dark-theme overrides + design tokens |
| `templates/base.html` | Modify | Add Inter font, fix navbar class (`bg-primary` → custom) |
| `templates/index.html` | No change | Bootstrap classes already semantic — CSS handles it |
| `templates/generate.html` | No change | Same |
| `templates/template_form.html` | No change | Same |
| `static/app.js` | No change | `btn-outline-primary`/`btn-success` swaps still valid |

---

## Color Tokens (reference for all tasks)

```
--bg-primary:   #37353E   ← darkest; page background
--bg-surface:   #44444E   ← cards, navbar, list items
--bg-elevated:  #4f4d59   ← hover states, secondary surfaces
--accent:       #715A5A   ← interactive elements, primary actions
--accent-hover: #8a6e6e   ← accent hover/active
--accent-muted: rgba(113,90,90,0.15)  ← ghost fills
--text-primary: #D3DAD9   ← body copy on dark
--text-muted:   rgba(211,218,217,0.55)
--border-color: rgba(211,218,217,0.10)
--border-accent:rgba(113,90,90,0.50)
--shadow-sm:    0 1px 3px rgba(0,0,0,0.30)
--shadow-md:    0 4px 12px rgba(0,0,0,0.40)
--radius:       8px
--transition:   150ms ease
```

---

## Task 1: Design Tokens + Base Reset

**Files:**
- Rewrite: `static/style.css` (starting from blank — existing file is ~30 lines)

- [ ] **Step 1: Verify the current style.css content before replacing it**

  Read `static/style.css` and confirm it only contains the ~30 lines shown in the project snapshot (body bg, template-preview, drag-handle, sortable-ghost). This is a sanity check — no hidden rules to preserve.

- [ ] **Step 2: Replace style.css with the design-token block + base reset**

  Write the following as the new `static/style.css`:

  ```css
  /* ── Design Tokens ─────────────────────────────────────── */
  :root {
    --bg-primary:    #37353E;
    --bg-surface:    #44444E;
    --bg-elevated:   #4f4d59;
    --accent:        #715A5A;
    --accent-hover:  #8a6e6e;
    --accent-muted:  rgba(113, 90, 90, 0.15);
    --text-primary:  #D3DAD9;
    --text-muted:    rgba(211, 218, 217, 0.55);
    --border-color:  rgba(211, 218, 217, 0.10);
    --shadow-sm:     0 1px 3px rgba(0, 0, 0, 0.30);
    --shadow-md:     0 4px 12px rgba(0, 0, 0, 0.40);
    --radius:        8px;
    --transition:    150ms ease;
  }

  /* ── Base ───────────────────────────────────────────────── */
  body {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    -webkit-font-smoothing: antialiased;
  }

  /* ── Custom scrollbar ───────────────────────────────────── */
  ::-webkit-scrollbar              { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track        { background: var(--bg-primary); }
  ::-webkit-scrollbar-thumb        { background: var(--bg-elevated); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover  { background: var(--accent); }
  ```

- [ ] **Step 3: Open the app in a browser and verify**

  Start the Flask dev server if not already running:
  ```bash
  python app.py
  ```
  Open `http://localhost:5000`. The page background should be dark charcoal (`#37353E`). The navbar will still be Bootstrap blue — that's expected; it's fixed in Task 2.

- [ ] **Step 4: Commit**

  ```bash
  git add static/style.css
  git commit -m "feat: add dark theme design tokens and base reset"
  ```

---

## Task 2: Navbar + Typography

**Files:**
- Modify: `templates/base.html` (add Inter font link, change navbar class)
- Append to: `static/style.css`

- [ ] **Step 1: Add Inter font and fix navbar class in base.html**

  In `templates/base.html`, inside `<head>`, add the Google Fonts link **before** the Bootstrap CSS link:

  ```html
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
  ```

  On the `<nav>` line, replace `navbar-dark bg-primary` with `navbar-dark bg-app`:

  ```html
  <nav class="navbar navbar-expand-sm navbar-dark bg-app mb-4">
  ```

  (`.bg-app` is a custom class — not Bootstrap's `.bg-primary` — so Bootstrap won't fight our override.)

- [ ] **Step 2: Append navbar + typography rules to style.css**

  Append to `static/style.css`:

  ```css
  /* ── Typography ─────────────────────────────────────────── */
  body { font-family: 'Inter', sans-serif; }

  h1, h2, h3, h4, h5, h6 { color: var(--text-primary); }

  h2.mb-3 {
    font-size: 1.35rem;
    font-weight: 600;
    letter-spacing: -0.01em;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 1.5rem !important;
  }

  .text-muted { color: var(--text-muted) !important; }

  code {
    background-color: rgba(211, 218, 217, 0.08);
    color: #a8c0be;
    padding: 0.15em 0.45em;
    border-radius: 4px;
    font-size: 0.85em;
  }

  hr { border-color: var(--border-color); opacity: 1; }

  /* ── Navbar ─────────────────────────────────────────────── */
  .bg-app {
    background-color: var(--bg-surface) !important;
    border-bottom: 1px solid var(--border-color);
    box-shadow: var(--shadow-sm);
  }

  .navbar-brand {
    font-weight: 600;
    font-size: 1.05rem;
    letter-spacing: 0.02em;
    color: var(--text-primary) !important;
  }

  .nav-link {
    color: var(--text-muted) !important;
    font-size: 0.9rem;
    transition: color var(--transition);
  }

  .nav-link:hover { color: var(--text-primary) !important; }
  ```

- [ ] **Step 3: Visually verify navbar**

  Reload `http://localhost:5000`. The navbar should be dark slate (`#44444E`) with the brand text in `#D3DAD9` and the "+ New Template" link in a muted tone. No Bootstrap blue visible in the navbar.

- [ ] **Step 4: Commit**

  ```bash
  git add templates/base.html static/style.css
  git commit -m "feat: dark navbar, Inter font, and typography scale"
  ```

---

## Task 3: Cards + List Group (Index Page)

**Files:**
- Append to: `static/style.css`

- [ ] **Step 1: Append card and list-group rules to style.css**

  ```css
  /* ── Cards ──────────────────────────────────────────────── */
  .card {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-color);
    border-radius: var(--radius);
    box-shadow: var(--shadow-sm);
  }

  .card-header {
    background-color: rgba(0, 0, 0, 0.15);
    border-bottom: 1px solid var(--border-color);
    color: var(--text-primary);
    font-weight: 500;
    padding: 0.85rem 1.25rem;
    border-radius: var(--radius) var(--radius) 0 0 !important;
  }

  .card-body { padding: 1.25rem; }

  .card-title { color: var(--text-primary); }

  /* ── List Group ─────────────────────────────────────────── */
  .list-group-item {
    background-color: var(--bg-surface);
    border-color: var(--border-color);
    color: var(--text-primary);
    transition: background-color var(--transition);
    padding: 1rem 1.25rem;
  }

  .list-group-item:first-child {
    border-radius: var(--radius) var(--radius) 0 0;
  }

  .list-group-item:last-child {
    border-radius: 0 0 var(--radius) var(--radius);
  }

  .list-group-item:hover {
    background-color: var(--bg-elevated);
  }

  /* ── Template preview text ───────────────────────────────── */
  .template-preview {
    font-family: 'Courier New', monospace;
    font-size: 0.82rem;
    color: var(--text-muted);
  }

  /* ── Drag handle ─────────────────────────────────────────── */
  .drag-handle {
    cursor: grab;
    font-size: 1.1rem;
    color: var(--text-muted);
    user-select: none;
    transition: color var(--transition);
  }

  .drag-handle:hover  { color: var(--accent); }
  .drag-handle:active { cursor: grabbing; }

  .sortable-ghost {
    opacity: 0.3;
    background-color: var(--accent-muted);
  }

  /* ── Empty state ─────────────────────────────────────────── */
  .text-center.py-5 p { color: var(--text-muted); }
  ```

- [ ] **Step 2: Visually verify the index/template list page**

  Navigate to `http://localhost:5000`. Each template card in the list should show a dark surface (`#44444E`) background, a barely-visible border, and smooth hover to `#4f4d59`. The drag handle should be muted and glow to the accent mauve on hover.

- [ ] **Step 3: Commit**

  ```bash
  git add static/style.css
  git commit -m "feat: dark card, list-group, and drag-handle styles"
  ```

---

## Task 4: Forms + Inputs

**Files:**
- Append to: `static/style.css`

- [ ] **Step 1: Append form rules to style.css**

  ```css
  /* ── Form labels ─────────────────────────────────────────── */
  .form-label {
    color: var(--text-primary);
    font-weight: 500;
    font-size: 0.9rem;
    margin-bottom: 0.4rem;
  }

  .form-text { color: var(--text-muted); font-size: 0.82rem; }

  /* ── Text inputs + textareas ─────────────────────────────── */
  .form-control {
    background-color: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: calc(var(--radius) - 2px);
    transition: border-color var(--transition), box-shadow var(--transition);
  }

  .form-control:focus {
    background-color: var(--bg-primary);
    border-color: var(--accent);
    color: var(--text-primary);
    box-shadow: 0 0 0 3px rgba(113, 90, 90, 0.20);
    outline: none;
  }

  .form-control::placeholder { color: var(--text-muted); }

  .form-control[readonly] {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    cursor: default;
  }

  /* ── Select ──────────────────────────────────────────────── */
  .form-select {
    background-color: var(--bg-primary);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: calc(var(--radius) - 2px);
    background-image: url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 16 16'%3e%3cpath fill='none' stroke='%23D3DAD9' stroke-linecap='round' stroke-linejoin='round' stroke-width='2' d='m2 5 6 6 6-6'/%3e%3c/svg%3e");
    transition: border-color var(--transition), box-shadow var(--transition);
  }

  .form-select:focus {
    background-color: var(--bg-primary);
    border-color: var(--accent);
    color: var(--text-primary);
    box-shadow: 0 0 0 3px rgba(113, 90, 90, 0.20);
    outline: none;
  }

  .form-select option {
    background-color: var(--bg-surface);
    color: var(--text-primary);
  }

  /* ── Radio / Checkbox ────────────────────────────────────── */
  .form-check-input {
    background-color: var(--bg-primary);
    border-color: rgba(211, 218, 217, 0.30);
  }

  .form-check-input:checked {
    background-color: var(--accent);
    border-color: var(--accent);
  }

  .form-check-input:focus {
    box-shadow: 0 0 0 3px rgba(113, 90, 90, 0.20);
    border-color: var(--accent);
  }

  .form-check-label { color: var(--text-primary); font-size: 0.9rem; }

  /* ── Result textarea ─────────────────────────────────────── */
  #resultText {
    background-color: var(--bg-primary);
    color: var(--text-primary);
    font-size: 1rem;
    border-color: var(--border-color);
    resize: vertical;
    line-height: 1.6;
  }
  ```

- [ ] **Step 2: Visually verify forms**

  Navigate to a template's Generate page (`/templates/<id>/generate`) and the New Template page (`/templates/new`). Check:
  - Inputs have dark backgrounds (`#37353E`) with barely-visible borders
  - Focus on any input shows the mauve (`#715A5A`) glow ring
  - Select dropdown chevron is light-colored
  - Placeholder text is muted but readable

- [ ] **Step 3: Commit**

  ```bash
  git add static/style.css
  git commit -m "feat: dark form inputs, selects, and focus ring styles"
  ```

---

## Task 5: Button System

**Files:**
- Append to: `static/style.css`

- [ ] **Step 1: Append button rules to style.css**

  ```css
  /* ── Button base ─────────────────────────────────────────── */
  .btn {
    font-weight: 500;
    font-size: 0.875rem;
    border-radius: calc(var(--radius) - 2px);
    transition: background-color var(--transition), border-color var(--transition),
                color var(--transition), box-shadow var(--transition);
  }

  /* Primary (accent mauve) */
  .btn-primary {
    background-color: var(--accent);
    border-color: var(--accent);
    color: var(--text-primary);
  }
  .btn-primary:hover,
  .btn-primary:focus {
    background-color: var(--accent-hover);
    border-color: var(--accent-hover);
    color: var(--text-primary);
    box-shadow: 0 0 0 3px rgba(113, 90, 90, 0.25);
  }

  /* Success (muted teal-green, readable on dark) */
  .btn-success {
    background-color: #4e7268;
    border-color: #4e7268;
    color: var(--text-primary);
  }
  .btn-success:hover,
  .btn-success:focus {
    background-color: #5d877c;
    border-color: #5d877c;
    color: var(--text-primary);
    box-shadow: 0 0 0 3px rgba(78, 114, 104, 0.25);
  }

  /* Secondary */
  .btn-secondary {
    background-color: var(--bg-elevated);
    border-color: var(--border-color);
    color: var(--text-primary);
  }
  .btn-secondary:hover,
  .btn-secondary:focus {
    background-color: #5a586a;
    border-color: var(--border-color);
    color: var(--text-primary);
  }

  /* Outline secondary */
  .btn-outline-secondary {
    border-color: rgba(211, 218, 217, 0.25);
    color: var(--text-muted);
    background-color: transparent;
  }
  .btn-outline-secondary:hover {
    background-color: var(--bg-elevated);
    border-color: rgba(211, 218, 217, 0.35);
    color: var(--text-primary);
  }

  /* Outline primary */
  .btn-outline-primary {
    border-color: var(--accent);
    color: #c49e9e;
    background-color: transparent;
  }
  .btn-outline-primary:hover,
  .btn-outline-primary:focus {
    background-color: var(--accent);
    border-color: var(--accent);
    color: var(--text-primary);
  }

  /* Outline danger */
  .btn-outline-danger {
    border-color: rgba(180, 80, 80, 0.40);
    color: rgba(210, 110, 110, 0.80);
    background-color: transparent;
  }
  .btn-outline-danger:hover {
    background-color: rgba(180, 80, 80, 0.15);
    border-color: rgba(180, 80, 80, 0.60);
    color: rgba(230, 130, 130, 0.95);
  }

  /* Vertical button group (template list actions) */
  .btn-group-vertical .btn { border-radius: 0; }
  .btn-group-vertical .btn:first-child { border-radius: calc(var(--radius) - 2px) calc(var(--radius) - 2px) 0 0; }
  .btn-group-vertical .btn:last-child  { border-radius: 0 0 calc(var(--radius) - 2px) calc(var(--radius) - 2px); }
  ```

- [ ] **Step 2: Visually verify buttons**

  - On the index page: the "Generate" button should be dark teal-green, "Edit" a dim outline, "Delete" a barely-there red outline that brightens on hover
  - On the Generate page: "Generate Feedback" is teal-green, "Back" is outline secondary
  - On the New Template page: "Create Template" is mauve (`#715A5A`), "Cancel" is outline secondary
  - The "Copy to Clipboard" button should be a muted mauve outline that fills on hover

- [ ] **Step 3: Commit**

  ```bash
  git add static/style.css
  git commit -m "feat: dark button system matching accent palette"
  ```

---

## Task 6: Alerts + Flash Messages + Final Polish

**Files:**
- Append to: `static/style.css`

- [ ] **Step 1: Append alert and polish rules to style.css**

  ```css
  /* ── Alerts / Flash messages ─────────────────────────────── */
  .alert {
    background-color: var(--bg-surface);
    border: 1px solid var(--border-color);
    color: var(--text-primary);
    border-radius: var(--radius);
  }

  .alert-success { border-left: 3px solid #4e7268; }
  .alert-danger  { border-left: 3px solid rgba(180, 80, 80, 0.70); }
  .alert-warning { border-left: 3px solid #9e8a4a; }
  .alert-info    { border-left: 3px solid var(--accent); }

  .btn-close { filter: invert(1) opacity(0.55); }
  .btn-close:hover { filter: invert(1) opacity(0.90); }

  /* ── Placeholder config cards (template form JS) ─────────── */
  #placeholderConfig .card {
    border-color: rgba(211, 218, 217, 0.08);
  }

  #placeholderConfig .card-body { padding: 1rem 1.25rem; }

  .card-title code { font-size: 0.88rem; }

  /* ── "No placeholders" italic message ───────────────────── */
  #placeholderConfig .fst-italic { color: var(--text-muted); }

  /* ── Section divider (Placeholder Configuration heading) ─── */
  h5 { font-size: 1rem; font-weight: 600; color: var(--text-primary); }

  /* ── Small helper text in template form ─────────────────── */
  .form-text code {
    background-color: rgba(211, 218, 217, 0.08);
    color: #a8c0be;
  }

  /* ── Generate page: template body preview ────────────────── */
  .text-muted.small em { color: var(--text-muted); font-style: italic; }

  /* ── "Generate Another" spacing ─────────────────────────── */
  a.btn.btn-secondary.mb-4 { margin-bottom: 1.5rem !important; }

  /* ── Smooth page-level padding ───────────────────────────── */
  main.container { padding-top: 0.5rem; padding-bottom: 3rem; }
  ```

- [ ] **Step 2: Full walkthrough — test every page**

  Verify each route:

  | Route | What to check |
  |---|---|
  | `/` (index) | Template list dark, buttons styled, drag handle muted, hover works |
  | `/templates/new` | Form dark, placeholder cards render styled, submit button mauve |
  | `/templates/<id>/edit` | Same as new + existing placeholders pre-filled, dropdown options dark |
  | `/templates/<id>/generate` | Placeholder inputs dark, Generated Feedback card dark, result textarea dark, Copy button outline-mauve → fills on click |
  | Flash messages | Trigger a delete or create to see the alert — should be dark surface with colored left border |

- [ ] **Step 3: Check browser console for errors**

  Open DevTools → Console. There should be no JavaScript errors. The `copyToClipboard()` class swap (`btn-outline-primary` ↔ `btn-success`) still works because both classes are now overridden in style.css.

- [ ] **Step 4: Commit**

  ```bash
  git add static/style.css
  git commit -m "feat: dark alerts, placeholder config cards, and final polish"
  ```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Dark tones with palette `#37353E / #44444E / #715A5A / #D3DAD9` — covered via CSS variables in Task 1
- [x] Modern, sleek navbar — Task 2
- [x] Cards and list items — Task 3
- [x] Forms — Task 4
- [x] Buttons — Task 5
- [x] Flash messages / alerts — Task 6
- [x] Placeholder config cards (JS-rendered) — Task 6
- [x] Inter font for modern typography — Task 2
- [x] Custom scrollbar — Task 1
- [x] Drag-and-drop handle — Task 3
- [x] `app.js` copy button class swap — verified still works in Task 6

**Placeholder scan:** No "TBD", "TODO", or "similar to Task N" patterns. All code blocks are complete.

**Type consistency:** Only CSS class names and CSS custom property names — no type mismatches possible. CSS variable names are defined in Task 1 and referenced identically in Tasks 2–6.
