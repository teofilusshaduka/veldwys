// VeldWys service worker — app shell cache so the farm register opens without signal.
const CACHE = "veldwys-v12";
const SHELL = [
  "/", "/static/index.html", "/static/app.js", "/static/i18n.js", "/static/styles.css",
  "/static/places.js", "/manifest.json", "/static/icon.svg",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css",
  "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js",
];

self.addEventListener("install", (e) => {
  e.waitUntil(
    caches.open(CACHE)
      // cache:"reload" bypasses the browser's HTTP cache. Without it a new service
      // worker happily re-caches the stale files it was published to replace.
      .then((c) => Promise.allSettled(
        SHELL.map((u) => fetch(new Request(u, { cache: "reload" }))
          .then((res) => (res && res.ok ? c.put(u, res) : null)))
      ))
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

  // Stale-while-revalidate: answer from cache instantly (this has to open with no
  // signal), and refresh in the background so the next open is current.
  //
  // The background refresh MUST bypass the browser's own HTTP cache. Revalidating
  // with the default cache mode re-reads the stale file the browser already has and
  // writes it straight back here, so the shell can never move forward — the reason
  // frontend fixes kept "not showing up on the device". ETags keep this cheap: an
  // unchanged file costs a 304, not a download.
  const cacheable = url.origin === location.origin || url.host.includes("unpkg.com");
  e.respondWith(
    caches.match(e.request).then((hit) => {
      const network = fetch(cacheable ? new Request(e.request, { cache: "no-cache" }) : e.request)
        .then((res) => {
          if (res && res.status === 200 && cacheable) {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(e.request, copy));
          }
          return res;
        })
        .catch(() => hit);
      return hit || network;
    })
  );
});
