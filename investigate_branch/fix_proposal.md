# Fix Proposal — API Config & Chat 405 Issues

**Branch:** `feature/stage4-polish` (investigation tracked here)  
**Date:** 2026-05-07  
**Status:** PROPOSED → RECOMMENDED  

---

## 1. Issue Summary & Root Cause Recap

| Issue | Root Cause | Primary Evidence |
|-------|-----------|------------------|
| **Issue 1** — No default base URL | `LLMConfigCreate.base_url` is mandatory; frontend form initializes empty | `backend/schemas/llm_config.py:31`, `ChatConfigPanel.vue:63` |
| **Issue 2** — Save button stuck | Child emits callback ignored by parent; `saving` prop undeclared; underlying 405 | `ChatConfigPanel.vue:91`, `Chat.vue:56`, `ChatConfigPanel.vue:52` |
| **Issue 3** — 405 on save/chat | Router paths use trailing `/` + catch-all `/{path:path}` suppresses `redirect_slashes` | TestClient: `POST /llm-config` → 405; `POST /llm-config/` → 401 |

---

## 2. Fix Design

### 2.1 Default Base URL Mapping (Issue 1)

**Approach:** Make `base_url` optional in the Pydantic schema. If omitted or empty, resolve from a provider→URL lookup table in `backend/config.py`. Update `LLMConfigCreate` validator to allow empty strings and fallback.

**Files:**
- `backend/config.py` — add `LLM_PROVIDER_DEFAULTS` dict
- `backend/schemas/llm_config.py` — make `base_url` optional (`str | None = None`), adjust validator
- `backend/routers/llm_config.py` — if `body.base_url` is empty/None, use default from config
- `frontend/src/components/chat/ChatConfigPanel.vue` — auto-fill `base_url` when `provider` changes; allow empty input to mean "use default"

### 2.2 Remove Trailing Slashes from Routers (Issue 3)

**Approach:** Change `path="/"` to `path=""` in `llm_config` and `chat_sessions` routers. This aligns backend routes with frontend axios URLs and eliminates the 405 caused by catch-all interference.

**Files:**
- `backend/routers/llm_config.py` — `@router.get("")`, `@router.post("")`, `@router.delete("")`
- `backend/routers/chat_sessions.py` — same pattern for all four decorators
- No frontend changes required; axios URLs already omit the slash.

### 2.3 Fix Saving State Synchronization (Issue 2)

**Approach:** Two coordinated frontend fixes:

**A) Prop-based saving state**
- Declare `saving` as a prop in `ChatConfigPanel.vue`
- Remove internal `saving` ref
- Template uses prop `saving` directly (`:disabled="saving"`)
- Parent `Chat.vue` already manages `savingConfig` and passes it down; this makes the mechanism actually work

**B) Error handling in save flow**
- `chatStore.saveConfig` already throws on failure
- `Chat.vue` `handleSaveConfig` already has `try/finally` to reset `savingConfig`
- With prop-based state, this naturally propagates to the child

**Files:**
- `frontend/src/components/chat/ChatConfigPanel.vue`

---

## 3. Alternative Approaches Considered

| Approach | Pros | Cons | Verdict |
|----------|------|------|---------|
| **A. Frontend-only** (auto-fill base_url + fix UI) | No backend changes | Does not fix 405; user can still manually clear URL and hit 422/405 | **Rejected** |
| **B. Backend-only** (slash fix + default URL) | Fixes core issues | UI still stuck if network slow or error; poor UX | **Rejected** |
| **C. Coordinated** (backend slash+default + frontend prop+autofill) | Fixes all three issues; minimal code; no breaking changes | Requires touching 5 files | **RECOMMENDED** |
| **D. Remove catch-all SPA fallback** | Eliminates 405 root cause entirely | Breaks Vue SPA client-side routing; high risk | **Rejected** |

---

## 4. Resource Impact Assessment

| Dimension | Before | After | Delta |
|-----------|--------|-------|-------|
| **CPU** | Baseline | Baseline | **0** — no computational change |
| **Memory (runtime)** | Baseline | Baseline | **0** — no new allocations |
| **Memory (DB row)** | `base_url` stored as user input | Same | **0** — still stores one string |
| **Storage (code)** | — | ~+30 lines across 5 files | **Negligible** |
| **Dev time** | — | ~30 min | — |
| **Test time** | — | ~15 min (backend schema + route tests) | — |
| **Deploy risk** | — | **Low** — no DB migration, no auth change, no API envelope change | — |
| **Rollback difficulty** | — | **Easy** — single `git revert` of the apply commit | — |

### Risk Mitigation
- No database schema changes; existing `llm_configs` rows remain valid
- No auth middleware changes
- No unified response format changes (`ok()` / `fail()` untouched)
- Route path change from `/` to `""` is backward-compatible for matching; existing clients already call the no-slash URL

---

## 5. Affected Files & Change Details

| File | Change Type | Lines | Description |
|------|-------------|-------|-------------|
| `backend/config.py` | Add | ~5 | `LLM_PROVIDER_DEFAULTS` mapping dict |
| `backend/schemas/llm_config.py` | Modify | ~8 | `base_url` optional; validator allows empty/None |
| `backend/routers/llm_config.py` | Modify | ~4 | Use default URL when `base_url` empty/None; `path=""` |
| `backend/routers/chat_sessions.py` | Modify | ~4 | `path=""` for all routes |
| `frontend/src/components/chat/ChatConfigPanel.vue` | Modify | ~15 | Declare `saving` prop; watch `provider` to auto-fill `base_url`; remove internal `saving` ref |

---

## 6. Verification Plan

1. **TestClient** — `POST /api/v1/llm-config` (no slash) with valid payload → 200/401 (not 405)
2. **TestClient** — `POST /api/v1/chat-sessions` (no slash) → 200/401 (not 405)
3. **Schema test** — `LLMConfigCreate(provider="siliconflow", api_key="sk-test", model="m")` (no base_url) → validates OK
4. **Schema test** — `LLMConfigCreate(..., base_url="")` → falls back to default
5. **Frontend unit** — Switch provider in ChatConfigPanel → base_url auto-populates
6. **E2E** — Click Save in ChatConfigPanel → button state resets on both success and error
