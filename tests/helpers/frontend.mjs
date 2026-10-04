import { readFile } from 'node:fs/promises';
import { JSDOM } from 'jsdom';

const html = await readFile(new URL('../../frontend/index.html', import.meta.url), 'utf8');
const script = await readFile(new URL('../../frontend/app.js', import.meta.url), 'utf8');

export const jsonResponse = (body, status = 200) => ({
  ok: status >= 200 && status < 300,
  status,
  json: async () => body,
});

export const flush = () => new Promise(resolve => setImmediate(resolve));

// Load the production HTML and script, stubbing only network/media browser APIs.
// An optional fetch handler returns undefined to use the default read-only routes.
export async function createFrontend({ jobs = [], fetch: handleFetch, setup } = {}) {
  const dom = new JSDOM(html, { runScripts: 'outside-only', url: 'http://calligraphy.test/' });
  const { window } = dom;
  const { document } = window;
  await new Promise(resolve => window.addEventListener('load', resolve, { once: true }));

  const requests = [];
  const mediaEvents = [];
  const intervals = new Map();
  const timeouts = new Map();
  let timerId = 0;
  window.HTMLElement.prototype.scrollIntoView = function () {};
  for (const method of ['load', 'pause', 'play']) {
    window.HTMLMediaElement.prototype[method] = function () {
      mediaEvents.push({ method, element: this, src: this.getAttribute('src') });
      if (method === 'play') return Promise.resolve();
    };
  }
  window.setInterval = callback => {
    intervals.set(++timerId, callback);
    return timerId;
  };
  window.clearInterval = id => intervals.delete(id);
  window.setTimeout = callback => {
    timeouts.set(++timerId, callback);
    return timerId;
  };
  window.clearTimeout = id => timeouts.delete(id);
  window.fetch = async (url, options = {}) => {
    const request = { url, options, body: options.body ? JSON.parse(options.body) : undefined };
    requests.push(request);
    const response = await handleFetch?.(request);
    if (response !== undefined) return response;
    if (url === '/api/styles') return jsonResponse({ styles: [{ id: 'kai', name: 'Kai', description: 'Fixture' }] });
    if (url === '/api/font-catalog') return jsonResponse([]);
    if (url === '/api/jobs') return jsonResponse({ jobs });
    throw new Error(`Unexpected request: ${url}`);
  };
  await setup?.(window);
  window.eval(script);
  document.dispatchEvent(new window.Event('DOMContentLoaded'));
  await flush();

  return {
    window, document, requests, mediaEvents, intervals, timeouts,
    async tickTimeouts() {
      const pending = [...timeouts.entries()];
      for (const [id] of pending) timeouts.delete(id);
      await Promise.all(pending.map(([, callback]) => callback()));
      await flush();
    },
    async tickIntervals() {
      await Promise.all([...intervals.values()].map(callback => callback()));
      await flush();
    },
    close: () => window.close(),
  };
}
