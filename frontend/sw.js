const CACHE_NAME = 'bidel-v20261116_023405';
const INDEX_CACHE = 'bidel-index';   // نسخهٔ آفلاین index.html (فقط وقتی شبکه نیست استفاده می‌شود)
const DATA_CACHE = 'bidel-data';     // پاسخ‌های شعر که کاربر دیده (برای خواندن آفلاین)
const DATA_MAX = 400;

// فقط محتوای عمومی و ثابت شعر؛ هرگز مسیرهای کاربری (auth، bookmarks، notes، profile، history)
const DATA_RE = /^\/api\/(poems\/(ghazal|terjee|zand)\/\d+|poems\/(ghazals|terjees|zand)|keywords\/[^/]+)$/;

self.addEventListener('install', e => {
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  const keep = new Set([CACHE_NAME, INDEX_CACHE, DATA_CACHE]);
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => !keep.has(k)).map(k => caches.delete(k)))
    ).then(() => self.clients.claim())
  );
});

async function trim(cache) {
  const keys = await cache.keys();
  if (keys.length > DATA_MAX) await Promise.all(keys.slice(0, keys.length - DATA_MAX).map(k => cache.delete(k)));
}

// شبکه اول؛ اگر قطع بود از کش
async function networkFirst(req, cacheName) {
  const cache = await caches.open(cacheName);
  try {
    const resp = await fetch(req);
    if (resp.ok) { cache.put(req, resp.clone()); if (cacheName === DATA_CACHE) trim(cache); }
    return resp;
  } catch (err) {
    const hit = await cache.match(req, { ignoreSearch: false });
    if (hit) return hit;
    throw err;
  }
}

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // صفحه‌ها: همیشه از شبکه (بدون کش مرورگر)؛ فقط در حالت آفلاین نسخهٔ ذخیره‌شده
  if (req.mode === 'navigate') {
    e.respondWith((async () => {
      try {
        const resp = await fetch(req);
        if (resp.ok && resp.headers.get('content-type')?.includes('text/html')) {
          const c = await caches.open(INDEX_CACHE);
          c.put('/index.html', resp.clone());
        }
        return resp;
      } catch (err) {
        const c = await caches.open(INDEX_CACHE);
        const hit = await c.match('/index.html');
        if (hit) return hit;
        throw err;
      }
    })());
    return;
  }

  if (url.pathname === '/index.html') return;

  // محتوای شعر: شبکه اول با پشتیبان کش
  if (DATA_RE.test(url.pathname)) {
    e.respondWith(networkFirst(req, DATA_CACHE));
    return;
  }

  // بقیهٔ API: بدون دخالت
  if (url.pathname.startsWith('/api/')) return;

  // فونت‌ها و آیکون‌ها: کش اول
  e.respondWith(
    caches.match(req).then(cached => {
      if (cached) return cached;
      return fetch(req).then(resp => {
        if (resp.ok) {
          const clone = resp.clone();
          caches.open(CACHE_NAME).then(c => c.put(req, clone));
        }
        return resp;
      });
    })
  );
});
