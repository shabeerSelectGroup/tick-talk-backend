/// <reference lib="webworker" />
import { clientsClaim } from 'workbox-core'
import { ExpirationPlugin } from 'workbox-expiration'
import { precacheAndRoute, createHandlerBoundToURL } from 'workbox-precaching'
import { registerRoute, NavigationRoute } from 'workbox-routing'
import {
  CacheFirst,
  NetworkFirst,
  NetworkOnly,
  StaleWhileRevalidate,
} from 'workbox-strategies'

declare let self: ServiceWorkerGlobalScope & {
  __WB_MANIFEST: Array<string | { url: string; revision: string | null }>
}

precacheAndRoute(self.__WB_MANIFEST)
clientsClaim()
self.skipWaiting()

// SPA navigations — app shell (offline-capable after first visit)
const navigationHandler = createHandlerBoundToURL('/index.html')
registerRoute(new NavigationRoute(navigationHandler))

// Mutating API calls must never go through cache strategies (fixes join POST hanging).
registerRoute(
  ({ url, request }) =>
    url.pathname.startsWith('/api/') &&
    request.method !== 'GET' &&
    request.method !== 'HEAD',
  new NetworkOnly()
)

// API reads — network first, short offline tolerance
registerRoute(
  ({ url, request }) =>
    url.pathname.startsWith('/api/') &&
    (request.method === 'GET' || request.method === 'HEAD'),
  new NetworkFirst({
    cacheName: 'ticktalk-api',
    networkTimeoutSeconds: 12,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 64,
        maxAgeSeconds: 5 * 60,
      }),
    ],
  })
)

// Media / selfies — stale-while-revalidate
registerRoute(
  ({ url }) => url.pathname.includes('/media/') || url.hostname.includes('r2'),
  new StaleWhileRevalidate({
    cacheName: 'ticktalk-media',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 120,
        maxAgeSeconds: 7 * 24 * 60 * 60,
      }),
    ],
  })
)

// Static assets from CDN-like paths
registerRoute(
  ({ request }) => request.destination === 'image' || request.destination === 'font',
  new CacheFirst({
    cacheName: 'ticktalk-static',
    plugins: [
      new ExpirationPlugin({
        maxEntries: 80,
        maxAgeSeconds: 30 * 24 * 60 * 60,
      }),
    ],
  })
)

self.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    self.skipWaiting()
  }
})

self.addEventListener('push', (event) => {
  if (!event.data) return
  let payload: { title?: string; body?: string; url?: string } = {}
  try {
    payload = event.data.json()
  } catch {
    payload = { title: 'Tick Talk', body: event.data.text() }
  }
  const title = payload.title ?? 'Tick Talk'
  const options: NotificationOptions = {
    body: payload.body ?? '',
    icon: '/icons/icon-192.png',
    badge: '/icons/icon-72.png',
    data: { url: payload.url ?? '/' },
    tag: 'ticktalk-push',
  }
  event.waitUntil(self.registration.showNotification(title, options))
})

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  const url = (event.notification.data?.url as string) ?? '/'
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client && client.url.includes(self.location.origin)) {
          return client.focus()
        }
      }
      return self.clients.openWindow(url)
    })
  )
})
