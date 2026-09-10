import { ref } from 'vue'
import { api, unwrap } from '@/api/client'

const VAPID_PUBLIC_ENV = import.meta.env.VITE_VAPID_PUBLIC_KEY as string | undefined
const vapidPublicKey = ref(VAPID_PUBLIC_ENV ?? '')

function urlBase64ToUint8Array(base64String: string): Uint8Array {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4)
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/')
  const raw = atob(base64)
  const arr = new Uint8Array(raw.length)
  for (let i = 0; i < raw.length; i++) arr[i] = raw.charCodeAt(i)
  return arr
}

export function usePushNotifications(registration?: ServiceWorkerRegistration) {
  const supported = ref(
    typeof window !== 'undefined' &&
      'Notification' in window &&
      'serviceWorker' in navigator &&
      'PushManager' in window
  )
  const permission = ref<NotificationPermission>(
    typeof Notification !== 'undefined' ? Notification.permission : 'default'
  )
  const subscribed = ref(false)
  const error = ref('')

  async function loadConfig() {
    try {
      const cfg = await unwrap<{ public_key: string; enabled: boolean }>(
        await api.get('/participant/push/config')
      )
      if (cfg.public_key) vapidPublicKey.value = cfg.public_key
    } catch {
      /* optional */
    }
  }

  async function subscribe(): Promise<boolean> {
    error.value = ''
    if (!vapidPublicKey.value) await loadConfig()
    if (!supported.value || !vapidPublicKey.value) {
      error.value = 'Push notifications are not configured on this server'
      return false
    }

    const perm = await Notification.requestPermission()
    permission.value = perm
    if (perm !== 'granted') {
      error.value = 'Notification permission denied'
      return false
    }

    const reg =
      registration ?? (await navigator.serviceWorker.ready)
    const existing = await reg.pushManager.getSubscription()
    const sub =
      existing ??
      (await reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(vapidPublicKey.value),
      }))

    const json = sub.toJSON()
    await unwrap(
      await api.post('/participant/push/subscribe', {
        endpoint: json.endpoint,
        keys: json.keys,
      })
    )
    subscribed.value = true
    return true
  }

  async function unsubscribe(): Promise<void> {
    const reg = registration ?? (await navigator.serviceWorker.ready)
    const sub = await reg.pushManager.getSubscription()
    if (sub) {
      const json = sub.toJSON()
      try {
        await api.post('/participant/push/unsubscribe', { endpoint: json.endpoint })
      } catch {
        /* ignore */
      }
      await sub.unsubscribe()
    }
    subscribed.value = false
  }

  async function checkSubscription() {
    if (!supported.value) return
    try {
      const reg = await navigator.serviceWorker.ready
      const sub = await reg.pushManager.getSubscription()
      subscribed.value = !!sub
    } catch {
      subscribed.value = false
    }
  }

  return {
    supported,
    permission,
    subscribed,
    error,
    subscribe,
    unsubscribe,
    checkSubscription,
    loadConfig,
  }
}
