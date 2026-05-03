# Fix Proposal: Profile File Serve Authentication

## Problem Summary

Profile file serve endpoints (`GET /api/v1/files/profile/avatar` and `GET /api/v1/files/profile/background`) fail with 401 when loaded from `<img>` tags or CSS `url()` because:

1. Both endpoints use `Depends(get_current_user)` which throws HTTP 401 when no `Authorization` header is present (`backend/middleware/auth.py:34-39`)
2. Browser `<img>` and CSS `url()` requests cannot include custom headers
3. The frontend correctly passes `?token=...` query param (`frontend/src/stores/auth.js:14,19`), but the dependency throws before the endpoint body runs
4. The `_resolve_user` helper (`backend/routers/files.py:36-47`) with query-param fallback is never reached

## Affected Endpoints

| Endpoint | File | Line |
|----------|------|------|
| `GET /api/v1/files/profile/avatar` | `backend/routers/files.py` | 133 |
| `GET /api/v1/files/profile/background` | `backend/routers/files.py` | 161 |

Other endpoints using the same pattern (`serve_original`, `serve_thumbnail`) also share this issue but are loaded via `<iframe>` or JavaScript `fetch()` which can include headers.

---

## Proposal A: Add `get_current_user_optional` Dependency

### Description

Create a new dependency `get_current_user_optional` that returns `Optional[User]` -- returning `None` instead of raising 401 when no credentials are provided. Use this for profile endpoints. The existing `get_current_user` remains unchanged for all other endpoints.

### Code Changes

**File: `backend/middleware/auth.py`**

Add after `get_current_user` (after line 43):

```python
def get_current_user_optional(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Authenticate via Authorization header, returning None if no credentials provided."""
    if not credentials:
        return None
    token = credentials.credentials
    if token.startswith("sk-"):
        return _authenticate_api_key(token, db, request)
    return _authenticate_jwt(token, db, request)
```

**File: `backend/routers/files.py`**

1. Update import (line 11):
```python
from backend.middleware.auth import get_current_user, get_current_user_optional, authenticate_from_token
```

2. Update `serve_avatar` (line 137):
```python
current_user: Optional[User] = Depends(get_current_user_optional),
```

3. Update `serve_background` (line 165):
```python
current_user: Optional[User] = Depends(get_current_user_optional),
```

No other changes needed -- `_resolve_user` already handles the `None` case correctly.

### Resource Impact

| Resource | Impact |
|----------|--------|
| CPU | None -- same logic, different flow |
| Memory | None |
| Storage | None |
| Dev Time | ~15 min |
| Test Time | ~20 min (unit tests for new dependency + integration tests for endpoints) |
| Deploy Risk | Very Low -- no existing behavior changes |
| Rollback Difficulty | Trivial -- remove the new function and revert imports |

### Security Analysis

- **No weakening of existing auth**: `get_current_user` is untouched; all other endpoints keep strict auth
- **Token validation unchanged**: `authenticate_from_token` still validates JWT expiry, signature, and user status
- **Token in query param**: The frontend already sends tokens in query params. This is the established pattern. Tokens in URLs are logged in server access logs and browser history -- this is an accepted tradeoff for image loading
- **No new attack surface**: The optional dependency delegates to the same `_authenticate_jwt` and `_authenticate_api_key` functions

### Risks

- Low: If a future developer uses `get_current_user_optional` where `get_current_user` is needed, they could forget to check for `None`. This is mitigated by the existing `_resolve_user` pattern which already raises if neither auth method succeeds.

---

## Proposal B: Modify `get_current_user` to Return `Optional[User]`

### Description

Change `get_current_user` to return `Optional[User]` (returning `None` when no credentials) instead of raising 401. All callers must then handle the `None` case. The `_resolve_user` helper already does this.

### Code Changes

**File: `backend/middleware/auth.py`**

Modify `get_current_user` (lines 28-43):

```python
def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> Optional[User]:
    """Authenticate via Authorization header (JWT or API Key). Returns None if no credentials."""
    if not credentials:
        return None
    token = credentials.credentials
    if token.startswith("sk-"):
        return _authenticate_api_key(token, db, request)
    return _authenticate_jwt(token, db, request)
```

**File: `backend/routers/files.py`**

No changes needed -- `_resolve_user` and all endpoint handlers already work correctly.

**Other files using `get_current_user`** (must be audited):

All endpoints that use `Depends(get_current_user)` and expect a non-None user must add their own 401 check. This requires finding and updating every caller:

```bash
grep -rn "Depends(get_current_user)" backend/
```

Each caller needs:
```python
if not current_user:
    raise HTTPException(status_code=401, detail={"code": 4001, "message": "Authentication required"})
```

Or use a pattern like:
```python
user = current_user or _resolve_user(token, current_user, db, request)
```

### Resource Impact

| Resource | Impact |
|----------|--------|
| CPU | None |
| Memory | None |
| Storage | None |
| Dev Time | ~45 min (audit + update all callers) |
| Test Time | ~60 min (re-test all authenticated endpoints) |
| Deploy Risk | Medium -- changes behavior of a core auth dependency |
| Rollback Difficulty | Moderate -- must revert all caller updates |

### Security Analysis

- **Weakens core dependency**: `get_current_user` no longer enforces authentication by default
- **Caller responsibility**: Every endpoint must now handle auth enforcement itself -- easy to miss
- **Regression risk**: If any caller is missed, that endpoint becomes publicly accessible
- **Same token-in-query-param tradeoff** as Proposal A

### Risks

- High: Any missed caller becomes an unauthenticated endpoint. This is the most significant risk. A thorough audit is required, and future endpoints using this dependency must remember to check for `None`.

---

## Proposal C: Manual Auth in Profile Endpoints

### Description

Remove `Depends(get_current_user)` from profile endpoints entirely. Manually extract the token from the `Authorization` header or `token` query param and call `authenticate_from_token` directly.

### Code Changes

**File: `backend/routers/files.py`**

Modify `serve_avatar` (lines 133-158):

```python
@router.get("/profile/avatar")
async def serve_avatar(
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    db: Session = Depends(get_db),
):
    user = _authenticate_from_request(request, token, db)
    # ... rest unchanged
```

Modify `serve_background` (lines 161-186):

```python
@router.get("/profile/background")
async def serve_background(
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    db: Session = Depends(get_db),
):
    user = _authenticate_from_request(request, token, db)
    # ... rest unchanged
```

Add helper function:

```python
def _authenticate_from_request(request: Request, token: Optional[str], db: Session) -> User:
    """Authenticate from Authorization header or query-param token."""
    auth_header = request.headers.get("authorization")
    if auth_header and auth_header.startswith("Bearer "):
        raw_token = auth_header[7:]
        return authenticate_from_token(raw_token, db, request)
    if token:
        return authenticate_from_token(token, db, request)
    raise AppException(code=4001, message="Authentication required", status_code=401)
```

### Resource Impact

| Resource | Impact |
|----------|--------|
| CPU | None |
| Memory | None |
| Storage | None |
| Dev Time | ~20 min |
| Test Time | ~20 min |
| Deploy Risk | Low -- only touches profile endpoints |
| Rollback Difficulty | Trivial -- revert two endpoints |

### Security Analysis

- **No change to existing dependencies**: `get_current_user` untouched
- **Same auth logic**: `authenticate_from_token` performs identical validation
- **Duplicated pattern**: Manual header extraction duplicates what `HTTPBearer` already does
- **Same token-in-query-param tradeoff** as Proposal A

### Risks

- Low: Slight code duplication in extracting the Bearer token from the header. Could diverge from the main auth path if `HTTPBearer` behavior changes.

---

## Recommendation

**Proposal A is the recommended approach.**

Reasons:

1. **Minimal change surface**: Adds one new function, changes two import lines, changes two `Depends()` calls. No existing code behavior changes.
2. **Leverages existing infrastructure**: `_resolve_user` already handles the `None` -> query-param fallback correctly. No new logic needed.
3. **Zero regression risk**: `get_current_user` is untouched. All existing endpoints keep their strict auth.
4. **Clean separation**: "Optional auth" and "required auth" are distinct concerns with distinct dependencies.
5. **Lowest rollback cost**: Three lines changed in `files.py`, one new function in `auth.py`.

Proposal B is too risky because it changes a core dependency's contract and requires auditing/updating every caller. Proposal C works but introduces unnecessary duplication of the Bearer token extraction logic.
