// Service Worker for V6.0 PWA
const CACHE_NAME = 'v6-app-v2';
const urlsToCache = [
  '/static/manifest.json',
  '/static/css/style.css',
  '/static/js/pwa.js'
];

// 安装时仅缓存静态资源（不再缓存需要登录的页面）
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        console.log('✅ V6.0 缓存已打开');
        return cache.addAll(urlsToCache);
      })
      .then(() => {
        console.log('✅ V6.0 静态资源缓存完成');
        return self.skipWaiting();
      })
  );
});

// 激活时清理旧缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== CACHE_NAME) {
            console.log('🗑️ 删除旧缓存:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => {
      console.log('✅ V6.0 Service Worker 激活');
      return self.clients.claim();
    })
  );
});

// 请求拦截
self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;

  const requestUrl = new URL(event.request.url);
  const acceptHeader = event.request.headers.get('accept') || '';
  const isHtmlRequest = acceptHeader.includes('text/html');

  // HTML 页面请求：始终走网络，不缓存
  // 这样服务端可以在会话过期时正确重定向到登录页
  if (isHtmlRequest) {
    event.respondWith(fetch(event.request));
    return;
  }

  // 静态资源：缓存优先策略
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        if (response) return response;
        
        return fetch(event.request)
          .then(response => {
            if (!response || response.status !== 200 || response.type !== 'basic') {
              return response;
            }
            
            const responseToCache = response.clone();
            caches.open(CACHE_NAME)
              .then(cache => cache.put(event.request, responseToCache));
            
            return response;
          });
      })
  );
});

// 处理推送通知
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  
  const title = data.title || '开标数据 V6';
  const options = {
    body: data.body || '您有一条新消息',
    icon: '/static/icons/icon-192.png',
    badge: '/static/icons/icon-72.png',
    vibrate: [200, 100, 200],
    data: {
      url: data.url || '/dashboard',
      timestamp: Date.now()
    },
    actions: [
      { action: 'open', title: '查看' },
      { action: 'dismiss', title: '忽略' }
    ],
    tag: data.tag || 'v6-notification',
    renotify: true
  };

  event.waitUntil(
    self.registration.showNotification(title, options)
  );
});

// 处理通知点击
self.addEventListener('notificationclick', event => {
  event.notification.close();

  if (event.action === 'dismiss') {
    return;
  }

  event.waitUntil(
    clients.matchAll({ type: 'window', includeUncontrolled: true })
      .then(clientList => {
        const url = event.notification.data.url;
        
        for (const client of clientList) {
          if (client.url.includes(url) && 'focus' in client) {
            return client.focus();
          }
        }
        
        if (clients.openWindow) {
          return clients.openWindow(url);
        }
      })
  );
});
