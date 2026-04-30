import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('../views/Login.vue'),
    meta: { guest: true },
  },
  {
    path: '/',
    name: 'Documents',
    component: () => import('../views/Documents.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/documents/:id',
    name: 'Reader',
    component: () => import('../views/Reader.vue'),
    meta: { requiresAuth: true },
  },
  {
    path: '/:pathMatch(.*)*',
    redirect: '/',
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const authStore = useAuthStore()
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return { name: 'Login' }
  }
  if (to.meta.guest && authStore.isAuthenticated) {
    return { name: 'Documents' }
  }
})

export default router
