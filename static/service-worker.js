const VERSION = "rgbridge-pwa-v1";
const swUrl = new URL(self.location.href);
const basePath = swUrl.pathname.replace(/\/sw\.js$/, "");
const rootPath = basePath.endsWith("/") ? basePath : `${basePath}/`;

const PRECACHE_URLS = [
  rootPath,
  `${rootPath}manifest.webmanifest`,
  `${rootPath}static/bridge.css`,
  `${rootPath}static/consultant.png`,
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) => cache.addAll(PRECACHE_URLS)),
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((k) => k !== VERSION).map((k) => caches.delete(k))),
      ),
  );
  self.clients.claim();
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;

  const reqUrl = new URL(event.request.url);
  if (reqUrl.origin !== self.location.origin) return;

  // Network-first for navigation; fall back to cached shell.
  if (event.request.mode === "navigate") {
    event.respondWith(
      fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(VERSION).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => caches.match(event.request).then((cached) => cached || caches.match(rootPath))),
    );
    return;
  }

  // Cache-first for same-origin GETs; update cache in background.
  event.respondWith(
    caches.match(event.request).then((cached) => {
      const networkFetch = fetch(event.request)
        .then((response) => {
          const copy = response.clone();
          caches.open(VERSION).then((cache) => cache.put(event.request, copy));
          return response;
        })
        .catch(() => cached);

      return cached || networkFetch;
    }),
  );
});
