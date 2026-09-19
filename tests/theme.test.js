const test = require("node:test");
const assert = require("node:assert/strict");
const { JSDOM } = require("jsdom");

const {
  resolveTheme,
  applyTheme,
  initTheme,
  initThemePicker,
} = require("../static/theme.js");

/**
 * Build a jsdom window with a controllable prefers-color-scheme media query.
 *
 * @param {string} pref - Value for data-theme-pref on <html>.
 * @param {boolean} prefersDark - Initial OS dark-mode state.
 * @returns {{window: object, setOsDark: function(boolean): void}}
 */
function buildWindow(pref, prefersDark) {
  const dom = new JSDOM(`<!DOCTYPE html>
    <html data-theme-pref="${pref}"><body>
      <input type="radio" name="theme" value="light">
      <input type="radio" name="theme" value="dark">
      <input type="radio" name="theme" value="system">
    </body></html>`);
  const { window } = dom;
  const listeners = [];
  const mql = {
    matches: prefersDark,
    addEventListener: (_type, fn) => listeners.push(fn),
  };
  window.matchMedia = () => mql;
  return {
    window,
    setOsDark(value) {
      mql.matches = value;
      listeners.forEach((fn) => fn({ matches: value }));
    },
  };
}

test("resolveTheme returns explicit choices unchanged", () => {
  assert.equal(resolveTheme("light", true), "light");
  assert.equal(resolveTheme("dark", false), "dark");
});

test("resolveTheme follows the OS for system", () => {
  assert.equal(resolveTheme("system", true), "dark");
  assert.equal(resolveTheme("system", false), "light");
});

test("resolveTheme treats unknown values as system", () => {
  assert.equal(resolveTheme("purple", true), "dark");
  assert.equal(resolveTheme(undefined, false), "light");
});

test("applyTheme sets data-theme and data-bs-theme", () => {
  const { window } = buildWindow("light", false);
  const root = window.document.documentElement;
  const theme = applyTheme(root, "dark", false);
  assert.equal(theme, "dark");
  assert.equal(root.getAttribute("data-theme"), "dark");
  assert.equal(root.getAttribute("data-bs-theme"), "dark");
});

test("initTheme applies the stored preference immediately", () => {
  const { window } = buildWindow("system", true);
  initTheme(window);
  assert.equal(window.document.documentElement.getAttribute("data-theme"), "dark");
});

test("initTheme live-updates when the OS changes and pref is system", () => {
  const { window, setOsDark } = buildWindow("system", true);
  initTheme(window);
  setOsDark(false);
  assert.equal(window.document.documentElement.getAttribute("data-theme"), "light");
});

test("initTheme ignores OS changes when pref is explicit", () => {
  const { window, setOsDark } = buildWindow("light", false);
  initTheme(window);
  setOsDark(true);
  assert.equal(window.document.documentElement.getAttribute("data-theme"), "light");
});

test("initThemePicker previews the chosen radio immediately", () => {
  const { window } = buildWindow("light", false);
  const apply = initTheme(window);
  initThemePicker(window.document, apply);

  const dark = window.document.querySelector('input[value="dark"]');
  dark.checked = true;
  dark.dispatchEvent(new window.Event("change", { bubbles: true }));

  const root = window.document.documentElement;
  assert.equal(root.getAttribute("data-theme"), "dark");
  assert.equal(root.getAttribute("data-theme-pref"), "dark");
});
