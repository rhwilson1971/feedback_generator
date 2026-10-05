# FG-35 Custom Feedback Implementation Plan

**Goal:** Edit feedback text during generation and optionally save a new template.
**Architecture:** Extend Flask generation routes, using server-derived placeholder configurations and a dedicated browser helper. Render draft state through Jinja, keeping saved template identity separate from edited text.
**Tech Stack:** Flask, pymongo, Jinja, JavaScript, unittest, node:test, jsdom.

Execute inline in the authorized session on feature/fg-35-custom-feedback.

### Task 1: Generation and persistence
- [x] Add tests/test_custom_feedback.py using ranking_support.Collection. Verify edited-body generation, tokenized saving with inherited metadata, missing-field rejection, literal substitution, retained state, and legacy submissions.
- [x] Run `.venv/bin/python -m unittest discover -s tests -p 'test_custom_feedback.py'`; confirm feature assertions fail.
- [x] Extend app.py with a generation render helper that derives current placeholders from the edited body, uses source configurations, and preserves submitted values. Validate body, save mode, name, and current values before insertion. Substitute with PLACEHOLDER_RE.sub and insert only for save mode.
- [x] Render editor, current placeholder inputs, use-once/save choice, conditional name, validation error, and draft values in templates/generate.html.
- [x] Repeat focused tests; expect all passing.

### Task 2: Browser controls
- [x] Add tests/customFeedback.test.js with jsdom. Exercise dynamic field addition/removal, value restoration, dropdown preservation, repeated names, Unicode names, and conditional name validation.
- [x] Run `node --test tests/customFeedback.test.js`; confirm helper is missing.
- [x] Create static/generate.js exposing initCustomFeedback for browser and CommonJS. Cache controls by placeholder name, rebuild only field order on editor changes, create new freeform controls using DOM text APIs, and toggle save-name visibility/required state. Bind via generate.html scripts block.
- [x] Repeat focused tests; expect all passing.

### Task 3: Verification and documentation
- [x] Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` and `npm test`.
- [x] Use isolated browser fixture to edit text, change placeholders, save, copy, and navigate back. Check browser errors and screenshot.
- [x] Add README usage instructions, review diff against approved spec, request code review, fix material findings, and run `git diff --check`.

## Validation results

- 81 Python tests and 70 JavaScript tests pass.
- Independent reviewer found no material correctness or spec compliance issues.
- Browser fixture used isolated in-memory data on port 5035. Verified one-off generation, dynamic fields, saving a new template, retained draft values, new-template navigation, and container reopening. Screenshot inspected; no browser console errors.
- Copy button passed the exact result to an instrumented clipboard write API. Actual OS clipboard read did not confirm a write in the automated browser, so OS clipboard behavior remains unverified.
- Production MongoDB persistence was not exercised.
