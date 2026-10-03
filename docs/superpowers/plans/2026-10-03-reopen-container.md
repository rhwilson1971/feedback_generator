# Reopen Container Implementation Plan

**Goal:** Implement approved FG-31 inline in this session.

**Architecture:** The generation link carries a template ID; a focused index initializer resolves the rendered row's containing accordion item. Existing settings controls gate both the link and initializer.

**Tech Stack:** Flask, Jinja, JavaScript, unittest, node:test/jsdom.

1. Add failing route tests in tests/test_return_container.py for return links, default preference, disabling, and checkbox persistence. Add DOM tests in tests/returnContainer.test.js for expansion/scroll, Uncategorized, absent targets, and Clear.
2. Run `.venv/bin/python -m unittest discover -s tests -p 'test_return_container.py'` and `node --test tests/returnContainer.test.js`; verify missing-feature failures.
3. Add reopen_container_after_feedback to app.py defaults and update_settings checkbox handling. Add the checkbox to templates/settings.html and conditional return_template link to templates/generate.html.
4. Add initReturnContainer in static/app.js, exported for DOM tests. Locate the row by comparing data-id strings, find its closest accordion item, expand/update aria state, and scrollIntoView. Call after filter setup in templates/index.html, gated by settings.
5. Run targeted tests followed by full Python/JavaScript suites and git diff --check. Review the patch and document the setting in README.

## Completion evidence

All five steps completed. New tests first failed for the absent feature, then passed after implementation. Full suites: 72 Python tests and 65 JavaScript tests pass; git diff --check passes.

Independent review found that a fixed scroll offset could hide the heading beneath stacked mobile navigation. Reproduced at 375px, added a failing regression, and replaced the offset with measured sticky-navigation height plus 16px. Browser recheck confirmed the heading sits below navigation. Desktop browser checks covered generation/return, subsequent Bootstrap collapse, Uncategorized, and disabling restoration from an existing return URL. Browser data was isolated in memory; no live MongoDB verification performed.
