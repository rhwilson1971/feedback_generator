# "Paste Feedback" Browser Extension Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A personal Chrome extension with a toolbar button that becomes **enabled** once feedback has been generated in the Feedback Generator, and that **pastes** that feedback into the text box you are working in on any other site (e.g. an LMS grading comment box).

**Architecture:** A Manifest V3 extension in `extension/`, loaded unpacked, never published.

1. **Capture:** a content script that runs only on the app's origin (`http://localhost:5010/*`) watches for the generated-feedback textarea (`#resultText`). When it appears, the script sends the text to the service worker. The app also stamps `data-feedback-generated` on that textarea so the script has a stable hook.
2. **State:** the service worker stores the latest feedback in `chrome.storage.session`, which is cleared when the browser closes. It then enables the action: a green badge dot and a "Paste feedback" tooltip. With no feedback stored, the action is disabled (`chrome.action.disable()`) and greyed out.
3. **Remember the target:** a tiny content script on all sites records the last text box you focused in each frame: `<input type=text>`, `<textarea>`, or a `contenteditable` rich-text editor (TinyMCE/CKEditor iframes in Canvas, Blackboard and Moodle).
4. **Paste:** clicking the toolbar button, pressing the keyboard shortcut (`Alt+Shift+F`) or using the right-click "Paste feedback" item on an editable field sends the text to the active tab. The frame holding the remembered field inserts it at the cursor, using `document.execCommand("insertText")` so the page's own editor and undo history see a real edit. For plain inputs it falls back to `setRangeText` plus `input`/`change` events, so frameworks such as React notice the change.

The extension never talks to the Flask server over HTTP; it only reads the rendered page. So the app needs no API, no CORS setup and no authentication.

**Tech Stack:** Chrome Manifest V3 (`action`, `storage`, `contextMenus`, `commands`, `scripting`), vanilla JS, `node --test` + jsdom for the insertion logic. No build step, no new npm dependencies.

**Decisions already made (do not re-litigate):**
- **Local only:** loaded via `chrome://extensions` → Developer mode → *Load unpacked*. No Web Store listing, no packing or signing, no update URL. It works in any Chromium browser (Chrome, Edge, Brave). Firefox is out of scope; it would need `browser_specific_settings` and a temporary add-on load.
- **App origin:** hard-coded as `http://localhost:5010/*` in `manifest.json`, `host_permissions` and `content_scripts.matches`. If you run the app elsewhere (Docker on another port, for example), edit that one line and reload the extension.
- **Scope:** only the **most recent** generated feedback is kept. There's no history, and it's cleared when the browser closes (`storage.session`).
- **Paste target:** the last text box you focused on the page. If there isn't one, the button shows a "Click into a text box first" badge and does nothing. It never guesses a field.
- **After pasting:** the feedback stays available, so you can paste it again. Generating new feedback replaces it.
- **Permissions:** the "remember focus" content script must run on all sites (`<all_urls>`, `all_frames: true`), because LMS editors live in iframes. That is acceptable for a personal extension. It only listens for `focusin` and reads nothing else.

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `extension/manifest.json` | **New** | MV3 manifest: permissions, content scripts, command, icons |
| `extension/background.js` | **New** | Service worker: store feedback, enable/disable action, context menu, route paste to tab |
| `extension/capture.js` | **New** | Content script on the app origin: detect `#resultText[data-feedback-generated]` → send text |
| `extension/paste.js` | **New** | Content script on all sites/frames: track last focused editable; `insertFeedback(el, text)` |
| `extension/icons/` | **New** | 16/32/48/128 px icons (reuse `static/feedback-brand/feedback-icon.png`, resized) |
| `extension/README.md` | **New** | How to load/reload it and change the app origin |
| `templates/generate.html` | Modify | Add `data-feedback-generated` to `#resultText` |
| `tests/extensionPaste.test.js` | **New** | jsdom tests for editable detection and insertion |
| `tests/extensionCapture.test.js` | **New** | jsdom tests for capture (message sent only when result exists) |
| `README.md` | Modify | Short "Browser extension (personal use)" section linking to `extension/README.md` |

Content scripts use the same `if (typeof module !== "undefined") module.exports = …` export pattern as `static/app.js`, so `node --test` can require them.

---

## Task 1: Mark generated feedback in the app

- [ ] In `templates/generate.html`, add `data-feedback-generated` to `<textarea id="resultText">`.
- [ ] Add a Flask test (extend `tests/test_placeholder_mru.py` or a new file): POST generate → response contains `data-feedback-generated`; GET form → it doesn't.
- [ ] Run `.venv/bin/python -m unittest discover tests`.

## Task 2: Paste logic (TDD)

- [ ] Write `tests/extensionPaste.test.js` first, covering:
  - `isEditable(el)` is true for textarea, text-like inputs (`text`, `search`, `email`, `url`, none) and `contenteditable`, and false for `password`, `checkbox`, `disabled` and `readonly`.
  - `insertFeedback(textarea, text)` inserts at the cursor, replaces the selection and fires `input`.
  - `insertFeedback(contentEditableDiv, text)` inserts text, keeping line breaks as `<br>`/paragraphs.
  - The focus tracker records the last editable on `focusin` and ignores non-editables.
- [ ] Implement `extension/paste.js`: `isEditable`, `insertFeedback`, a `focusin` listener storing `lastEditable`, and a `chrome.runtime.onMessage` handler for `{type: "paste", text}`. The handler focuses `lastEditable`, inserts, and replies `{ok: true}`, or `{ok: false, reason: "no-target"}` if there's no field.
- [ ] `npm test`.

## Task 3: Capture logic (TDD)

- [ ] Write `tests/extensionCapture.test.js`: with `#resultText[data-feedback-generated]` present → it calls `chrome.runtime.sendMessage({type: "feedback", text})` (with `chrome` stubbed). With the element absent → no message.
- [ ] Implement `extension/capture.js`: run at `document_idle`, find the element and send its `value`.
- [ ] `npm test`.

## Task 4: Service worker + manifest

- [ ] `manifest.json`: `manifest_version: 3`. Permissions: `storage`, `contextMenus`, `activeTab`, `scripting`. `host_permissions`: `["http://localhost:5010/*"]`. Content scripts: `capture.js` on the app origin; `paste.js` on `<all_urls>` with `all_frames: true` and `match_about_blank: true`. `commands._execute_action` → `Alt+Shift+F`. Plus `action.default_title` and icons.
- [ ] `background.js`:
  - On install/startup: `chrome.action.disable()` unless `storage.session` already holds feedback. Create the context menu item "Paste feedback" (`contexts: ["editable"]`).
  - On a `feedback` message: save the text, `chrome.action.enable()`, set a badge dot and the title "Paste feedback (N chars)".
  - On `action.onClicked` or the context menu: send `{type: "paste", text}` to the active tab in **all frames**. If every frame replies `no-target`, show a "!" badge for 2 seconds with the title "Click into a text box first".
  - The context menu passes `info.frameId`, so it targets that frame directly.

## Task 5: Load and test by hand

- [ ] Resize the brand icon into `extension/icons/`.
- [ ] Write `extension/README.md`: load unpacked, reload after edits, change the origin line, and note that the keyboard shortcut can be changed at `chrome://extensions/shortcuts`.
- [ ] Test by hand:
  1. The button is greyed out before generating.
  2. Generate feedback → the button is enabled with a badge.
  3. On another tab, click into a plain `<textarea>` (any site) → click the button → the text appears at the cursor.
  4. Repeat in an LMS rich-text comment box inside an iframe.
  5. Right-click an editable → "Paste feedback" works.
  6. No field focused → "!" badge and nothing changes on the page.
  7. Restart the browser → the button is disabled again.
- [ ] Update `README.md`.

---

## Risks / notes
- **Stricter editors** (Google Docs, some Canvas/React editors) may ignore `execCommand`. The fallback is to put the text on the clipboard and tell you to press Cmd+V. Add that fallback only if step 4 of the manual test fails.
- **Pages the extension can't reach:** Chrome blocks extensions on `chrome://` pages and the Chrome Web Store, so the button can't paste there.
- **Different app URL:** if you use `127.0.0.1` instead of `localhost`, add it to the `matches` list as well.
