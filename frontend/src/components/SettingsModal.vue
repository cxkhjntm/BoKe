<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="emit('close')">
      <div class="modal-content">
        <div class="modal-header">
          <h3>个人设置</h3>
          <button class="modal-close" @click="emit('close')" aria-label="关闭">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div class="modal-body">
          <!-- Avatar section (unchanged) -->
          <div class="section">
            <label class="form-label">个人头像</label>
            <div class="avatar-area">
              <div class="avatar-preview">
                <img v-if="avatarPreview" :src="avatarPreview" alt="头像预览" />
                <svg v-else viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                  <circle cx="12" cy="8" r="4" /><path d="M4 21v-1a6 6 0 0 1 12 0v1" />
                </svg>
              </div>
              <div class="avatar-actions">
                <button class="btn btn-sm" @click="avatarInput.click()">上传头像</button>
                <button v-if="authStore.userProfile?.avatar_path" class="btn btn-sm btn-danger" @click="removeAvatar">移除</button>
              </div>
              <input ref="avatarInput" type="file" accept="image/*" class="hidden-input" @change="onAvatarSelect" />
            </div>
          </div>

          <!-- Multi-background section -->
          <div class="section">
            <label class="form-label">背景图片（最多10张，自动轮播）</label>
            <div class="bg-grid">
              <div
                v-for="bg in backgrounds"
                :key="bg.id"
                class="bg-thumb"
              >
                <div class="bg-thumb-img" :style="bgThumbStyle(bg)"></div>
                <button class="bg-thumb-delete" @click="removeBackground(bg.id)" title="删除">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <line x1="18" y1="6" x2="6" y2="18" /><line x1="6" y1="6" x2="18" y2="18" />
                  </svg>
                </button>
              </div>
              <button
                v-if="backgrounds.length < 10"
                class="bg-add"
                @click="bgInput.click()"
              >
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                  <line x1="12" y1="5" x2="12" y2="19" /><line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                <span>添加</span>
              </button>
            </div>
            <input ref="bgInput" type="file" accept="image/*" class="hidden-input" @change="onBgUpload" />
            <p v-if="backgrounds.length === 0" class="bg-empty">暂无背景图</p>
          </div>

          <!-- Carousel interval -->
          <div class="section" v-if="backgrounds.length > 1">
            <label class="form-label">轮播间隔: {{ interval }}秒</label>
            <input
              type="range"
              class="slider"
              min="1"
              max="60"
              step="1"
              v-model.number="interval"
              @input="onIntervalChange"
            />
          </div>

          <!-- Max rounds -->
          <div class="section">
            <label class="form-label">消息轮数上限: {{ maxRoundsDisplay }}</label>
            <input
              type="range"
              class="slider"
              min="0"
              max="30"
              step="1"
              v-model.number="maxRounds"
              @input="onMaxRoundsChange"
            />
          </div>

          <!-- Opacity -->
          <div class="section">
            <label class="form-label">背景透明度: {{ opacity.toFixed(2) }}</label>
            <input
              type="range"
              class="slider"
              min="0"
              max="1"
              step="0.01"
              v-model.number="opacity"
              @input="onOpacityChange"
            />
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import {
  uploadAvatar, deleteAvatar,
  uploadBackgroundMulti, deleteBackgroundMulti,
  updateProfile, getBackgroundUrlById,
} from '../api'

const MAX_ROUNDS_DEFAULT = 10

const emit = defineEmits(['close'])
const authStore = useAuthStore()

const avatarInput = ref(null)
const bgInput = ref(null)
const avatarPreview = ref(authStore.avatarUrl)
const backgrounds = ref([...authStore.backgrounds])
const opacity = ref(authStore.backgroundOpacity)
const interval = ref(authStore.carouselInterval)
const maxRounds = ref(authStore.userProfile?.max_rounds ?? MAX_ROUNDS_DEFAULT)

const maxRoundsDisplay = computed(() => {
  if (maxRounds.value === 0) return '无限制'
  return `${maxRounds.value}轮`
})

let intervalSaveTimer = null
let opacitySaveTimer = null
let maxRoundsSaveTimer = null

function bgThumbStyle(bg) {
  const hash = bg.image_path ? bg.image_path.split('/').pop().split('.')[0] : bg.id
  const url = getBackgroundUrlById(bg.id, authStore.accessToken, hash)
  return {
    backgroundImage: `url(${url})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
  }
}

async function onAvatarSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await uploadAvatar(formData)
    const profile = res.data.data
    authStore.updateProfileInStore(profile)
    avatarPreview.value = authStore.avatarUrl
  } catch {
    // error handled by interceptor
  }
}

async function removeAvatar() {
  try {
    const res = await deleteAvatar()
    const profile = res.data.data
    authStore.updateProfileInStore(profile)
    avatarPreview.value = null
  } catch {
    // error handled by interceptor
  }
}

async function onBgUpload(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    await uploadBackgroundMulti(formData)
    await authStore.fetchBackgrounds()
    backgrounds.value = [...authStore.backgrounds]
  } catch {
    // error handled by interceptor
  }
  // Reset input so same file can be re-selected
  e.target.value = ''
}

async function removeBackground(bgId) {
  try {
    await deleteBackgroundMulti(bgId)
    await authStore.fetchBackgrounds()
    backgrounds.value = [...authStore.backgrounds]
  } catch {
    // error handled by interceptor
  }
}

function onIntervalChange() {
  clearTimeout(intervalSaveTimer)
  intervalSaveTimer = setTimeout(async () => {
    try {
      const res = await updateProfile({ carousel_interval: interval.value })
      authStore.updateProfileInStore(res.data.data)
    } catch {
      // error handled by interceptor
    }
  }, 300)
}

function onOpacityChange() {
  clearTimeout(opacitySaveTimer)
  opacitySaveTimer = setTimeout(async () => {
    try {
      const res = await updateProfile({ background_opacity: opacity.value })
      authStore.updateProfileInStore(res.data.data)
    } catch {
      // error handled by interceptor
    }
  }, 300)
}

function onMaxRoundsChange() {
  clearTimeout(maxRoundsSaveTimer)
  maxRoundsSaveTimer = setTimeout(async () => {
    try {
      const res = await updateProfile({ max_rounds: maxRounds.value })
      authStore.updateProfileInStore(res.data.data)
    } catch {
      // error handled by interceptor
    }
  }, 300)
}

onUnmounted(() => {
  clearTimeout(intervalSaveTimer)
  clearTimeout(opacitySaveTimer)
  clearTimeout(maxRoundsSaveTimer)
})
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 1rem;
}

.modal-content {
  background: var(--bg-card);
  border-radius: var(--radius);
  box-shadow: var(--elevation-5);
  width: 100%;
  max-width: 28rem;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1rem 1.25rem;
  border-bottom: 1px solid var(--border);
}

.modal-header h3 {
  font-size: 1rem;
  font-weight: 600;
}

.modal-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: 0.25rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.modal-close svg {
  width: 1.25rem;
  height: 1.25rem;
}

.modal-body {
  padding: 1.25rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.section {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.8125rem;
  font-weight: 600;
  color: var(--text);
}

.hidden-input {
  display: none;
}

/* Avatar */
.avatar-area {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.avatar-preview {
  width: 5rem;
  height: 5rem;
  border-radius: 50%;
  border: 2px solid var(--border);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg);
  flex-shrink: 0;
}

.avatar-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.avatar-preview svg {
  width: 2.5rem;
  height: 2.5rem;
  color: var(--text-secondary);
}

.avatar-actions {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

/* Background grid */
.bg-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(5rem, 1fr));
  gap: 0.5rem;
}

.bg-thumb {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: var(--radius);
  overflow: hidden;
  border: 1px solid var(--border);
}

.bg-thumb-img {
  width: 100%;
  height: 100%;
}

.bg-thumb-delete {
  position: absolute;
  top: 0.25rem;
  right: 0.25rem;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background: rgba(0, 0, 0, 0.6);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.15s;
}

.bg-thumb:hover .bg-thumb-delete {
  opacity: 1;
}

.bg-thumb-delete svg {
  width: 0.75rem;
  height: 0.75rem;
  color: white;
}

.bg-add {
  width: 100%;
  aspect-ratio: 16 / 10;
  border-radius: var(--radius);
  border: 2px dashed var(--border);
  background: transparent;
  cursor: pointer;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.25rem;
  color: var(--text-secondary);
  font-size: 0.75rem;
  transition: border-color var(--transition-fast), color var(--transition-fast);
}

.bg-add:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.bg-add svg {
  width: 1.25rem;
  height: 1.25rem;
}

.bg-empty {
  font-size: 0.8125rem;
  color: var(--text-secondary);
  margin: 0;
}

/* Sliders */
.slider {
  width: 100%;
  height: 0.375rem;
  appearance: none;
  -webkit-appearance: none;
  background: var(--border);
  border-radius: 9999px;
  outline: none;
  cursor: pointer;
}

.slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
}

.slider::-moz-range-thumb {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: var(--primary);
  border: none;
  cursor: pointer;
}
</style>
