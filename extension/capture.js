// Runs on the Feedback Generator app. Sends newly generated feedback to the
// extension so its toolbar button can paste it elsewhere.

/**
 * Send the generated feedback on this page to the extension, if any.
 *
 * @param {Document} [doc] - Page to inspect.
 * @param {object} [runtime] - chrome.runtime (injectable for tests).
 * @returns {boolean} Whether feedback was found and sent.
 */
function captureFeedback(doc = document, runtime = globalThis.chrome && chrome.runtime) {
  const el = doc.querySelector("#resultText[data-feedback-generated]");
  if (!el || !el.value.trim() || !runtime) return false;
  runtime.sendMessage({ type: "feedback", text: el.value });
  return true;
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { captureFeedback };
} else {
  captureFeedback();
}
