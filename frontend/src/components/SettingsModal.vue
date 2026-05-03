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

          <div class="section">
            <label class="form-label">背景图片</label>
            <div class="bg-area">
              <div class="bg-preview" :style="bgPreviewStyle">
                <span v-if="!bgPreview" class="bg-placeholder">无背景图</span>
              </div>
              <div class="bg-actions">
                <button class="btn btn-sm" @click="bgInput.click()">上传背景</button>
                <button v-if="authStore.userProfile?.background_path" class="btn btn-sm btn-danger" @click="removeBackground">移除</button>
              </div>
              <input ref="bgInput" type="file" accept="image/*" class="hidden-input" @change="onBgSelect" />
            </div>

            <div class="opacity-section">
              <label class="form-label">背景透明度: {{ opacity.toFixed(2) }}</label>
              <input type="range" class="opacity-slider" min="0" max="1" step="0.01" v-model.number="opacity" @input="onOpacityChange" />
            </div>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { uploadAvatar, deleteAvatar, uploadBackground, deleteBackground, updateProfile } from '../api'

const emit = defineEmits(['close'])
const authStore = useAuthStore()

const avatarInput = ref(null)
const bgInput = ref(null)
const avatarPreview = ref(authStore.avatarUrl)
const bgPreview = ref(authStore.backgroundUrl)
const opacity = ref(authStore.backgroundOpacity)

let opacityTimer = null

const bgPreviewStyle = computed(() => {
  if (!bgPreview.value) return {}
  return {
    backgroundImage: `url(${bgPreview.value})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
  }
})

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

async function onBgSelect(e) {
  const file = e.target.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('file', file)
  try {
    const res = await uploadBackground(formData)
    const profile = res.data.data
    authStore.updateProfileInStore(profile)
    bgPreview.value = authStore.backgroundUrl
  } catch {
    // error handled by interceptor
  }
}

async function removeBackground() {
  try {
    const res = await deleteBackground()
    const profile = res.data.data
    authStore.updateProfileInStore(profile)
    bgPreview.value = null
  } catch {
    // error handled by interceptor
  }
}

function onOpacityChange() {
  clearTimeout(opacityTimer)
  opacityTimer = setTimeout(async () => {
    try {
      const res = await updateProfile({ background_opacity: opacity.value })
      authStore.updateProfileInStore(res.data.data)
    } catch {
      // error handled by interceptor
    }
  }, 300)
}

onUnmounted(() => clearTimeout(opacityTimer))
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

.hidden-input {
  display: none;
}

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

.bg-area {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.bg-preview {
  width: 100%;
  height: 6rem;
  border-radius: var(--radius);
  border: 1px solid var(--border);
  background: var(--bg);
  display: flex;
  align-items: center;
  justify-content: center;
}

.bg-placeholder {
  font-size: 0.8125rem;
  color: var(--text-secondary);
}

.bg-actions {
  display: flex;
  gap: 0.5rem;
}

.opacity-section {
  margin-top: 0.5rem;
}

.opacity-slider {
  width: 100%;
  height: 0.375rem;
  appearance: none;
  -webkit-appearance: none;
  background: var(--border);
  border-radius: 9999px;
  outline: none;
  cursor: pointer;
}

.opacity-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: var(--primary);
  cursor: pointer;
}

.opacity-slider::-moz-range-thumb {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
  background: var(--primary);
  border: none;
  cursor: pointer;
}
</style>
