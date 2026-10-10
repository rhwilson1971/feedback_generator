const { test } = require('node:test');
const assert = require('node:assert/strict');
const { initAvailability } = require('../static/availability');

test('only marked database outages navigate to the outage page', async () => {
  for (const [status, marker, expected] of [[503, '1', ['/unavailable']], [503, null, []], [200, null, []]]) {
    const navigations = [];
    const response = { status, headers: { get: () => marker } };
    const win = { fetch: async () => response, location: { assign: (url) => navigations.push(url) } };
    initAvailability(win);
    assert.equal(await win.fetch('/containers/reorder'), response);
    assert.deepEqual(navigations, expected);
  }
});
