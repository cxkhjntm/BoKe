# Fix Proposal — API Config & Chat 405 Issues

**Branch:** `investigate/api-config-chat-405`  
**Date:** 2026-05-07  
**Based on:** `diagnosis.md` by team-lead (diagnostician)

---

## Executive Summary

Three coordinated issues block the AI chat feature:

1. **Issue 1 — Missing default base_url:** Users must manually enter provider-specific base URLs (SiliconFlow / DeepSeek) because the backend schema makes `base_url` mandatory with no default.
2. **Issue 2 — UI "saving forever" bug:** `ChatConfigPanel.vue` emits a callback that `Chat.vue` ignores, and the `saving` prop is not declared, so the internal `saving` ref stays `true` permanently.
3. **Issue 3 — 405 Method Not Allowed:** FastAPI routers use `path="/"` which, combined with the `prefix`, produces trailing slashes (`/llm-config/`). The SPA fallback `/{path:path}` (GET only) intercepts the no-slash requests and causes Starlette to return 405 instead of redirecting.

All three must be fixed together because they are interdependent (see Cross-Issue Impact Map in diagnosis.md).

---

## Issue 1: 硅基流动 / DeepSeek 应有固定 Base URL

### Recommended Fix: Backend schema default + frontend auto-fill (Dual-layer)

**Rationale:** Making the backend robust (provider-aware defaults) prevents 422 errors even if future frontends forget to pre-fill. Adding frontend auto-fill improves UX by showing the user what URL will be used.

#### Option A — Backend-only default (Chosen as primary)

Change `backend/schemas/llm_config.py` so `base_url` is optional. If omitted or empty, derive it from `provider` using a hard-coded mapping.

```python
# backend/schemas/llm_config.py
from pydantic import BaseModel, Field, model_validator

PROVIDER_DEFAULT_BASE_URL = {
    "siliconflow": "https://api.siliconflow.cn/v1",
    "deepseek": "https://api.deepseek.com/v1",
}

class LLMConfigCreate(BaseModel):
    provider: str
    api_key: str = Field(..., min_length=10)
    base_url: str = ""   # optional, default empty
    model: str = Field(..., min_length=1)

    @model_validator(mode="after")
    def fill_base_url(self):
        if not self.base_url or not self.base_url.strip():
            default = PROVIDER_DEFAULT_BASE_URL.get(self.provider)
            if default:
                self.base_url = default
            else:
                raise ValueError(f"Unknown provider '{self.provider}'; base_url is required")
        return self
```

**Why this option:**
- Keeps the API contract simple (clients can omit `base_url` entirely).
- No database migration needed — the field already exists; we only change validation.
- Rollback-safe: reverting the schema file restores the old behavior without data loss.

#### Option B — Frontend-only auto-fill (Rejected)

Pre-fill `form.base_url` in `ChatConfigPanel.vue` when `provider` changes.

**Why rejected:** If a different client (mobile app, admin CLI) calls the API without pre-filling, it still gets 422. The fix belongs at the schema layer.

#### Option C — Both backend default + frontend auto-fill (Recommended enhancement)

Apply Option A in the backend **and** add a `watch` on `form.provider` in `ChatConfigPanel.vue` to pre-fill the input for better UX. The backend remains the source of truth.

**Specific file changes:**
- `backend/schemas/llm_config.py` — add `PROVIDER_DEFAULT_BASE_URL`, make `base_url` default to `""`, add `@model_validator`
- `frontend/src/components/chat/ChatConfigPanel.vue` — add `watch(() => form.provider, ...)` to pre-fill when user switches providers and field is empty

---

## Issue 2: 保存 API Key 时按钮一直显示"保存中…"

### Recommended Fix: Align parent-child contract via declared prop + callback (Option A)

**Rationale:** The root cause has two layers: (A) the `saving` prop is not declared so it falls through to `$attrs` and is ignored, and (B) the callback emitted by the child is never invoked by the parent. Fixing both layers makes the component contract explicit and robust.

#### Option A — Declare `saving` prop + make parent call callback (Chosen)

1. In `ChatConfigPanel.vue`, declare `saving` as a Boolean prop:
   ```vue
   const props = defineProps({
     config: { type: Object, default: null },
     saving: { type: Boolean, default: false },   # <-- add
   })
   ```
   Remove the internal `saving` ref entirely; the template already reads `saving` which will now resolve to the prop.

2. In `Chat.vue`, change `handleSaveConfig` to accept and invoke the callback:
   ```javascript
   async function handleSaveConfig(cfg, done) {
     savingConfig.value = true
     try {
       await chatStore.saveConfig(cfg)
     } finally {
       savingConfig.value = false
       if (typeof done === 'function') done()   # <-- add
     }
   }
   ```

**Why this option:**
- Uses the existing prop-driven pattern already intended by `Chat.vue` (`:saving="savingConfig"`).
- The callback contract (`emit('save', data, done)`) is preserved; no changes to child event emission logic.
- Rollback-safe: reverting both files restores the previous (broken) behavior without side effects.

#### Option B — Remove callback, rely solely on prop (Rejected)

Remove the callback from `emit('save', ...)` and let `Chat.vue` drive `savingConfig` entirely.

**Why rejected:** It requires changing the child's `handleSave` to not set `saving.value = true` locally. This is a larger behavioral change and breaks the existing callback contract that other callers might rely on.

#### Option C — Use `defineExpose` + template ref (Rejected)

Expose a `resetSaving()` method from the child and call it from the parent via template ref.

**Why rejected:** Template refs are brittle in Vue 3 composition API with `v-if`/`v-show` toggles. The prop + callback pattern is the idiomatic Vue parent-child communication pattern.

**Specific file changes:**
- `frontend/src/components/chat/ChatConfigPanel.vue` — add `saving` to `defineProps`, remove internal `saving` ref
- `frontend/src/views/Chat.vue` — invoke `done()` callback in `finally` block of `handleSaveConfig`

---

## Issue 3: AI 聊天界面 "Request failed with status code 405"

### Recommended Fix: Remove trailing slashes from router paths (Option A)

**Rationale:** The 405 is caused by the interaction between trailing-slash routes and the SPA fallback catch-all. The cleanest, lowest-risk fix is to make the backend routes match the frontend URLs exactly (no trailing slash), which is also the convention used by all other routers in the project (`api_keys`, `documents`, `profile`, etc.).

#### Option A — Change `path="/"` to `path=""` in routers (Chosen)

In FastAPI, `APIRouter(prefix="/api/v1/llm-config")` with `@router.get("/")` produces `/api/v1/llm-config/`. Changing the decorator to `@router.get("")` produces `/api/v1/llm-config`.

Apply to:
- `backend/routers/llm_config.py` — change `@router.get("/")`, `@router.post("/")`, `@router.delete("/")` to `path=""`
- `backend/routers/chat_sessions.py` — change `@router.get("/")`, `@router.post("/")` to `path=""`
- `backend/routers/chat.py` — change `@router.get("/")` to `path=""` (preventive, for consistency)

**Why this option:**
- Zero frontend changes required — the frontend already calls `/llm-config` and `/chat-sessions` without slashes.
- Aligns with the existing convention in the codebase: `api_keys.py`, `documents.py`, `profile.py` all use `path=""`.
- Rollback-safe: reverting the router files restores the old paths; no database or config changes.
- No impact on the SPA fallback — the catch-all remains for genuine client-side routes.

#### Option B — Add trailing slashes to all frontend API calls (Rejected)

Change `frontend/src/api/index.js` to use `/llm-config/`, `/chat-sessions/`, etc.

**Why rejected:**
- Requires changing every API call site and risks missing some.
- The existing project convention is no-trailing-slash (all other routers use `path=""`).
- The SPA fallback would still intercept `/llm-config` (no slash) if a request ever comes in without it.

#### Option C — Restrict SPA fallback to exclude `/api/` paths more aggressively (Rejected)

The SPA fallback already skips `path.startswith("api/")`, but Starlette's route matching happens **before** the handler body runs. We could move the catch-all to a mounted sub-application or use a middleware-based fallback.

**Why rejected:**
- Far more invasive than adjusting router paths.
- Could break legitimate SPA client-side routes that happen to look like `/api/...` (unlikely but possible).
- Adds architectural complexity for a problem that has a one-character fix.

**Specific file changes:**
- `backend/routers/llm_config.py` — `@router.get("")`, `@router.post("")`, `@router.delete("")`
- `backend/routers/chat_sessions.py` — `@router.get("")`, `@router.post("")`
- `backend/routers/chat.py` — `@router.get("")` (preventive consistency)

---

## Resource Comparison Table

| Fix | CPU delta | Memory delta | Storage delta | Dev time | Test time | Deploy risk | Rollback difficulty |
|-----|-----------|--------------|---------------|----------|-----------|-------------|---------------------|
| Issue 1 — Backend schema default (Option A) | +0% | +0~1 MB (validator object) | 0 | 15 min | 10 min | Low | Trivial (`git revert`) |
| Issue 1 — Frontend auto-fill (Option C add-on) | +0% | +0 MB | 0 | 10 min | 5 min | Low | Trivial (`git revert`) |
| Issue 2 — Prop + callback fix (Option A) | +0% | +0 MB | 0 | 10 min | 10 min | Low | Trivial (`git revert`) |
| Issue 3 — Remove trailing slashes (Option A) | +0% | +0 MB | 0 | 5 min | 10 min | Low | Trivial (`git revert`) |
| **Combined (all three)** | **+0%** | **+0~1 MB** | **0** | **~40 min** | **~30 min** | **Low** | **Trivial (`git revert` on single commit)** |

**Notes:**
- All fixes are code-only; no migrations, no new dependencies, no infra changes.
- Test time assumes running existing backend pytest + frontend unit tests + manual verification of the save flow.
- Deploy risk is "Low" because each fix is localized and rollback is a single `git revert`.

---

## Specific File Changes Needed

| File | Change | Issue |
|------|--------|-------|
| `backend/schemas/llm_config.py` | Make `base_url` optional with provider defaults via `@model_validator` | 1 |
| `backend/routers/llm_config.py` | Change `@router.get("/")`, `@router.post("/")`, `@router.delete("/")` to `path=""` | 3 |
| `backend/routers/chat_sessions.py` | Change `@router.get("/")`, `@router.post("/")` to `path=""` | 3 |
| `backend/routers/chat.py` | Change `@router.get("/")` to `path=""` (preventive) | 3 |
| `frontend/src/components/chat/ChatConfigPanel.vue` | Declare `saving` prop; remove internal `saving` ref; add `watch` on `provider` to auto-fill `base_url` | 1, 2 |
| `frontend/src/views/Chat.vue` | Invoke `done()` callback in `handleSaveConfig` | 2 |

---

## Rollback Plan

1. All changes are contained in the files listed above.
2. No database migrations, environment variables, or external services are involved.
3. If a regression is detected post-deploy, run `git revert <commit-hash>` to restore the previous state instantly.
4. The SPA fallback and auth middleware are untouched, so the rest of the application remains unaffected.

---

## Testing Plan

1. **Backend unit tests:**
   - Test `LLMConfigCreate` with `provider="siliconflow"`, no `base_url` → expect `base_url == "https://api.siliconflow.cn/v1"`
   - Test `LLMConfigCreate` with `provider="deepseek"`, no `base_url` → expect `base_url == "https://api.deepseek.com/v1"`
   - Test `LLMConfigCreate` with unknown provider, no `base_url` → expect `ValueError`
   - Test `LLMConfigCreate` with explicit `base_url` → expect explicit value preserved

2. **Backend integration tests (TestClient):**
   - `POST /api/v1/llm-config` (no trailing slash) with valid payload → 200
   - `POST /api/v1/chat-sessions` (no trailing slash) with valid payload → 200
   - `GET /api/v1/chat/` (old trailing slash) → should still work or return 307 (verify Starlette behavior)

3. **Frontend manual / E2E:**
   - Open Chat page → expand config panel → select SiliconFlow → observe Base URL auto-filled
   - Clear Base URL → click Save → observe button returns to "保存" state (not stuck)
   - Refresh page → verify config persisted
   - Repeat for DeepSeek provider
