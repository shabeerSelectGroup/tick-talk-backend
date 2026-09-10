import { createApp } from 'vue'
import { createPinia } from 'pinia'
import { setupAdminInterceptors } from '@/api/adminInterceptors'
import App from './App.vue'
import router from './router'
import './styles/main.css'

/** Drop stale dev service workers so API POST (join) is not intercepted. */
if (import.meta.env.DEV && 'serviceWorker' in navigator) {
  void navigator.serviceWorker.getRegistrations().then((regs) => {
    for (const reg of regs) void reg.unregister()
  })
}

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
setupAdminInterceptors()
app.use(router)
app.mount('#app')
