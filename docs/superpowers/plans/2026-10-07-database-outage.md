# Database Outage Implementation Plan

**Goal:** Display a friendly page during database connection failures.

**Architecture:** Register a shared ConnectionFailure handler in availability.py. Render templates/unavailable.html without database-dependent context processors. Wrap browser fetch in static/availability.js and load it before app.js.

**Tech Stack:** Flask, PyMongo, Jinja, JavaScript, unittest, node:test.

- [x] Add tests/test_database_outage.py for settings failures, writes, independent outage rendering, recovery, and unrelated exceptions. Run `.venv/bin/python -m unittest discover -s tests -p test_database_outage.py`; confirm outage assertions fail with 500 before implementation.
- [x] Add availability.py with register_availability(app), /unavailable, and ConnectionFailure handler; render directly through app.jinja_env and return marked, non-cacheable 503 responses.
- [x] Register the handler in app.py; document existing undocumented functions in that touched file.
- [x] Add a self-contained accessible outage page with responsive styling and a home-page retry link.
- [x] Add static/availability.js and load it in templates/base.html before app.js. Preserve fetch responses and navigate only on marked 503 responses.
- [x] Add tests/availability.test.js verifying marked outages navigate and ordinary responses do not.
- [x] Run `.venv/bin/python -m unittest discover -s tests -p 'test_*.py'` and `npm test`: 88 Python and 82 JavaScript tests pass. Run `git diff --check`.
