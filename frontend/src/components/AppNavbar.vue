<template>
  <nav class="navbar">
    <div class="container navbar-inner">
      <router-link to="/" class="navbar-brand">BoKe</router-link>
      <button class="navbar-toggle" @click="mobileOpen = true" aria-label="打开菜单">
        <span></span>
      </button>
      <div class="navbar-actions desktop-only">
        <nav class="navbar-links">
          <router-link to="/" class="nav-link">仪表盘</router-link>
          <router-link to="/documents" class="nav-link">文档列表</router-link>
          <router-link to="/favorites" class="nav-link">我的收藏</router-link>
          <router-link to="/categories" class="nav-link">文档分类</router-link>
          <router-link to="/chat" class="nav-link">AI对话</router-link>
        </nav>
        <SearchBar />
        <SettingsDropdown @open-settings="settingsOpen = true" />
      </div>
    </div>
  </nav>

  <!-- Mobile Drawer -->
  <transition name="fade-slide">
    <div v-if="mobileOpen" class="drawer-overlay" @click="mobileOpen = false">
      <div class="drawer-content" @click.stop>
        <div style="display: flex; justify-content: flex-end; margin-bottom: 1rem;">
          <button class="btn btn-sm" @click="mobileOpen = false">关闭</button>
        </div>
        <nav class="navbar-links-mobile">
          <router-link to="/" class="nav-link" @click="mobileOpen = false">仪表盘</router-link>
          <router-link to="/documents" class="nav-link" @click="mobileOpen = false">文档列表</router-link>
          <router-link to="/favorites" class="nav-link" @click="mobileOpen = false">我的收藏</router-link>
          <router-link to="/categories" class="nav-link" @click="mobileOpen = false">文档分类</router-link>
          <router-link to="/chat" class="nav-link" @click="mobileOpen = false">AI对话</router-link>
        </nav>
        <div style="margin-top: 1rem">
          <SearchBar />
        </div>
      </div>
    </div>
  </transition>

  <SettingsModal v-if="settingsOpen" @close="settingsOpen = false" />
</template>

<script setup>
import { ref } from 'vue'
import SearchBar from './SearchBar.vue'
import SettingsDropdown from './SettingsDropdown.vue'
import SettingsModal from './SettingsModal.vue'

const mobileOpen = ref(false)
const settingsOpen = ref(false)
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
  .desktop-only { display: none !important; }
  .navbar-links-mobile {
    display: flex;
    flex-direction: column;
    align-items: stretch;
    gap: 0.5rem;
  }
}
</style>
