// Minimal service worker — exists purely so Chrome surfaces the
// "Install app" prompt on Android (Chrome requires a registered SW
// with a fetch handler for full PWA installability). We do NOT cache
// anything here; every request passes through to the network exactly
// as it would without the SW.
//
// If venue WiFi turns out to be unreliable at the event, we can layer
// offline caching into the fetch handler below. For now: empty.

self.addEventListener("install", () => {
  // Activate immediately on first install rather than waiting for
  // every old client to close — avoids the user having to refresh
  // before the install prompt appears.
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("fetch", () => {
  // Passthrough. The presence of this listener is what satisfies
  // Chrome's installability check — we deliberately don't intercept.
});
