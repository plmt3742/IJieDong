import { createPinia } from 'pinia'
import { createApp } from 'vue'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

import 'element-plus/dist/index.css'
import '@/styles/element.css'
import '@/styles/base.css'

import App from './App.vue'
import { setUnauthorizedHandler } from '@/api/http'
import { router } from '@/router'
import { useAuthStore } from '@/stores/auth'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })

/**
 * Global 401 handling: drop the session, then send the user to /login with a
 * return path. Registered here so the HTTP client never imports router/pinia.
 */
setUnauthorizedHandler(() => {
  const auth = useAuthStore(pinia)
  auth.clearSession()
  const current = router.currentRoute.value
  if (current.name !== 'login') {
    void router.replace({ path: '/login', query: { redirect: current.fullPath } })
  }
})

app.mount('#app')
