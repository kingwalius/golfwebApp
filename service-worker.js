const CACHE_NAME = 'golf-app-v2';
const STATIC_ASSETS = [
  '/',
  '/offline',
  '/personal_score_offline',
  '/record_score',
  '/static/styles.css',
  '/static/manifest.json',
  '/static/icons/icon_192.png',
  '/static/icons/icon_512.png',
  '/static/icons/apple-touch-icon.png',
];

self.addEventListener('install', function (event) {
    event.waitUntil(
      caches.open(CACHE_NAME).then(function (cache) {
        return cache.addAll(STATIC_ASSETS);
      })
    );
  });

// ✅ Handle fetch with dynamic route support
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (url.pathname === '/user_rounds') {
    event.respondWith(fetch(event.request));
    return;
  }
  // ✅ Cache `/record_score` and `/personal_score` dynamically
  const dynamicRoutes = ['/record_score', '/personal_score'];

  if (dynamicRoutes.some(route => url.pathname.startsWith(route))) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          return caches.open(CACHE_NAME).then((cache) => {
            cache.put(event.request, response.clone());
            return response;
          });
        })
        .catch(() => caches.match(event.request).then(res => res || caches.match('/offline')))
    );
    return;
  }

  // ✅ Fallback for static or other pages
  event.respondWith(
    fetch(event.request)
      .catch(() => caches.match(event.request).then(res => res || caches.match('/offline')))
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keyList) =>
      Promise.all(
        keyList.map((key) => {
          if (key !== CACHE_NAME) return caches.delete(key);
        })
      )
    )
  );
});