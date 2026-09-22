/* AI 英語家教 — Service Worker
   策略：
   - 靜態 app shell 預先快取，可離線開啟介面。
   - 導覽請求（開網頁）走「網路優先、離線退回快取」，確保更新能傳到裝置。
   - 其他同源 GET 走「快取優先、退回網路並回填」。
   - 跨網域請求（Gemini API、Google 字型等）一律不攔截，直接放行。
   改版時只要把 CACHE 版本號 +1，舊快取會自動清除。
*/
const CACHE = 'ai-eng-tutor-v6';
const SHELL = [
  './',
  './index.html',
  './manifest.webmanifest',
  './icons/icon-192.png',
  './icons/icon-512.png',
  './icons/maskable-512.png',
  './icons/apple-touch-icon.png',
  './avatars/emma_full.png',
  './avatars/ryan_full.png',
  './avatars/emma_head.png',
  './avatars/ryan_head.png',
  './words.json',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  // 只處理同源請求；API / 外部資源直接交給瀏覽器。
  if (url.origin !== self.location.origin) return;

  // words.json：網路優先（拿最新單字），離線時退回快取。
  if (url.pathname.endsWith('/words.json') || url.pathname.endsWith('words.json')) {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy));
          return res;
        })
        .catch(() => caches.match(req))
    );
    return;
  }

  // 導覽（開啟頁面）：網路優先，離線時退回快取的 index。
  if (req.mode === 'navigate') {
    e.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put('./index.html', copy));
          return res;
        })
        .catch(() => caches.match('./index.html'))
    );
    return;
  }

  // 其他靜態資源：快取優先，退回網路並回填。
  e.respondWith(
    caches.match(req).then((hit) =>
      hit ||
      fetch(req).then((res) => {
        const copy = res.clone();
        caches.open(CACHE).then((c) => c.put(req, copy));
        return res;
      }).catch(() => hit)
    )
  );
});
