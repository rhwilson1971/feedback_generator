// Theme resolution. Loaded as a blocking <script> in <head> so the theme is
// set before first paint. Exports mirror the pattern used in app.js.

const THEME_QUERY = "(prefers-color-scheme: dark)";

/**
 * Resolve a stored preference to a concrete theme.
 *
 * @param {string} pref - "light", "dark", or "system" (anything else = system).
 * @param {boolean} prefersDark - Whether the OS currently prefers dark.
 * @returns {"light"|"dark"} The theme to render.
 */
function resolveTheme(pref, prefersDark) {
  if (pref === "light" || pref === "dark") return pref;
  return prefersDark ? "dark" : "light";
}

/**
 * Stamp the resolved theme on the root element for our CSS and Bootstrap's.
 *
 * @param {Element} root - The <html> element.
 * @param {string} pref - Stored preference.
 * @param {boolean} prefersDark - Current OS preference.
 * @returns {"light"|"dark"} The theme that was applied.
 */
function applyTheme(root, pref, prefersDark) {
  const theme = resolveTheme(pref, prefersDark);
  root.setAttribute("data-theme", theme);
  root.setAttribute("data-bs-theme", theme);
  return theme;
}

/**
 * Apply the preference found on <html data-theme-pref> and keep `system`
 * in sync with the OS.
 *
 * @param {Window} win - Window to read from (injectable for tests).
 * @returns {function(string): string} apply(pref) — re-applies a preference.
 */
function initTheme(win) {
  const root = win.document.documentElement;
  const mql = win.matchMedia(THEME_QUERY);
  const apply = (pref) => applyTheme(root, pref, mql.matches);

  apply(root.getAttribute("data-theme-pref") || "system");
  mql.addEventListener("change", () => {
    if (root.getAttribute("data-theme-pref") === "system") apply("system");
  });
  return apply;
}

/**
 * Preview a theme as soon as a settings radio is chosen (saved on submit).
 *
 * @param {Document} doc - Document containing input[name="theme"] radios.
 * @param {function(string): string} apply - Function returned by initTheme.
 */
function initThemePicker(doc, apply) {
  doc.querySelectorAll('input[name="theme"]').forEach((radio) => {
    radio.addEventListener("change", () => {
      if (!radio.checked) return;
      doc.documentElement.setAttribute("data-theme-pref", radio.value);
      apply(radio.value);
    });
  });
}

if (typeof module !== "undefined" && module.exports) {
  module.exports = { resolveTheme, applyTheme, initTheme, initThemePicker };
} else {
  const applyPref = initTheme(window);
  document.addEventListener("DOMContentLoaded", () =>
    initThemePicker(document, applyPref)
  );
}
