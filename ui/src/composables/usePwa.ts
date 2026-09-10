import { onMounted, ref } from 'vue'

export function usePwa() {
  const needRefresh = ref(false)
  const offline = ref(!navigator.onLine)
  const updateSW = ref<(() => Promise<void>) | null>(null)

  let registration: ServiceWorkerRegistration | undefined

  async function registerServiceWorker() {
    if (!('serviceWorker' in navigator)) return

    const { registerSW } = await import('virtual:pwa-register')
    updateSW.value = registerSW({
      immediate: true,
      onNeedRefresh() {
        needRefresh.value = true
      },
      onOfflineReady() {
        /* precache ready */
      },
      onRegistered(reg) {
        registration = reg
      },
    })
  }

  async function applyUpdate() {
    needRefresh.value = false
    updateSW.value?.()
  }

  onMounted(() => {
    void registerServiceWorker()

    window.addEventListener('online', () => {
      offline.value = false
    })
    window.addEventListener('offline', () => {
      offline.value = true
    })
  })

  return {
    needRefresh,
    offline,
    registration,
    applyUpdate,
  }
}
