const SHELL = "sosflow-reporter-shell-v1";
const ASSETS = ["/", "/report", "/offline.html", "/manifest.webmanifest", "/icons/sosflow-192.svg", "/icons/sosflow-512.svg"];

self.addEventListener("install", (event) => event.waitUntil(caches.open(SHELL).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting())));
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));
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
