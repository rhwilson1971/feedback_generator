# FG-29: Warn before discarding changed forms

## Goal and scope

Warn when leaving a form whose current values differ from its initial values. The user selected warning before discarding rather than offering to save during navigation. Cover new/edit templates, new/edit containers, new/edit ranking scales, Settings, and the feedback-generation form.

## User behavior

Use the browser's native leave-page confirmation for navigation links (including Cancel and Back), browser Back, refresh, and closing the tab. Staying retains the form; leaving discards the page's draft. The browser controls dialog wording and button labels and may require prior user interaction or omit warnings in some mobile lifecycle cases.

An untouched form does not warn. Changing a value and then restoring its initial value does not warn. Successful ordinary Save/Create/Update/Generate submissions proceed without a discard warning. Invalid submissions and submissions canceled by the existing no-placeholder confirmation keep protection active. A newly rendered success/result page starts clean; further edits enable protection again.

Initial values mean the values rendered on each page after its existing JavaScript controls initialize, including forms redisplayed following server validation errors. This feature protects changes made on that page; it does not recover drafts across navigation or track whether submitted values match the database. Feedback generated using Use once starts a clean baseline on the result page even though its draft was not saved as a template.

## Implementation

Add a dedicated static/unsaved-forms.js helper and opt the covered forms in with a data attribute. Load the helper in base.html and initialize after existing page-specific control setup. Keep the guard separate from the existing app.js so it does not require unrelated changes.

Snapshot meaningful named input, select, and textarea values, checkbox/radio selections, and repeated field values in order. Include dynamic placeholder configurations and ranking rows, so adding/removing fields counts as a change. Ignore button controls and read-only generated output. Include disabled values where they represent draft state, while excluding inactive new-template-name input in Use once mode. DOM-derived comparison captures programmatic tag additions and dynamic field updates without relying on every control dispatching an input event.

Evaluate the current snapshot when leaving. Use beforeunload to request the native confirmation only for a changed opted-in form. Suppress the warning for an uncanceled form submission; retain it when a later handler prevents submission. Handle browser history restoration so a prior successful submission does not disable future warnings. No backend or database changes are needed.

Document all added functions with the project's JavaScript documentation-comment style, including nested helpers. Add missing documentation to any existing functions in files modified for implementation, as required by the user's standing preference.

## Verification

Use node:test and jsdom to verify clean/changed/reverted state, checkboxes, radios, repeated ranking fields, dynamic additions/removals, programmatic tag changes, submission cancellation, inactive save-name fields, result-page baselines, and history restoration. Verify covered form markers and script loading with rendered templates. Run existing Python and JavaScript suites.

In an isolated browser fixture, exercise leaving a changed form and choosing Stay/Leave, refresh, a successful submit without a discard prompt, and canceling the existing no-placeholder save confirmation. Inspect for console errors. Browser-native dialogs require direct browser validation in addition to simulated beforeunload events.

## Evidence

Tier 2 verification in graph project Users-drreubenwilson-dev-projects-feedback_generator identified initPlaceholderConfirm, initRankRows, initCustomFeedback, and initThemePicker. initPlaceholderConfirm prevents the submit event when the existing save confirmation is declined; the guard must respect that cancellation. Dynamic rank rows and generated placeholder inputs require comparison of current DOM state. Coverage is best effort. Partial template ranges in template_form.html (27,55,65), generate.html (49,77,83), and settings.html (16) were read directly.
