# Multi-Background Carousel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Allow users to upload multiple background images in personal settings, with automatic carousel rotation at a configurable interval, maintaining transparency (opacity) compatibility.

**Architecture:** New `user_backgrounds` table stores multiple images per user. Existing `background_path` column preserved for backward compatibility with auto-migration of old data. Pure CSS crossfade carousel in `App.vue` using two-layer opacity transitions. User-level `carousel_interval` field on the users table controls rotation speed.

**Tech Stack:** Vue 3 + Vite + Pinia (frontend), FastAPI + SQLAlchemy + SQLite (backend), Alembic (migrations). No new dependencies required.

---

## File Structure

### New Files
- `backend/models/user_background.py` — SQLAlchemy model for `user_backgrounds` table
- `alembic/versions/005_add_user_backgrounds.py` — Migration: create table + migrate old data
- `tests/api/test_backgrounds.py` — Tests for multi-background endpoints

### Modified Files
- `backend/models/__init__.py` — Register `UserBackground` model
- `backend/models/user.py` — Add `carousel_interval` column + relationship
- `backend/schemas/user.py` — Add `BackgroundOut`, extend `ProfileOut`/`ProfileUpdate`
- `backend/routers/profile.py` — Add multi-background CRUD endpoints
- `backend/routers/files.py` — Add `GET /profile/backgrounds/{bg_id}` serving endpoint
- `frontend/src/api/index.js` — Add new API functions for multi-background CRUD
- `frontend/src/stores/auth.js` — Extend with `backgroundUrls[]` and `carouselInterval`
- `frontend/src/App.vue` — Carousel with CSS crossfade
- `frontend/src/components/SettingsModal.vue` — Multi-image upload grid + interval control

---

## Task 1: Database — UserBackground Model

**Files:**
- Create: `backend/models/user_background.py`

- [ ] **Step 1: Create the UserBackground model**

```python
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.database import Base


class UserBackground(Base):
    __tablename__ = "user_backgrounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    image_path = Column(String(500), nullable=False)
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="backgrounds")
```

- [ ] **Step 2: Register model in `backend/models/__init__.py`**

Add import and export:

```python
from backend.models.user_background import UserBackground
```

And add `"UserBackground"` to the `__all__` list.

- [ ] **Step 3: Add relationship and carousel_interval to User model**

In `backend/models/user.py`, add:

```python
from sqlalchemy.orm import relationship
```

And add to the `User` class:

```python
    carousel_interval = Column(Integer, default=5)
    backgrounds = relationship("UserBackground", back_populates="user", cascade="all, delete-orphan", order_by="UserBackground.position")
```

- [ ] **Step 4: Run lsp_diagnostics**

Run `lsp_diagnostics` on both modified model files to verify no type errors.

---

## Task 2: Database — Alembic Migration

**Files:**
- Create: `alembic/versions/005_add_user_backgrounds.py`

- [ ] **Step 1: Write the migration**

```python
"""add user_backgrounds table and carousel_interval

Revision ID: 005
Revises: 004
Create Date: 2026-05-04
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_exists(table: str, column: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text(f"PRAGMA table_info({table})"))
    columns = [row[1] for row in result]
    return column in columns


def _table_exists(table: str) -> bool:
    conn = op.get_bind()
    result = conn.execute(sa.text("SELECT name FROM sqlite_master WHERE type='table' AND name=:name"), {"name": table})
    return result.first() is not None


def upgrade() -> None:
    # Add carousel_interval to users
    if not _column_exists("users", "carousel_interval"):
        op.execute("ALTER TABLE users ADD COLUMN carousel_interval INTEGER DEFAULT 5")

    # Create user_backgrounds table
    if not _table_exists("user_backgrounds"):
        op.create_table(
            "user_backgrounds",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.Integer, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
            sa.Column("image_path", sa.String(500), nullable=False),
            sa.Column("position", sa.Integer, nullable=False, server_default="0"),
            sa.Column("created_at", sa.DateTime, server_default=sa.func.now()),
        )
        op.create_index("ix_user_backgrounds_user_id", "user_backgrounds", ["user_id"])

    # Migrate existing background_path data
    conn = op.get_bind()
    users_with_bg = conn.execute(sa.text("SELECT id, background_path FROM users WHERE background_path IS NOT NULL"))
    for row in users_with_bg:
        user_id, bg_path = row
        # Check if already migrated
        existing = conn.execute(
            sa.text("SELECT id FROM user_backgrounds WHERE user_id=:uid AND image_path=:path"),
            {"uid": user_id, "path": bg_path},
        ).first()
        if not existing:
            conn.execute(
                sa.text("INSERT INTO user_backgrounds (user_id, image_path, position) VALUES (:uid, :path, 0)"),
                {"uid": user_id, "path": bg_path},
            )


def downgrade() -> None:
    op.drop_index("ix_user_backgrounds_user_id", table_name="user_backgrounds")
    op.drop_table("user_backgrounds")
    # Note: we don't drop carousel_interval from users to avoid data loss
```

- [ ] **Step 2: Verify migration syntax**

Run: `python -c "import alembic; print('alembic importable')"` from project root.
Expected: No import errors.

---

## Task 3: Backend — Schema Updates

**Files:**
- Modify: `backend/schemas/user.py`

- [ ] **Step 1: Update schemas**

Replace the entire file content with:

```python
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class BackgroundOut(BaseModel):
    id: int
    image_path: str
    position: int

    model_config = {"from_attributes": True}


class ProfileOut(BaseModel):
    avatar_path: str | None = None
    background_path: str | None = None
    background_opacity: float = 0.3
    carousel_interval: int = 5
    backgrounds: list[BackgroundOut] = []

    model_config = {"from_attributes": True}


class ProfileUpdate(BaseModel):
    background_opacity: float | None = Field(default=None, ge=0.0, le=1.0)
    carousel_interval: int | None = Field(default=None, ge=1, le=300)


class BackgroundReorder(BaseModel):
    background_ids: list[int]
```

- [ ] **Step 2: Run lsp_diagnostics**

Run `lsp_diagnostics` on the schema file.

---

## Task 4: Backend — Profile Router (Multi-Background CRUD)

**Files:**
- Modify: `backend/routers/profile.py`

- [ ] **Step 1: Add imports**

Add at the top of the file, after existing imports:

```python
from backend.models.user_background import UserBackground
from backend.schemas.user import BackgroundOut, BackgroundReorder
from backend.config import IMAGE_MAX_UPLOAD_SIZE_BYTES
```

Note: `IMAGE_MAX_UPLOAD_SIZE_BYTES` is already imported via `IMAGE_MAX_UPLOAD_SIZE_BYTES, IMAGE_ALLOWED_EXTENSIONS` — verify and adjust.

- [ ] **Step 2: Update the PUT /profile endpoint**

Replace the existing `update_profile` function:

```python
@router.put("")
def update_profile(
    body: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if body.background_opacity is not None:
        current_user.background_opacity = body.background_opacity
    if body.carousel_interval is not None:
        current_user.carousel_interval = body.carousel_interval
    db.commit()
    db.refresh(current_user)
    return ok(data=ProfileOut.model_validate(current_user).model_dump())
```

- [ ] **Step 3: Add GET /backgrounds endpoint**

```python
MAX_BACKGROUNDS = 10


@router.get("/backgrounds")
def list_backgrounds(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bgs = db.query(UserBackground).filter(
        UserBackground.user_id == current_user.id
    ).order_by(UserBackground.position).all()
    return ok(data=[BackgroundOut.model_validate(bg).model_dump() for bg in bgs])
```

- [ ] **Step 4: Add POST /backgrounds endpoint (upload)**

```python
@router.post("/backgrounds")
def upload_background_multi(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Check limit
    count = db.query(UserBackground).filter(UserBackground.user_id == current_user.id).count()
    if count >= MAX_BACKGROUNDS:
        raise AppException(code=4000, message=f"Maximum {MAX_BACKGROUNDS} backgrounds allowed", status_code=400)

    content = file.file.read()
    _validate_image(file, content)

    relative_path = file_service.save_file(current_user.id, file.filename, content, "profile")

    bg = UserBackground(
        user_id=current_user.id,
        image_path=relative_path,
        position=count,
    )
    db.add(bg)
    db.commit()
    db.refresh(bg)
    return ok(data=BackgroundOut.model_validate(bg).model_dump())
```

- [ ] **Step 5: Add DELETE /backgrounds/{bg_id} endpoint**

```python
@router.delete("/backgrounds/{bg_id}")
def delete_background_multi(
    bg_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    bg = db.query(UserBackground).filter(
        UserBackground.id == bg_id,
        UserBackground.user_id == current_user.id,
    ).first()
    if not bg:
        raise AppException(code=4004, message="Background not found", status_code=404)

    file_service.delete_file(bg.image_path)
    db.delete(bg)

    # Reorder remaining backgrounds to fill gaps
    remaining = db.query(UserBackground).filter(
        UserBackground.user_id == current_user.id
    ).order_by(UserBackground.position).all()
    for i, item in enumerate(remaining):
        item.position = i

    db.commit()
    return ok(data=None)
```

- [ ] **Step 6: Add PUT /backgrounds/reorder endpoint**

```python
@router.put("/backgrounds/reorder")
def reorder_backgrounds(
    body: BackgroundReorder,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Verify all IDs belong to current user
    bgs = db.query(UserBackground).filter(
        UserBackground.user_id == current_user.id,
        UserBackground.id.in_(body.background_ids),
    ).all()

    if len(bgs) != len(body.background_ids):
        raise AppException(code=4000, message="One or more invalid background IDs", status_code=400)

    bg_map = {bg.id: bg for bg in bgs}
    for pos, bg_id in enumerate(body.background_ids):
        bg_map[bg_id].position = pos

    db.commit()
    return ok(data=None)
```

- [ ] **Step 7: Run lsp_diagnostics on profile.py**

---

## Task 5: Backend — Files Router (Serve by ID)

**Files:**
- Modify: `backend/routers/files.py`

- [ ] **Step 1: Add imports**

Add after existing imports:

```python
from backend.models.user_background import UserBackground
```

- [ ] **Step 2: Add the serve endpoint**

Add before the `serve_avatar` function (or at the end of profile-related endpoints):

```python
@router.get("/profile/backgrounds/{bg_id}")
async def serve_background_by_id(
    bg_id: int,
    request: Request,
    token: Optional[str] = Query(None, description="JWT token for img auth"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    user = _resolve_user(token, current_user, db, request)

    bg = db.query(UserBackground).filter(
        UserBackground.id == bg_id,
        UserBackground.user_id == user.id,
    ).first()
    if not bg:
        raise AppException(code=4004, message="Background not found", status_code=404)

    abs_path = file_service.get_file_path(bg.image_path)
    if not abs_path.exists():
        raise AppException(code=4004, message="Background file not found on disk", status_code=404)

    def file_iter():
        with open(abs_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        file_iter(),
        media_type=_get_mime(abs_path),
        headers={"Content-Disposition": "inline", "Accept-Ranges": "bytes"},
    )
```

- [ ] **Step 3: Run lsp_diagnostics on files.py**

---

## Task 6: Backend — Tests

**Files:**
- Create: `tests/api/test_backgrounds.py`

- [ ] **Step 1: Write test file**

```python
"""Tests for multi-background endpoints."""

import io
import pytest
from PIL import Image


def _make_test_image(width=100, height=100, color="blue", fmt="PNG"):
    img = Image.new("RGB", (width, height), color=color)
    buf = io.BytesIO()
    img.save(buf, format=fmt)
    buf.seek(0)
    return buf.getvalue()


class TestListBackgrounds:
    def test_empty_list(self, client, auth_headers):
        response = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        assert response.status_code == 200
        assert response.json()["data"] == []

    def test_unauthenticated(self, client):
        response = client.get("/api/v1/profile/backgrounds")
        assert response.status_code == 401


class TestUploadBackgroundMulti:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        response = client.post(
            "/api/v1/profile/backgrounds",
            headers=auth_headers,
            files={"file": ("bg1.png", image_data, "image/png")},
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["id"] is not None
        assert data["position"] == 0

    def test_multiple_uploads_increment_position(self, client, auth_headers):
        for i in range(3):
            image_data = _make_test_image(color=["red", "green", "blue"][i])
            resp = client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
            assert resp.status_code == 200
            assert resp.json()["data"]["position"] == i

    def test_max_limit(self, client, auth_headers):
        image_data = _make_test_image()
        for i in range(10):
            client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
        # 11th should fail
        response = client.post(
            "/api/v1/profile/backgrounds",
            headers=auth_headers,
            files={"file": ("bg11.png", image_data, "image/png")},
        )
        assert response.status_code == 400


class TestDeleteBackgroundMulti:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        resp = client.post(
            "/api/v1/profile/backgrounds",
            headers=auth_headers,
            files={"file": ("bg.png", image_data, "image/png")},
        )
        bg_id = resp.json()["data"]["id"]

        response = client.delete(f"/api/v1/profile/backgrounds/{bg_id}", headers=auth_headers)
        assert response.status_code == 200

        # Verify list is empty
        list_resp = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        assert list_resp.json()["data"] == []

    def test_not_found(self, client, auth_headers):
        response = client.delete("/api/v1/profile/backgrounds/999", headers=auth_headers)
        assert response.status_code == 404

    def test_reorder_after_delete(self, client, auth_headers):
        image_data = _make_test_image()
        ids = []
        for i in range(3):
            resp = client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
            ids.append(resp.json()["data"]["id"])

        # Delete the middle one
        client.delete(f"/api/v1/profile/backgrounds/{ids[1]}", headers=auth_headers)

        list_resp = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        remaining = list_resp.json()["data"]
        assert len(remaining) == 2
        assert remaining[0]["position"] == 0
        assert remaining[1]["position"] == 1


class TestReorderBackgrounds:
    def test_success(self, client, auth_headers):
        image_data = _make_test_image()
        ids = []
        for i in range(3):
            resp = client.post(
                "/api/v1/profile/backgrounds",
                headers=auth_headers,
                files={"file": (f"bg{i}.png", image_data, "image/png")},
            )
            ids.append(resp.json()["data"]["id"])

        # Reverse order
        response = client.put(
            "/api/v1/profile/backgrounds/reorder",
            headers=auth_headers,
            json={"background_ids": list(reversed(ids))},
        )
        assert response.status_code == 200

        list_resp = client.get("/api/v1/profile/backgrounds", headers=auth_headers)
        reordered = list_resp.json()["data"]
        assert [bg["id"] for bg in reordered] == list(reversed(ids))


class TestCarouselInterval:
    def test_default_interval(self, client, auth_headers):
        response = client.get("/api/v1/profile", headers=auth_headers)
        assert response.json()["data"]["carousel_interval"] == 5

    def test_update_interval(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            headers=auth_headers,
            json={"carousel_interval": 10},
        )
        assert response.status_code == 200
        assert response.json()["data"]["carousel_interval"] == 10

    def test_interval_too_low(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            headers=auth_headers,
            json={"carousel_interval": 0},
        )
        assert response.status_code == 422

    def test_interval_too_high(self, client, auth_headers):
        response = client.put(
            "/api/v1/profile",
            headers=auth_headers,
            json={"carousel_interval": 301},
        )
        assert response.status_code == 422
```

- [ ] **Step 2: Run the tests**

Run: `python -m pytest tests/api/test_backgrounds.py -v`
Expected: All tests pass.

---

## Task 7: Frontend — API Functions

**Files:**
- Modify: `frontend/src/api/index.js`

- [ ] **Step 1: Add new API functions**

Add after the existing `deleteBackground` function:

```javascript
// --- Multi-backgrounds ---
export const getBackgrounds = () =>
  api.get('/profile/backgrounds')

export const uploadBackgroundMulti = (formData) =>
  api.post('/profile/backgrounds', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })

export const deleteBackgroundMulti = (id) =>
  api.delete(`/profile/backgrounds/${id}`)

export const reorderBackgrounds = (backgroundIds) =>
  api.put('/profile/backgrounds/reorder', { background_ids: backgroundIds })

export function getBackgroundUrlById(bgId, token) {
  return `/api/v1/files/profile/backgrounds/${bgId}?token=${encodeURIComponent(token)}`
}
```

- [ ] **Step 2: Run lsp_diagnostics on api/index.js**

---

## Task 8: Frontend — Auth Store Extension

**Files:**
- Modify: `frontend/src/stores/auth.js`

- [ ] **Step 1: Update imports**

Change the import line to include the new API function:

```javascript
import { login as apiLogin, logout as apiLogout, refreshToken as apiRefresh, revokeAllBlobUrls, getProfile, getBackgrounds } from '../api'
```

- [ ] **Step 2: Add backgrounds state and computed properties**

After the existing `backgroundOpacity` computed, add:

```javascript
const backgrounds = ref(JSON.parse(localStorage.getItem('user_backgrounds') || '[]'))
const carouselInterval = computed(() => userProfile.value?.carousel_interval ?? 5)

const backgroundUrls = computed(() => {
  if (!accessToken.value) return []
  return backgrounds.value.map(bg =>
    `/api/v1/files/profile/backgrounds/${bg.id}?token=${encodeURIComponent(accessToken.value)}`
  )
})
```

- [ ] **Step 3: Add fetchBackgrounds function**

After `fetchProfile`:

```javascript
async function fetchBackgrounds() {
  try {
    const res = await getBackgrounds()
    backgrounds.value = res.data.data
    localStorage.setItem('user_backgrounds', JSON.stringify(backgrounds.value))
    return backgrounds.value
  } catch {
    return []
  }
}
```

- [ ] **Step 4: Call fetchBackgrounds after login and profile fetch**

In the `login` function, after the `if (data.user)` block:

```javascript
await fetchBackgrounds()
```

In the `fetchProfile` function, after `updateProfileInStore(profile)`:

```javascript
await fetchBackgrounds()
```

- [ ] **Step 5: Clear backgrounds on logout**

In the `logout` function, add:

```javascript
backgrounds.value = []
localStorage.removeItem('user_backgrounds')
```

- [ ] **Step 6: Expose new state in return**

Update the return object:

```javascript
return {
  accessToken,
  refreshToken: refreshTokenVal,
  isAuthenticated,
  userProfile,
  avatarUrl,
  backgroundUrl,
  backgroundOpacity,
  backgrounds,
  backgroundUrls,
  carouselInterval,
  login,
  refresh,
  logout,
  fetchProfile,
  fetchBackgrounds,
  updateProfileInStore,
}
```

- [ ] **Step 7: Run lsp_diagnostics on auth.js**

---

## Task 9: Frontend — App.vue Carousel

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Replace entire file**

```vue
<template>
  <div id="app" :style="appStyle">
    <template v-if="authStore.backgroundUrls.length > 0">
      <div
        v-for="(url, idx) in authStore.backgroundUrls"
        :key="idx"
        class="user-bg"
        :style="bgLayerStyle(idx)"
      ></div>
    </template>
    <AppNavbar v-if="authStore.isAuthenticated" />
    <main class="container app-main">
      <router-view />
    </main>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted, onUnmounted } from 'vue'
import { useAuthStore } from './stores/auth'
import AppNavbar from './components/AppNavbar.vue'

const authStore = useAuthStore()
const activeIndex = ref(0)
let timer = null

const appStyle = computed(() => ({
  position: 'relative',
  minHeight: '100vh',
}))

function bgLayerStyle(idx) {
  return {
    position: 'fixed',
    inset: '0',
    backgroundImage: `url(${authStore.backgroundUrls[idx]})`,
    backgroundSize: 'cover',
    backgroundPosition: 'center',
    opacity: idx === activeIndex.value ? authStore.backgroundOpacity : 0,
    zIndex: '-1',
    pointerEvents: 'none',
  }
}

function startCarousel() {
  stopCarousel()
  const urls = authStore.backgroundUrls
  if (urls.length <= 1) {
    activeIndex.value = 0
    return
  }
  timer = setInterval(() => {
    activeIndex.value = (activeIndex.value + 1) % authStore.backgroundUrls.length
  }, authStore.carouselInterval * 1000)
}

function stopCarousel() {
  if (timer) {
    clearInterval(timer)
    timer = null
  }
}

watch(() => authStore.carouselInterval, startCarousel)
watch(() => authStore.backgroundUrls, () => {
  if (activeIndex.value >= authStore.backgroundUrls.length) {
    activeIndex.value = 0
  }
  startCarousel()
})
onMounted(startCarousel)
onUnmounted(stopCarousel)
</script>

<style scoped>
.user-bg {
  transition: opacity 1s ease-in-out;
}
.app-main { padding-top: var(--spacing-lg); padding-bottom: 2rem; position: relative; }
</style>
```

- [ ] **Step 2: Run lsp_diagnostics on App.vue**

---

## Task 10: Frontend — SettingsModal Multi-Image UI

**Files:**
- Modify: `frontend/src/components/SettingsModal.vue`

- [ ] **Step 1: Replace entire file**

```vue
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

const emit = defineEmits(['close'])
const authStore = useAuthStore()

const avatarInput = ref(null)
const bgInput = ref(null)
const avatarPreview = ref(authStore.avatarUrl)
const backgrounds = ref([...authStore.backgrounds])
const opacity = ref(authStore.backgroundOpacity)
const interval = ref(authStore.carouselInterval)

let saveTimer = null

function bgThumbStyle(bg) {
  const url = getBackgroundUrlById(bg.id, authStore.accessToken)
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
  clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    try {
      const res = await updateProfile({ carousel_interval: interval.value })
      authStore.updateProfileInStore(res.data.data)
    } catch {
      // error handled by interceptor
    }
  }, 300)
}

function onOpacityChange() {
  clearTimeout(saveTimer)
  saveTimer = setTimeout(async () => {
    try {
      const res = await updateProfile({ background_opacity: opacity.value })
      authStore.updateProfileInStore(res.data.data)
    } catch {
      // error handled by interceptor
    }
  }, 300)
}

onUnmounted(() => clearTimeout(saveTimer))
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
```

- [ ] **Step 2: Run lsp_diagnostics on SettingsModal.vue**

---

## Task 11: Integration Verification

- [ ] **Step 1: Run backend tests**

Run: `python -m pytest tests/api/test_profile.py tests/api/test_backgrounds.py -v`
Expected: All tests pass.

- [ ] **Step 2: Run full test suite**

Run: `python -m pytest`
Expected: All tests pass (no regressions).

- [ ] **Step 3: Build frontend**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no errors.

- [ ] **Step 4: Manual QA checklist**

1. Start the application
2. Login as admin
3. Open Settings modal → verify "背景图片" section shows empty state
4. Upload 3 background images → verify thumbnails appear in grid
5. Delete one background → verify it disappears, remaining reorder correctly
6. Set carousel interval to 3 seconds → verify slider works
7. Close settings → verify backgrounds rotate every 3 seconds with crossfade
8. Verify opacity slider still works (affects all backgrounds equally)
9. Refresh page → verify backgrounds and interval persist
10. Logout and login → verify backgrounds load correctly

---

## Commit Plan

After all tasks complete:

```bash
git checkout -b feature/multi-background-carousel
git add .
git commit -m "feat: 多背景图轮播功能" -m "实现内容：
- 新增 user_backgrounds 表，支持每用户最多10张背景图
- 旧 background_path 数据自动迁移到新表
- 新增 carousel_interval 字段（1-300秒），控制轮播间隔
- 后端新增背景图 CRUD 接口（上传/删除/重排序）
- 前端 App.vue 实现 CSS crossfade 轮播效果
- 设置界面支持多图管理、间隔调节、透明度调节
- 保持透明度兼容，所有背景图共享全局透明度设置

验证方式：运行 pytest tests/api/test_backgrounds.py 及手动 QA"
```
