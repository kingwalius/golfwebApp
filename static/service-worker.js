self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('golf-app-cache').then((cache) => {
            return cache.addAll([
                '/',
                '/static/manifest.json',
                '/static/styles.css',
                '/static/icons/Icon_192.png',
                '/static/icons/Icon_512.png'
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        caches.match(event.request).then((response) => {
            return response || fetch(event.request);
        })
    );
});