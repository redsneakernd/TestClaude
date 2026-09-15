var CACHE_NAME = "bmls-shell-v2";
var APP_SHELL = [
  "./",
  "index.html",
  "css/style.css",
  "js/app.js",
  "data/locations.csv",
  "manifest.json",
  "icons/icon.svg"
];
var CDN_ASSETS = [
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.css",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/MarkerCluster.Default.css",
  "https://cdnjs.cloudflare.com/ajax/libs/leaflet.markercluster/1.5.3/leaflet.markercluster.js"
];

self.addEventListener("install", function (event) {
  event.waitUntil(
    caches.open(CACHE_NAME).then(function (cache) {
      return cache.addAll(APP_SHELL).then(function () {
        // Best-effort: don't fail install if the CDN is unreachable right now.
        return Promise.all(
          CDN_ASSETS.map(function (url) {
            return cache.add(new Request(url, { mode: "cors" })).catch(function () {});
          })
        );
      });
    })
  );
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(
        keys.filter(function (key) { return key !== CACHE_NAME; }).map(function (key) { return caches.delete(key); })
      );
    })
  );
  self.clients.claim();
});

// Cache-first for the app shell and the pinned Leaflet library files, so the
// map still works offline after a first successful visit. Map tiles and
// anything else cross-origin go straight to the network (they're too many
// and change too often to usefully cache).
self.addEventListener("fetch", function (event) {
  var url = event.request.url;
  var sameOrigin = url.indexOf(self.location.origin) === 0;
  var isPinnedCdnAsset = CDN_ASSETS.indexOf(url) !== -1;
  if (!sameOrigin && !isPinnedCdnAsset) return;

  event.respondWith(
    caches.match(event.request).then(function (cached) {
      if (cached) return cached;
      return fetch(event.request).then(function (response) {
        var copy = response.clone();
        caches.open(CACHE_NAME).then(function (cache) { cache.put(event.request, copy); });
        return response;
      }).catch(function () { return cached; });
    })
  );
});
