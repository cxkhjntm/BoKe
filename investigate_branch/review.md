# Design Review: Avatar Display Fix

**Date:** 2026-05-03
**Reviewer:** team-lead
**Verdict:** APPROVE (Proposal A)

---

## 1. Diagnosis Verification

Verified against source code:

- `backend/middleware/auth.py:34-39` — `get_current_user` raises 401 on missing credentials. CONFIRMED.
- `backend/routers/files.py:137,165` — `Depends(get_current_user)` blocks before `_resolve_user` runs. CONFIRMED.
- `frontend/src/stores/auth.js:14,19` — Token correctly passed as query param. CONFIRMED.
- `_resolve_user` at `files.py:36-47` — Correctly handles None current_user with token fallback. CONFIRMED.

Root cause is accurate and well-evidenced.

---

## 2. Fix Proposal Review

### Proposal A (RECOMMENDED) — `get_current_user_optional`

**Security:** PASS
- `get_current_user` untouched — no existing endpoint weakened
- New dependency delegates to same `_authenticate_jwt` / `_authenticate_api_key` functions
- `_resolve_user` still raises 401 if both auth methods fail
- Token-in-query-param is an accepted tradeoff (already the established pattern)

**Correctness:** PASS
- FastAPI dependency injection will call `get_current_user_optional` → returns None when no header
- `_resolve_user` receives None → falls back to query-param token → authenticates
- Existing endpoints keep strict auth via `get_current_user`

**Rollback:** PASS
- Revert 1 commit; no DB migration, no config change

**Resource Assessment:** Reasonable
- CPU/Memory/Storage: zero impact (same logic path)
- Dev time: ~15 min (accurate)
- Risk: Very Low (accurate)

### Proposal B — REJECTED (agree)
Changing core dependency contract is too risky. Any missed caller becomes unauthenticated.

### Proposal C — REJECTED (agree)
Unnecessary code duplication. `HTTPBearer` already handles header extraction.

---

## 3. Issues Found

None. The fix is minimal, safe, and correct.

---

## 4. Conditions

None. Ready for implementation.
