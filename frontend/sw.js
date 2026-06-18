const CACHE_NAME = 'bidel-v20260618_094706';

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  // index.html و API هیچ‌وقت cache نمی‌شن
  if (url.pathname === '/' || url.pathname === '/index.html' || url.pathname.startsWith('/api/')) {
    e.respondWith(fetch(e.request));
    return;
  }
  // فونت‌ها و آیکون‌ها cache می‌شن
  e.respondWith(
    caches.match(e.request).then(cached => {
      if (cached) return cached;
      return fetch(e.request).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(e.request, clone));
        }
        return resp;
      });
    })
  );
});
