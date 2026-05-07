# BoKe LLM Chat Feature — Code Review Report

> Date: 2026-05-07
> Branch: `feature/stage4-polish`
> Commit: `a7dd005`

---

## 1. Overview

This review covers the complete LLM Chat feature implementation across four stages:

| Stage | Description | Status |
|-------|-------------|--------|
| Stage 1 | Backend core (models, migrations, SSE chat endpoint, storage, LLM client) | ✅ Complete |
| Stage 2 | Frontend UI (Chat.vue, components, Pinia store, router, API integration) | ✅ Complete |
| Stage 3 | Settings integration (`max_rounds` frontend ↔ backend) | ✅ Complete |
| Stage 4 | Security hardening, tests, DevOps | ✅ Complete |

---

## 2. Architecture

### Service Layer Split
The backend follows a clean separation of concerns:

- **`chat_storage.py`** — File I/O with `filelock`, atomic writes (`.tmp` + `replace`), path traversal protection
- **`chat_service.py`** — Orchestrator: load history → decrypt key → stream LLM → save reply → trim history
- **`llm_client.py`** — Thin async generator over `httpx.AsyncClient.stream()` for OpenAI-compatible APIs

This split makes unit testing straightforward and allows swapping the LLM provider without touching storage logic.

### SSE Streaming
- Uses `sse-starlette` `EventSourceResponse` with explicit event types: `start`, `delta`, `finish`, `error`
- Frontend consumes via native `fetch` + `ReadableStream` (not Axios), avoiding Axios interceptor complexity with streaming

### Frontend State Management
- Pinia store (`stores/chat.js`) centralizes sessions, messages, streaming status, and config
- Computed properties for `isStreaming`, `currentSession`, etc., keep UI reactive without manual event bus

---

## 3. Security Review

### Checks Performed
- [x] No hardcoded secrets
- [x] API key encryption at rest (AES-256-GCM)
- [x] SSRF protection via base_url whitelist
- [x] Rate limiting on chat endpoints (20 req/min per IP)
- [x] Path traversal protection in session storage
- [x] Cross-user access isolation verified by tests
- [x] Input validation on message length

### Findings

| Severity | Item | Status |
|----------|------|--------|
| **HIGH** | `RequestValidationError` handler in `main.py` failed to serialize Pydantic v2 `ValueError` from custom `@field_validator` — fixed by wrapping with `jsonable_encoder` | ✅ Fixed |
| MEDIUM | `api_key` masking in GET response operates on the encrypted ciphertext, not the original plaintext. This is acceptable because the ciphertext is already opaque, but users should understand they are seeing `enc(key)[:8] + "***" + enc(key)[-4:]` | ℹ️ Acknowledged |
| LOW | `chat.py` error handler yields `str(e)` to the client. For production, consider logging the full traceback server-side and sending a generic error message to the client to avoid leaking internal details. | ℹ️ Note |

---

## 4. Test Coverage

### New Tests (49 total)

| Module | Tests | Coverage |
|--------|-------|----------|
| `utils/crypto_utils.py` | 6 | **100%** |
| `services/chat_storage.py` | 12 | **98%** |
| `services/chat_service.py` | — (covered via integration) | **100%** |
| `routers/chat_sessions.py` | 14 | **100%** |
| `routers/llm_config.py` | 12 | **98%** |
| `routers/chat.py` | 5 | **93%** |

### Full Suite Status
```
175 passed, 1 failed (pre-existing)
```
The single failure (`test_delete_queued_document_blocked`) predates this feature and is unrelated.

---

## 5. DevOps

### Nginx
- Added dedicated `/api/v1/chat/messages/` location with:
  - `proxy_buffering off;`
  - `proxy_cache off;`
  - `proxy_read_timeout 300s;`
  - `proxy_send_timeout 300s;`

### Environment Variables
New vars documented in `.env.example`:
- `CHAT_MAX_TIMEOUT=120`
- `CHAT_MAX_MESSAGE_LENGTH=8000`
- `CHAT_RATE_LIMIT_PER_MINUTE=20`

---

## 6. Recommendations

1. **Frontend E2E tests** — Add Playwright tests for the critical chat flow: open chat → create session → send message → verify streamed response appears.
2. **LLM client retries** — `llm_client.py` currently has no retry logic for transient network failures. Consider adding `httpx` retries or a simple backoff wrapper.
3. **Session file cleanup** — If a user is deleted, their `sessions/{user_id}/` directory is not automatically cleaned. A background task or cascade hook could handle this.
4. **Token usage tracking** — For future billing/observability, consider parsing and storing `usage` fields from LLM API responses.
5. **Error message sanitization** — In `chat.py`, replace `str(e)` in the SSE error event with a user-friendly message and log the original exception server-side.

---

## 7. Approval

- **No CRITICAL or HIGH security issues remain.**
- **All new code meets the 80% coverage minimum.**
- **Frontend builds with zero errors.**

**Verdict: APPROVE for merge into `main` (via PR).**
