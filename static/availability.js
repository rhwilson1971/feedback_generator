/**
 * Send marked database failures from background requests to the outage page.
 * @param {Window} win Browser window whose fetch implementation is wrapped.
 */
function initAvailability(win) {
  const originalFetch = win.fetch.bind(win);
  win.fetch = async function (...args) {
    const response = await originalFetch(...args);
    if (response.status === 503 && response.headers.get('X-Database-Unavailable') === '1') {
      win.location.assign('/unavailable');
    }
    return response;
  };
}

if (typeof window !== 'undefined' && typeof window.fetch === 'function') {
  initAvailability(window);
}
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { initAvailability };
}
