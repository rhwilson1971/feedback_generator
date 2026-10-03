# Template Rankings Implementation Plan

> Execute inline in this session, task by task, using test-driven development and an independent final code review.

**Goal:** Deliver FG-4 and FG-17 through FG-20: shared scales, optional template ranks, and combined filters.

**Architecture:** A rankings blueprint owns scale validation and management. Templates store shared scale IDs and numeric rank IDs; existing client-side filters gain scale/rank controls.

**Tech Stack:** Flask, PyMongo, Jinja, Bootstrap, plain JavaScript, unittest, node:test/jsdom.

## Task 1: Reliable test isolation

- [x] Reproduce the settings lookup dependency in existing rendered-page tests.
- [x] Patch settings collections in affected test fixtures; preserve settings-specific tests.
- [x] Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'`; expect 47 passing tests without MongoDB.

## Task 2: Scale management (FG-17, FG-18)

Files: `rankings.py`, `database.py`, `app.py`, `templates/rankings.html`, `templates/ranking_form.html`, `templates/base.html`, `static/rankings.js`, `tests/test_rankings.py`, `tests/rankings.test.js`.

- [x] Write tests posting a named scale with rank IDs 1 and 3, verifying sorted saved ranks and rendered management page.
- [x] Verify failure before implementation: scale routes return 404.
- [x] Implement collection helper and blueprint CRUD with unique casefolded names; reject empty/duplicate/invalid ranks, protect used scales and ranks, preserve invalid form input.
- [x] Implement row add/remove UI and theme-compatible forms. Test dynamic controls before adding their implementation.
- [x] Run targeted tests, then the existing suites.

## Task 3: Template assignments and copies (FG-19)

Files: `app.py`, `templates/template_form.html`, `templates/index.html`, `static/rankings.js`, `tests/test_template_rankings.py`.

- [x] Write tests for create/edit/unrank, invalid references, legacy templates, badges, shared label updates, and template/container copies.
- [x] Verify failure: ranking fields are absent from saved templates and rendered forms.
- [x] Add dependent scale/rank selectors, server validation, and preserved form values on errors.
- [x] Persist optional references, display badges, and preserve them in both copy paths.
- [x] Run targeted tests, then the existing suites.

## Task 4: Combined filtering (FG-20)

Files: `templates/index.html`, `static/app.js`, `static/rankings.js`, `tests/rankingFilter.test.js`.

- [x] Write DOM tests selecting a scale, a specific rank, and Unranked; combine name/container/tags and verify Clear and empty results.
- [x] Verify failure: selecting ranking controls has no filtering effect.
- [x] Extend filtering with AND semantics and dependent rank reset; preserve existing tag OR semantics and accordion behavior.
- [x] Run `npm test`; expect all old and new tests to pass.

## Task 5: Review and delivery

- [x] Document Rankings usage in README.
- [x] Run full Python and JavaScript suites, `git diff --check`, and browser checks with isolated data.
- [x] Refresh/check graph coverage for changed files, falling back to source where necessary.
- [x] Obtain independent code review; fix material findings and rerun affected checks.
- [x] Commit the feature, push the branch, and create a draft PR with ticket links and validation results. Report limitations explicitly; do not close Jira tickets before user verification.

## Validation results

67 Python tests and 60 JavaScript tests pass; `git diff --check` is clean. Browser checks covered assignments, unranking, copies, combined filters, used-rank protections, mobile layout, and light/dark themes with isolated in-memory data. Production MongoDB persistence remains to be verified. Independent review found a missing persisted-rank removal confirmation; it was fixed with a regression test.
