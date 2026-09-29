// Runs in every frame. Remembers the last text box you focused and inserts
// feedback into it when the extension asks.

const TEXT_INPUT_TYPES = new Set(["", "text", "search", "email", "url", "tel"]);

/**
 * Whether an element is a text field feedback can be pasted into.
 *
 * @param {Element|null} el - Candidate element.
 * @returns {boolean} True for enabled, writable text inputs, textareas and
 *   contenteditable regions.
 */
function isEditable(el) {
  if (!el || el.nodeType !== 1) return false;
  if (el.isContentEditable || el.getAttribute("contenteditable") === "true") return true;
  if (el.disabled || el.readOnly) return false;
  if (el.tagName === "TEXTAREA") return true;
  if (el.tagName === "INPUT") {
    return TEXT_INPUT_TYPES.has((el.getAttribute("type") || "").toLowerCase());
  }
  return false;
}

/**
 * Insert text into a plain input or textarea at the cursor, replacing any
 * selection, and fire the events frameworks listen for.
 *
 * @param {HTMLInputElement|HTMLTextAreaElement} el - Target field.
 * @param {string} text - Text to insert.
 */
function insertIntoField(el, text) {
  const start = el.selectionStart ?? el.value.length;
  const end = el.selectionEnd ?? el.value.length;
  el.setRangeText(text, start, end, "end");
  el.dispatchEvent(new el.ownerDocument.defaultView.Event("input", { bubbles: true }));
  el.dispatchEvent(new el.ownerDocument.defaultView.Event("change", { bubbles: true }));
}

/**
 * Insert text into a contenteditable region at the cursor, turning line
 * breaks into <br> elements.
 *
 * @param {HTMLElement} el - Contenteditable root.
 * @param {string} text - Text to insert.
 */
function insertIntoRichText(el, text) {
  const doc = el.ownerDocument;
  const win = doc.defaultView;
  const sel = win.getSelection();
  let range;
  if (sel && sel.rangeCount && el.contains(sel.getRangeAt(0).commonAncestorContainer)) {
    range = sel.getRangeAt(0);
  } else {
    range = doc.createRange();
    range.selectNodeContents(el);
    range.collapse(false);
  }
  range.deleteContents();

  const frag = doc.createDocumentFragment();
  text.split("\n").forEach((line, i) => {
    if (i > 0) frag.appendChild(doc.createElement("br"));
    if (line) frag.appendChild(doc.createTextNode(line));
  });
  const last = frag.lastChild;
  range.insertNode(frag);
  if (last && sel) {
    range.setStartAfter(last);
    range.collapse(true);
    sel.removeAllRanges();
    sel.addRange(range);
  }
  el.dispatchEvent(new win.Event("input", { bubbles: true }));
}

/**
 * Insert feedback into a field. Prefers execCommand("insertText") so rich
 * editors and undo history see a real edit, falling back to direct DOM edits.
 *
 * @param {HTMLElement} el - Target editable element.
 * @param {string} text - Feedback text.
 */
function insertFeedback(el, text) {
  el.focus();
  const doc = el.ownerDocument;
  if (typeof doc.execCommand === "function") {
    try {
      if (doc.execCommand("insertText", false, text)) return;
    } catch (_) {
      // Fall through to the manual insert.
    }
  }
  if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
    insertIntoField(el, text);
  } else {
    insertIntoRichText(el, text);
  }
}

/**
 * Track the last focused editable in this frame and handle paste requests.
 *
 * @param {Document} [doc] - Frame document.
 * @param {object} [runtime] - chrome.runtime (injectable for tests).
 * @returns {{lastEditable: function(): (HTMLElement|null)}} Accessor for tests.
 */
function initPasteTarget(doc = document, runtime = globalThis.chrome && chrome.runtime) {
  let lastEditable = null;

  doc.addEventListener(
    "focusin",
    (event) => {
      let el = event.target;
      // Focus inside a rich editor lands on a child; use the editable root.
      while (el && el.parentElement && el.parentElement.isContentEditable) el = el.parentElement;
      if (!isEditable(el)) return;
      lastEditable = el;
      if (runtime) runtime.sendMessage({ type: "focus" }).catch?.(() => {});
    },
    true
  );

  if (runtime) {
    runtime.onMessage.addListener((msg, _sender, sendResponse) => {
      if (msg.type !== "paste") return;
      if (!lastEditable || !lastEditable.isConnected) {
        sendResponse({ ok: false, reason: "no-target" });
        return;
      }
      insertFeedback(lastEditable, msg.text);
      sendResponse({ ok: true });
    });
  }

  return { lastEditable: () => lastEditable };
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { isEditable, insertFeedback, initPasteTarget };
} else {
  initPasteTarget();
}
