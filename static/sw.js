// VeldWys service worker — app shell cache so the farm register opens without signal.
const CACHE = "veldwys-v7";
const SHELL = [
  "/", "/static/index.html", "/static/app.js", "/static/i18n.js", "/static/styles.css",
  "/manifest.json", "/static/icon.svg",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      .then((c) => Promise.allSettled(SHELL.map((u) => c.add(u))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", (e) => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;                 // writes go through the app's own queue
  if (url.pathname.startsWith("/api/")) return;           // API freshness matters; app caches data itself

  // Cache-first for the shell, network fallback that refreshes the cache.
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const network = fetch(e.request).then((res) => {
        if (res && res.status === 200 && (url.origin === location.origin || url.host.includes("unpkg.com"))) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(e.request, copy));
        }
        return res;
      }).catch(() => hit);
      return hit || network;
    })
  );
});
