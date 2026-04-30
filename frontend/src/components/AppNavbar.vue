<template>
  <nav class="navbar">
    <div class="container navbar-inner">
      <router-link to="/" class="navbar-brand">BoKe</router-link>
      <button class="navbar-toggle" @click="mobileOpen = !mobileOpen" aria-label="切换菜单">
        <span :class="{ open: mobileOpen }"></span>
      </button>
      <div class="navbar-actions" :class="{ 'navbar-actions-open': mobileOpen }">
        <nav class="navbar-links">
          <router-link to="/" class="nav-link" @click="mobileOpen = false">仪表盘</router-link>
          <router-link to="/documents" class="nav-link" @click="mobileOpen = false">文档列表</router-link>
          <router-link to="/favorites" class="nav-link" @click="mobileOpen = false">我的收藏</router-link>
        </nav>
        <SearchBar />
        <button class="btn btn-sm" @click="handleLogout">退出登录</button>
      </div>
    </div>
  </nav>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import SearchBar from './SearchBar.vue'

const router = useRouter()
const authStore = useAuthStore()
const mobileOpen = ref(false)

async function handleLogout() {
  await authStore.logout()
  router.push('/login')
}
</script>

<style scoped>
.navbar {
  background: var(--bg-card);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  z-index: 100;
}
.navbar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: 3.5rem;
  gap: 1rem;
}
.navbar-brand {
  font-size: 1.125rem;
  font-weight: 700;
  color: var(--text);
  text-decoration: none;
  white-space: nowrap;
}
.navbar-brand:hover { text-decoration: none; }
.navbar-actions {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.navbar-links {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.nav-link {
  font-size: 0.8125rem;
  font-weight: 500;
  color: var(--text-secondary);
  text-decoration: none;
  padding: 0.375rem 0.625rem;
  border-radius: var(--radius);
  transition: color var(--transition-fast), background var(--transition-fast);
}
.nav-link:hover,
.nav-link.router-link-exact-active {
  color: var(--text);
  background: var(--bg);
}

/* Mobile hamburger */
.navbar-toggle {
  display: none;
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  width: 2rem;
  height: 2rem;
  position: relative;
}
.navbar-toggle span,
.navbar-toggle span::before,
.navbar-toggle span::after {
  display: block;
  width: 1.25rem;
  height: 2px;
  background: var(--text);
  border-radius: 2px;
  transition: background var(--transition-fast), transform var(--transition-fast);
  position: absolute;
  left: 0.375rem;
}
.navbar-toggle span { top: 50%; transform: translateY(-50%); }
.navbar-toggle span::before { content: ''; top: -6px; }
.navbar-toggle span::after { content: ''; top: 6px; }
.navbar-toggle span.open { background: transparent; }
.navbar-toggle span.open::before { top: 0; transform: rotate(45deg); }
.navbar-toggle span.open::after { top: 0; transform: rotate(-45deg); }

@media (max-width: 640px) {
  .navbar-toggle { display: flex; align-items: center; justify-content: center; }
  .navbar-actions {
    display: none;
    position: absolute;
    top: 3.5rem;
    left: 0;
    right: 0;
    background: var(--bg-card);
    border-bottom: 1px solid var(--border);
    padding: 0.75rem 1rem;
    flex-direction: column;
    gap: 0.75rem;
    box-shadow: var(--shadow);
  }
  .navbar-actions-open { display: flex; }
  .navbar-links {
    flex-direction: column;
    align-items: stretch;
    gap: 0.25rem;
  }
}
</style>
