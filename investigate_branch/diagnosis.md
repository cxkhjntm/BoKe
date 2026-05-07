# Diagnosis Report — API Config & Chat 405 Issues

**Branch:** `investigate/api-config-chat-405`
**Date:** 2026-05-07
**Diagnostician:** team-lead (diagnostician role)

---

## Issue 1: 硅基流动 / DeepSeek 应有固定 Base URL，不应强制用户填写

### Trigger Condition
用户进入聊天界面 → 展开 `ChatConfigPanel` → 选择 Provider（siliconflow / deepseek）→ 必须手动填写 `Base URL` 才能保存。

### Call Chain
1. `frontend/src/components/chat/ChatConfigPanel.vue:61` — `form.base_url` 初始化为空字符串 `''`
2. `frontend/src/stores/chat.js:124-131` — `saveConfig(cfg)` 直接透传表单数据
3. `frontend/src/api/index.js:243` — `api.post('/llm-config', data)`
4. `backend/routers/llm_config.py:45-69` — `upsert_llm_config` 接收 `LLMConfigCreate`
5. `backend/schemas/llm_config.py:28-39` — `LLMConfigCreate.base_url` 是必填字段，且经过 `_is_allowed_url` 校验

### Root Cause
后端 Schema 将 `base_url` 设为必填（`str` 无默认值），且前端未根据 `provider` 自动填充默认值。用户必须知道并手动输入：
- SiliconFlow: `https://api.siliconflow.cn/v1`
- DeepSeek: `https://api.deepseek.com/v1`

### Key Evidence
```python
# backend/schemas/llm_config.py:28-39
class LLMConfigCreate(BaseModel):
    provider: str
    api_key: str = Field(..., min_length=10)
    base_url: str   # <-- 必填，无默认值
    model: str = Field(..., min_length=1)
```

```vue
<!-- frontend/src/components/chat/ChatConfigPanel.vue:60-65 -->
const form = ref({
  provider: 'siliconflow',
  api_key: '',
  base_url: '',   # <-- 空字符串，未根据 provider 自动填充
  model: '',
})
```

---

## Issue 2: 保存 API Key 时按钮一直显示"保存中…"，无法完成配置

### Trigger Condition
用户在 `ChatConfigPanel` 中填写信息并点击"保存"→ 按钮永久禁用，状态无法恢复，页面刷新后配置丢失。

### Call Chain
1. `ChatConfigPanel.vue:80-95` — `handleSave()` 设置 `saving.value = true`，然后 `emit('save', data, callback)`
2. `Chat.vue:56-63` — `handleSaveConfig(cfg)` **只接收一个参数**，完全不调用回调函数
3. `ChatConfigPanel.vue` 的 `saving` ref 因此**永远为 `true`**，按钮保持 disabled

### Root Cause (Layer A — UI State Bug)
父组件 `Chat.vue` 与子组件 `ChatConfigPanel.vue` 之间的状态同步契约断裂：
- 子组件通过 `emit('save', data, callback)` 期望父组件在异步完成后调用 `callback()` 来重置内部 `saving` 状态
- 父组件 `handleSaveConfig(cfg)` 签名只有 `(cfg)`，忽略了 callback
- 此外，父组件向子组件传入了 `:saving="savingConfig"` prop，但子组件**未声明该 prop**（props 中只有 `config`），因此 Vue 将其放入 `$attrs`，而模板中直接使用的 `saving` 解析的是子组件内部 ref，prop 机制完全失效

### Key Evidence
```vue
<!-- Chat.vue:15 -->
<ChatConfigPanel
  :config="chatStore.config"
  :saving="savingConfig"   <!-- prop 传入，但子组件未声明 -->
  @save="handleSaveConfig"
/>
```

```vue
<!-- ChatConfigPanel.vue:52-55 -->
const props = defineProps({
  config: { type: Object, default: null },
  // saving 未声明！
})
```

```vue
<!-- ChatConfigPanel.vue:80-95 -->
function handleSave() {
  saving.value = true
  emit('save', { ...form.value }, () => {
    saving.value = false   # <-- 永远不会执行
    expanded.value = false
  })
}
```

```vue
<!-- Chat.vue:56-63 -->
async function handleSaveConfig(cfg) {
  savingConfig.value = true
  try {
    await chatStore.saveConfig(cfg)
  } finally {
    savingConfig.value = false
  }
}
```

### Root Cause (Layer B — Backend 405)
即使前端状态管理修复，请求本身也会因 **405 Method Not Allowed** 失败（见 Issue 3），导致 `chatStore.saveConfig` 抛出异常，配置无法真正保存。

---

## Issue 3: AI 聊天界面 "Request failed with status code 405"

### Trigger Condition
用户在聊天界面点击"保存"配置，或在某些边界情况下发送消息，收到 405 错误。

### Call Chain
1. 前端 axios / fetch 发送 POST 到 `/api/v1/llm-config`（**无尾部斜杠**）
2. Starlette 路由匹配器遍历已注册路由
3. 路由表末尾的 SPA fallback `@app.get("/{path:path}")` 匹配了路径 `api/v1/llm-config`，但**只接受 GET**
4. Starlette 记录"路径匹配、方法不匹配"，且由于已有路径匹配，**不再触发自动斜杠重定向**（`redirect_slashes` 逻辑被抑制）
5. 最终返回 **405 Method Not Allowed**（`Allow: GET`）

### Root Cause
FastAPI 的 `llm_config` router 与 `chat_sessions` router 在定义时使用了 `path="/"`，与 prefix 拼接后产生**尾部斜杠**：
- `/api/v1/llm-config/`
- `/api/v1/chat-sessions/`

而前端 axios 请求的是**无斜杠版本**：
- `/api/v1/llm-config`
- `/api/v1/chat-sessions`

正常情况下 Starlette 的 `redirect_slashes` 会自动 307 重定向到带斜杠 URL。**但 `/{path:path}` catch-all 路由的存在彻底破坏了这一机制**：因为 `/api/v1/llm-config` 可以匹配 `/{path:path}`（`path="api/v1/llm-config"`），Starlette 认为路径存在、只是方法不对，于是返回 405 而非 307 重定向。

### Key Evidence
```
FastAPI Route Table (extracted via app.routes):
{'GET'}  -> /api/v1/llm-config/
{'POST'} -> /api/v1/llm-config/
{'GET'}  -> /api/v1/chat-sessions/
{'POST'} -> /api/v1/chat-sessions/
{'GET'}  -> /{path:path}          <-- SPA fallback, GET only
```

Local reproduction via TestClient:
```python
client.post('/api/v1/llm-config')         # => 405  (Allow: GET)
client.post('/api/v1/llm-config/')        # => 401  (auth required, route exists)
client.post('/api/v1/chat/messages/')     # => 405  (Allow: GET)
```

```python
# backend/main.py:194-205  -- the catch-all that breaks redirects
@app.get("/{path:path}")
async def serve_spa(path: str):
    ...
```

```python
# backend/routers/llm_config.py:34-45  -- trailing slash routes
@router.get("/")
@router.post("/")
def upsert_llm_config(...)
```

```javascript
// frontend/src/api/index.js:242-244  -- no trailing slash
export const getLLMConfig = () => api.get('/llm-config')
export const saveLLMConfig = (data) => api.post('/llm-config', data)
export const deleteLLMConfig = () => api.delete('/llm-config')
```

---

## Cross-Issue Impact Map

| Issue | Affects | Severity |
|-------|---------|----------|
| Issue 1 (no default base_url) | Issue 2 (user leaves field empty → 422) | Medium |
| Issue 3 (405 on llm-config) | Issue 2 (save request fails → UI stuck) | **Critical** |
| Issue 2 (UI state bug) | Issue 3 (user perceives "saving forever" even after 405) | **Critical** |
| Issue 3 (405 on chat-sessions) | Chat session creation if URL mis-constructed | Low |

---

## Hypotheses Verified / Ruled Out

1. **Hypothesis: CORS preflight OPTIONS causing 405**
   - Ruled out. `main.py` explicitly includes `OPTIONS` in `allow_methods`, and `CORSMiddleware` handles preflight before routing.

2. **Hypothesis: Nginx stripping method on redirect**
   - Ruled out. Reproduced 405 **directly via TestClient** against raw FastAPI app, bypassing nginx entirely.

3. **Hypothesis: Rate limiting returning 405**
   - Ruled out. `RateLimitMiddleware` only returns 429; it does not alter HTTP method semantics.

4. **Hypothesis: Frontend sends wrong HTTP method**
   - Ruled out. `api.post('/llm-config', data)` and `fetch(..., {method: 'POST'})` are correct. TestClient confirmed the same 405 with explicit POST.

---

## Conclusion

Three issues share two underlying root causes:

1. **Missing default base URL mapping** in backend schema + frontend form initialization (Issue 1)
2. **Trailing-slash mismatch + catch-all route interaction** causing 405 (Issue 3)
3. **Broken parent-child state synchronization** in Vue component (Issue 2)

Fixing all three requires coordinated changes in:
- `backend/schemas/llm_config.py` — make `base_url` optional with provider defaults
- `backend/routers/llm_config.py` — remove trailing slash from route paths
- `backend/routers/chat_sessions.py` — remove trailing slash from route paths (preventive)
- `frontend/src/components/chat/ChatConfigPanel.vue` — declare `saving` prop, auto-fill base_url by provider
- `frontend/src/api/index.js` — ensure URL consistency (will naturally align once backend slashes removed)
