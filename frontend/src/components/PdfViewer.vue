<template>
  <div class="pdf-viewer-container" ref="containerRef">
    <div v-if="loading" class="pdf-loading">
      <span class="spinner"></span> 正在加载 PDF ...
    </div>
    
    <div v-if="error" class="pdf-error">
      {{ error }}
    </div>

    <div class="pdf-controls" v-if="pdfDoc">
      <button class="btn btn-sm" @click="prevPage" :disabled="pageNum <= 1">上一页</button>
      <span class="page-info">{{ pageNum }} / {{ numPages }}</span>
      <button class="btn btn-sm" @click="nextPage" :disabled="pageNum >= numPages">下一页</button>
      
      <span class="spacer"></span>
      
      <button class="btn btn-sm" @click="zoomOut" :disabled="scale <= 0.5">-</button>
      <span class="zoom-info">{{ Math.round(scale * 100) }}%</span>
      <button class="btn btn-sm" @click="zoomIn" :disabled="scale >= 3.0">+</button>
    </div>

    <div class="canvas-wrapper" v-show="!loading && !error">
      <canvas ref="canvasRef"></canvas>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, shallowRef } from 'vue'
import * as pdfjsLib from 'pdfjs-dist'

export const props = defineProps({
  url: {
    type: String,
    required: true
  }
})

// Configure worker
pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.js',
  import.meta.url
).toString()

const containerRef = ref(null)
const canvasRef = ref(null)

const loading = ref(false)
const error = ref(null)

// Use shallowRef for the PDF document to prevent Vue taking performance hit on making it reactive
const pdfDoc = shallowRef(null)
const pageNum = ref(1)
const numPages = ref(0)
const scale = ref(1.0)
let renderTask = null

async function loadPDF() {
  if (!props.url) return
  
  loading.value = true
  error.value = null
  pageNum.value = 1
  
  try {
    const loadingTask = pdfjsLib.getDocument({
      url: props.url,
      withCredentials: true // Depending on whether cookies are needed
    })
    
    const pdf = await loadingTask.promise
    pdfDoc.value = pdf
    numPages.value = pdf.numPages
    
    // Auto scale to fit width if on mobile
    if (window.innerWidth <= 768) {
       scale.value = (containerRef.value?.clientWidth - 20) / 600 || 0.8
    } else {
       scale.value = 1.2
    }
    
    await renderPage(pageNum.value)
  } catch (err) {
    error.value = '加载 PDF 失败: ' + err.message
    console.error('Error loading PDF:', err)
  } finally {
    loading.value = false
  }
}

async function renderPage(num) {
  if (!pdfDoc.value || !canvasRef.value) return
  
  try {
    const page = await pdfDoc.value.getPage(num)
    const viewport = page.getViewport({ scale: scale.value })
    
    const canvas = canvasRef.value
    const ctx = canvas.getContext('2d')
    
    // Support HiDPI-displays
    const outputScale = window.devicePixelRatio || 1;
    canvas.width = Math.floor(viewport.width * outputScale)
    canvas.height = Math.floor(viewport.height * outputScale)
    canvas.style.width = Math.floor(viewport.width) + 'px'
    canvas.style.height = Math.floor(viewport.height) + 'px'
    
    const transform = outputScale !== 1 ? [outputScale, 0, 0, outputScale, 0, 0] : null
    
    const renderContext = {
      canvasContext: ctx,
      transform,
      viewport: viewport
    }
    
    if (renderTask) {
        // We're already rendering, cancel it if possible
        try { renderTask.cancel() } catch(e){}
    }
    
    renderTask = page.render(renderContext)
    await renderTask.promise
    renderTask = null
  } catch (err) {
    if (err.name === 'RenderingCancelledException') return // Ignored
    console.error('Page render error', err)
  }
}

function prevPage() {
  if (pageNum.value <= 1) return
  pageNum.value--
  renderPage(pageNum.value)
}

function nextPage() {
  if (pageNum.value >= numPages.value) return
  pageNum.value++
  renderPage(pageNum.value)
}

function zoomIn() {
  scale.value = Math.min(3.0, scale.value + 0.2)
  renderPage(pageNum.value)
}

function zoomOut() {
  scale.value = Math.max(0.5, scale.value - 0.2)
  renderPage(pageNum.value)
}

watch(() => props.url, loadPDF)

onMounted(() => {
  loadPDF()
})

onUnmounted(() => {
  if (renderTask) try { renderTask.cancel() } catch(e) {}
  if (pdfDoc.value) pdfDoc.value.destroy()
})
</script>

<style scoped>
.pdf-viewer-container {
  display: flex;
  flex-direction: column;
  width: 100%;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}

.pdf-controls {
  display: flex;
  align-items: center;
  padding: 0.5rem 1rem;
  background: var(--bg-color);
  border-bottom: 1px solid var(--border);
  gap: 0.5rem;
}

.spacer {
  flex-grow: 1;
}

.page-info, .zoom-info {
  font-size: 0.9rem;
  color: var(--text-color);
  min-width: 4rem;
  text-align: center;
}

.canvas-wrapper {
  overflow: auto;
  flex-grow: 1;
  display: flex;
  justify-content: center;
  background: #f0f0f0; /* Default light gray behind canvas */
  padding: 1rem;
  min-height: 50vh;
}

canvas {
  box-shadow: 0 4px 12px rgba(0,0,0,0.1);
  background: white;
}

.pdf-loading, .pdf-error {
  padding: 2rem;
  text-align: center;
  color: var(--text-muted);
}
.pdf-error {
  color: var(--status-error-text);
}

@media (max-width: 768px) {
  .pdf-controls {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>