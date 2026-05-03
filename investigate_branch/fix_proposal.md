# Fix Proposal: DOCX Embedded Images — Extract and Render Inline

**Date**: 2026-05-03
**Branch**: `investigate/docx-image-extraction`
**Status**: PROPOSED

---

## 1. Approach Overview

**Strategy**: Extract images to disk during DOCX processing, replace inline base64 with lightweight index markers, add a serving endpoint, and render images inline on the frontend.

**Marker format**: `[image:N]` where N is a 0-based index into the extracted images for that document.

Example `content_text` after fix:
```
这是一段文字。

[image:0]

这是另一段文字。

[image:1]

更多文字内容。
```

---

## 2. Affected Files and Changes

### 2.1 Backend: `backend/services/file_service.py`
**Change**: Add `save_docx_images()` and `delete_docx_images()` helpers.

```python
def save_docx_images(user_id: int, doc_id: int, images: list[tuple[str, bytes]]) -> list[str]:
    """Save extracted DOCX images to storage/{user_id}/docx_images/{doc_id}/.
    images: list of (extension, binary_data)
    Returns list of relative paths.
    """
    img_dir = STORAGE_PATH / str(user_id) / "docx_images" / str(doc_id)
    img_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, (ext, data) in enumerate(images):
        filename = f"{i}{ext}"
        (img_dir / filename).write_bytes(data)
        paths.append(str((img_dir / filename).relative_to(STORAGE_PATH)))
    return paths

def delete_docx_images(user_id: int, doc_id: int) -> None:
    """Delete all extracted images for a DOCX document."""
    img_dir = STORAGE_PATH / str(user_id) / "docx_images" / str(doc_id)
    if img_dir.exists():
        import shutil
        shutil.rmtree(img_dir)
```

### 2.2 Backend: `backend/services/extract_service.py`
**Change**: `_extract_docx()` now saves images to disk and returns lightweight markers.

- Accept additional params: `user_id`, `doc_id`
- Save images via `file_service.save_docx_images()`
- Return `content_text` with `[image:N]` markers instead of base64

### 2.3 Backend: `backend/routers/files.py`
**Change**: Add new endpoint for serving extracted DOCX images.

```
GET /api/v1/files/{doc_id}/docx_images/{image_index}
```
- Auth: JWT Bearer or `?token=` query param (same as thumbnail)
- Ownership check: verify `doc.user_id == user.id`
- Path validation: prevent traversal via index bounds check
- Serve with correct MIME type from file extension

### 2.4 Backend: `backend/services/processing_service.py`
**Change**: Pass `user_id` and `doc_id` to `extract_service.extract_text()` for DOCX.

### 2.5 Backend: `backend/services/document_service.py`
**Change**: On document delete, also call `file_service.delete_docx_images()`.

### 2.6 Frontend: `frontend/src/views/Reader.vue`
**Change**: Replace plain text rendering with structured HTML for DOCX.

- Parse `content_text` with regex: `/\[image:(\d+)\]/g`
- Split into segments: `[{type: "text", value: "..."}, {type: "image", index: N}, ...]`
- Render text segments as `<p>` tags, image segments as `<img>` tags
- Image `src` = `/api/v1/files/{docId}/docx_images/{index}?token={jwt}`
- Use `v-html` with DOMPurify sanitization (same pattern as Markdown)
- Add CSS styles for DOCX images (reuse `.md-content img` styles)

### 2.7 Frontend: `frontend/src/api/index.js`
**Change**: Add `fetchDocxImageUrl(docId, imageIndex)` helper that returns authenticated URL.

---

## 3. Backward Compatibility

Existing documents with `[image: data:...;base64,...]` markers will continue to display as text. Two options:

| Option | Description | Effort |
|--------|-------------|--------|
| A. Auto-migrate | Add a one-time migration script that re-processes all existing DOCX documents | Medium (need to handle edge cases) |
| B. Manual re-upload | Users re-upload affected documents | Zero effort, but poor UX |
| C. Frontend dual-format | Frontend handles both old base64 and new index markers | Low effort, covers both |

**Recommendation**: Option C — the frontend can detect both marker formats. Old markers render as base64 `<img>` (works, just less efficient), new markers render via serving endpoint. No migration needed.

---

## 4. Resource Impact Analysis

### 4.1 Storage

| Metric | Before (base64 in DB) | After (files on disk) | Delta |
|--------|----------------------|----------------------|-------|
| DB `content_text` size | ~1.33x original image bytes (base64) | ~0.001x (just markers) | **-99% DB storage for images** |
| Disk storage | 0 (images in DB) | ~1.0x original image bytes | **+disk, but native format** |
| Example: 10 images × 500KB | ~6.65 MB in DB | ~5 MB on disk + ~100 bytes in DB | Net savings ~1.6 MB per doc |

### 4.2 CPU

| Operation | Before | After | Delta |
|-----------|--------|-------|-------|
| Upload processing | base64 encode (fast) | file write (fast) | Negligible |
| Serving | N/A (data in DB response) | File read + stream | Minimal increase |
| Frontend parse | N/A (plain text) | Regex split | Negligible |

### 4.3 Memory

| Scenario | Before | After | Delta |
|----------|--------|-------|-------|
| DB query for document | Loads full base64 into memory | Loads small marker text | **-significant for image-heavy docs** |
| Frontend render | Entire base64 in DOM as text | Images loaded lazily via `<img>` | **-significant** |

### 4.4 Network

| Scenario | Before | After | Delta |
|----------|--------|-------|-------|
| GET /documents/{id} | Returns full base64 in JSON | Returns small markers | **-90%+ for image-heavy docs** |
| Image loading | N/A | Separate requests per image | +HTTP overhead per image |

### 4.5 Development & Risk

| Dimension | Estimate |
|-----------|----------|
| Backend changes | ~3 files, ~80 lines new/modified |
| Frontend changes | ~1 file, ~50 lines new/modified |
| Dev time | 2-4 hours |
| Test time | 1-2 hours |
| Deployment risk | LOW — no DB schema change, no migration required |
| Rollback difficulty | EASY — `git revert` the commit; old docs still work with base64 format |

---

## 5. Security Considerations

1. **Auth on image endpoint**: Must verify JWT + document ownership (same pattern as existing endpoints)
2. **Path traversal**: Index-based lookup (not filename) prevents traversal attacks
3. **XSS**: DOMPurify sanitization on frontend (already used for Markdown)
4. **File type validation**: Only serve files from the docx_images directory, verify MIME types

---

## 6. Recommended Implementation Order

1. `file_service.py` — add `save_docx_images()` / `delete_docx_images()`
2. `extract_service.py` — modify `_extract_docx()` to save images and use `[image:N]` markers
3. `processing_service.py` — pass `user_id`/`doc_id` through to extraction
4. `files.py` router — add `GET /{doc_id}/docx_images/{index}` endpoint
5. `document_service.py` — cleanup images on document delete
6. `Reader.vue` — parse markers and render inline images
7. Tests — update extraction tests, add integration test for image serving
