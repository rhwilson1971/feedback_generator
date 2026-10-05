# FG-29 Unsaved Form Warning Implementation Plan

**Goal:** Warn before leaving changed editor forms while allowing ordinary submissions.
**Architecture:** A standalone JavaScript helper snapshots opted-in forms after page setup and checks beforeunload. Templates opt in explicitly; server behavior is unchanged.
**Tech Stack:** JavaScript, Jinja, jsdom/node:test, Flask/unittest.

Execute inline on feature/fg-29-unsaved-form-warning.

### Task 1: Guard behavior
- [x] Write tests/unsavedForms.test.js covering initial/change/revert snapshots; dynamic and repeated fields; check/radio state; disabled inputs; ignored buttons/output/inactive save-name; canceled and accepted submits; pageshow restoration; and pages without opted-in forms.
- [x] Run `node --test tests/unsavedForms.test.js` and verify failure because helper is missing.
- [x] Create static/unsaved-forms.js exporting snapshotForm(form) and initUnsavedForms(doc). Snapshot named editable controls in DOM order as JSON tuples of type/name/value or checked state. Honor data-unsaved-ignore-if selectors. Cache initial snapshots; request native beforeunload warning only when changed and not leaving through an uncanceled matching submit. Reset submit state on pageshow and subsequent input/change.
- [x] Add documentation comments to every named function, including nested helpers. Run focused tests until passing.

### Task 2: Template integration
- [x] Create tests/test_unsaved_forms.py with isolated collections and rendered-route checks for all covered forms, success/error baselines, and initialization after page scripts.
- [x] Run `.venv/bin/python -m unittest discover -s tests -p 'test_unsaved_forms.py'`; confirm missing markers fail.
- [x] Add data-unsaved-form to template_form.html, container_form.html, ranking_form.html, settings.html, and generate.html. Mark new_template_name with data-unsaved-ignore-if="#useOnce:checked". Load the helper at the end of base.html after the scripts block; initialize at DOMContentLoaded so existing theme and page controls complete first.
- [x] Repeat focused tests until passing.

### Task 3: Verify and document
- [x] Run full Python and JavaScript suites and `git diff --check`.
- [x] Use isolated browser fixture to test native Stay/Leave, refresh, normal submit, and declined existing save confirmation. Check console errors.
- [x] Add README behavior description, obtain independent code review, resolve material findings, and commit changes.

## Validation results

- All 85 Python and 81 JavaScript tests pass.
- Isolated browser fixture verified native beforeunload Stay/Leave behavior, retained draft values, refresh warnings, dynamic ranking-row protection, and normal template creation and feedback generation without discard prompts. Declining the existing no-placeholder confirmation retained protection.
- No browser console errors. Independent reviewer found no material issues.
- Browser lifecycle limitations remain as documented: native wording is controlled by the browser, prior interaction may be required, and mobile tab termination can omit beforeunload.
- No backend or database schema changes.
