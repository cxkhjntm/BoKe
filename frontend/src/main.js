// Fix: Edge (Windows) minimization bug caused by vue-router's beforeUnloadListener
// When the window is being minimized, vue-router calls history.replaceState() to save
// scroll position, but on Edge/Windows this causes the window to immediately restore.
// See: https://github.com/vuejs/router/issues/2644
if (/Edg\//.test(navigator.userAgent)) {
  const originalReplaceState = history.replaceState.bind(history)
  history.replaceState = function (state, title, url) {
    if (document.visibilityState === 'hidden') return
    return originalReplaceState(state, title, url)
  }
}

import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)
app.mount('#app')
