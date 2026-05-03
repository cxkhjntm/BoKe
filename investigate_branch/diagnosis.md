# Diagnosis Report: Avatar & Background Display Bug

**Date:** 2026-05-03
**Branch:** `investigate/avatar-display-401`
**Severity:** HIGH - Core user feature broken

---

## 1. Problem Statement

After uploading avatar and background images via the personal settings page (top-right corner), the avatar displays as a broken image icon and the background does not change.

---

## 2. Root Cause

The profile file **serve endpoints** (`GET /api/v1/files/profile/avatar` and `GET /api/v1/files/profile/background`) return **401 Unauthorized** when accessed via browser `<img>` tags and CSS `background-image: url()`.

### Root Cause Chain

1. **Browser `<img>` and CSS `url()` requests CANNOT include Authorization headers.**
2. The serve endpoints declare `current_user: Optional[User] = Depends(get_current_user)`.
3. `get_current_user` (in `backend/middleware/auth.py:28-39`) **throws HTTPException 401 immediately** when no `Authorization` header is present — it never returns `None`.
4. The `Optional[User]` type hint is misleading; the function returns `User` or raises, never `None`.
5. A `_resolve_user` helper exists with `token` query-param fallback, but **is never reached** because `Depends(get_current_user)` fails first in the dependency injection chain.

---

## 3. Evidence

### 3.1 Backend Auth Dependency (CRITICAL)

**File:** `backend/middleware/auth.py` lines 28-39

```python
def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    db: Session = Depends(get_db),
) -> User:
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": 4001, "message": "Authentication required", "data": None},
        )
```

### 3.2 Serve Endpoints (BROKEN)

**File:** `backend/routers/files.py` lines 133-186

```python
@router.get("/profile/avatar")
async def serve_avatar(
    ...
    current_user: Optional[User] = Depends(get_current_user),  # <-- Fails here
    ...
):
    user = _resolve_user(token, current_user, db, request)  # <-- Never reached
```

### 3.3 Frontend URL Construction (CORRECT)

**File:** `frontend/src/stores/auth.js` lines 12-19

```javascript
const avatarUrl = computed(() => {
    if (!userProfile.value?.avatar_path || !accessToken.value) return null
    return `/api/v1/files/profile/avatar?token=${encodeURIComponent(accessToken.value)}`
})
```

The frontend correctly passes JWT as a `token` query param. The problem is purely backend-side.

### 3.4 Upload Flow (WORKS)

- Frontend uploads via axios with `Authorization` header → backend receives header → `get_current_user` succeeds → file saved to `storage/{user_id}/profile/{uuid}{ext}`
- Upload succeeds, path stored in DB, but display fails on retrieval.

### 3.5 Contrast with Working File Serving

Document files (`/api/v1/files/{doc_id}/original`) work because the frontend fetches them via `fetchFileBlobUrl()` which uses `api.get()` (axios) — the request interceptor adds the `Authorization: Bearer` header. Profile images are loaded directly by the browser (no axios), so no header is attached.

---

## 4. Impact Analysis

| Component | Status |
|-----------|--------|
| Upload (avatar) | WORKING |
| Upload (background) | WORKING |
| Display (avatar) | BROKEN - 401 |
| Display (background) | BROKEN - 401 |
| Document file serving | WORKING (uses axios) |

---

## 5. Verified Facts

- Nginx config correctly proxies `/api/` to backend. Not the issue.
- Vite proxy correctly proxies `/api` to `localhost:8000`. Not the issue.
- No static file mount for storage directory — files are served through authenticated endpoints. This is intentional.
- Database: User 1 has `avatar_path = None`, `background_path = None` (no successful display has occurred).

---

## 6. Recommended Fix Direction

Create a `get_current_user_optional` dependency that returns `Optional[User]` (returns `None` when no credentials, instead of raising 401). Use it for the profile file serve endpoints. This allows the existing `_resolve_user` token query-param fallback to work.

---

## 7. Trigger Conditions

1. User uploads avatar/background via settings modal (works)
2. Browser renders `<img :src="avatarUrl">` or `background-image: url(...)` (no Authorization header)
3. Backend `get_current_user` dependency throws 401
4. Image fails to load → broken icon / no background change
