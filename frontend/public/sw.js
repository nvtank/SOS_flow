const SHELL = "sosflow-reporter-shell-v2";
const ASSETS = ["/", "/report", "/offline.html", "/manifest.webmanifest", "/icons/sosflow-192.svg", "/icons/sosflow-512.svg"];

async function cacheReporterShell() {
  const cache = await caches.open(SHELL);
  await cache.addAll(ASSETS);
  // Vite emits content-hashed JS/CSS names. Discover them from index.html so
  // the first service-worker install is enough for a real offline reload.
  const index = await fetch("/");
  const html = await index.clone().text();
  await cache.put("/", index);
  const builtAssets = [...html.matchAll(/(?:src|href)="(\/assets\/[^"]+)"/g)].map((match) => match[1]);
  if (builtAssets.length) await cache.addAll([...new Set(builtAssets)]);
}

self.addEventListener("install", (event) => event.waitUntil(cacheReporterShell().then(() => self.skipWaiting())));
self.addEventListener("activate", (event) => event.waitUntil(
  caches.keys().then((keys) => Promise.all(keys.filter((key) => key.startsWith("sosflow-reporter-shell-") && key !== SHELL).map((key) => caches.delete(key)))).then(() => self.clients.claim())
));
self.addEventListener("fetch", (event) => {
  const request = event.request;
  const url = new URL(request.url);
  // API responses can contain operational/admin data; never place them in Cache Storage.
  if (url.pathname.startsWith("/api/") || url.origin !== self.location.origin) return;
  if (request.mode === "navigate") {
    event.respondWith(fetch(request).catch(() => caches.match("/report").then((response) => response || caches.match("/offline.html"))));
    return;
  }
  event.respondWith(caches.match(request).then((cached) => cached || fetch(request).then((response) => {
    if (response.ok && (url.pathname.startsWith("/assets/") || url.pathname.startsWith("/icons/"))) caches.open(SHELL).then((cache) => cache.put(request, response.clone()));
    return response;
  }))));
});
