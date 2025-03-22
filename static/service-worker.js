self.addEventListener('install', (event) => {
    event.waitUntil(
        caches.open('golf-app-cache').then((cache) => {
            return cache.addAll([
                '/',
                '/offline',
                '/static/manifest.json',
                '/static/styles.css',
                '/static/icons/icon_192.png',
                '/static/icons/icon_512.png',
                '/static/icons/apple-touch-icon.png',
            ]);
        })
    );
});

self.addEventListener('fetch', (event) => {
    event.respondWith(
        fetch(event.request).catch(() =>
            caches.match(event.request).then((response) =>
                response || caches.match('/offline')
            )
        )
    );
});