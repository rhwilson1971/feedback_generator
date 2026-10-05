/**
 * Serialize an editor's named controls in DOM order, including repeated fields.
 * Read-only output and buttons are ignored. data-unsaved-ignore-if supplies a
 * form-local selector that excludes an inactive control when it matches.
 * @param {HTMLFormElement} form - Form whose current draft should be compared.
 * @returns {string} Stable JSON representation of the editable values.
 */
function snapshotForm(form) {
  const values = [];
  for (const control of form.elements) {
    if (!control.name || control.readOnly || !control.matches('input, select, textarea')) continue;
    if (['button', 'submit', 'reset', 'image'].includes(control.type)) continue;
    const ignoreIf = control.dataset.unsavedIgnoreIf;
    if (ignoreIf && form.querySelector(ignoreIf)) continue;
    let value = control.value;
    if (['checkbox', 'radio'].includes(control.type)) value = [control.value, control.checked];
    else if (control.multiple) value = [...control.selectedOptions].map(option => option.value);
    values.push([control.name, control.type, value]);
  }
  return JSON.stringify(values);
}

/**
 * Protect opted-in forms with a native leave-page warning when drafts differ.
 * Call after page controls initialize. Canceled submissions retain protection;
 * accepted submissions bypass it only while their submitted values are intact.
 * @param {Document} doc - Document containing forms marked data-unsaved-form.
 */
function initUnsavedForms(doc) {
  const win = doc.defaultView;
  const states = [...doc.querySelectorAll('form[data-unsaved-form]')].map(form => {
    const state = {form, baseline: snapshotForm(form), submission: null};
    form.addEventListener('submit', event => {
      state.submission = {event, snapshot: snapshotForm(form)};
    });
    form.addEventListener('input', () => { state.submission = null; });
    form.addEventListener('change', () => { state.submission = null; });
    return state;
  });
  if (!states.length) return;

  /** Request the browser-controlled warning unless a current submit permits leaving. */
  function warnBeforeLeaving(event) {
    const changed = states.some(state => {
      const current = snapshotForm(state.form);
      const submission = state.submission;
      return current !== state.baseline &&
        !(submission && !submission.event.defaultPrevented && submission.snapshot === current);
    });
    if (changed) {
      event.preventDefault();
      event.returnValue = '';
    }
  }

  /** Clear stale submit bypasses when browser history restores this document. */
  function restoreProtection() {
    states.forEach(state => { state.submission = null; });
  }
  win.addEventListener('beforeunload', warnBeforeLeaving);
  win.addEventListener('pageshow', restoreProtection);
}

if (typeof module !== 'undefined' && module.exports) {
  module.exports = { snapshotForm, initUnsavedForms };
} else {
  document.addEventListener('DOMContentLoaded', () => initUnsavedForms(document));
}
