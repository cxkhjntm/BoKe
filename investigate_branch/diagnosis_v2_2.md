# Diagnosis Report V2 — Pipeline, Serving & Frontend Analysis

**Date**: 2026-05-03
**Branch**: `investigate/docx-image-extraction`
**Analyst**: Diagnoser 2 (team-lead fallback)
**Severity**: HIGH — frontend backward compatibility gap and image corruption pathway

---

## 1. Problem Summary

| Document | Symptom | Likely Cause |
|----------|---------|-------------|
| 毕业论文.docx | Base64 text displayed | Old format in DB + no frontend dual-format support |
| 智能问答技术难点.docx | Images corrupted | Wrong image-to-marker mapping due to extraction bugs |

---

## 2. Root Cause Analysis

### 2.1 BUG 1: Frontend backward compatibility NOT implemented (CRITICAL — explains 毕业论文.docx)

**File**: `frontend/src/views/Reader.vue`, lines 187-206

```javascript
function renderDocxContent(text, docId) {
  const segments = text.split(/\[image:(\d+)\]/g)  // Only matches [image:N]
  // ...
}
```

The fix proposal (`fix_proposal.md`, section 3) approved **Option C: Frontend dual-format** — the frontend should handle BOTH:
- Old format: `[image: data:image/png;base64,iVBORw0KGgo...]`
- New format: `[image:0]`

**But this was NEVER implemented.** The current regex `/\[image:(\d+)\]/g` only matches the new numeric index format. Documents uploaded before the fix (or documents that weren't reprocessed) still have base64 markers in their `content_text`. These markers are NOT matched by the regex, so they appear as literal text.

**This is the primary cause of 毕业论文.docx showing base64 text.** The document was either:
1. Uploaded before the fix was applied, OR
2. Not reprocessed after the fix was deployed

**Evidence**:
- `fix_proposal.md` line 105: "Option C — the frontend can detect both marker formats"
- `fix_proposal.md` line 107: "Old markers render as base64 `<img>` (works, just less efficient)"
- Reader.vue line 189: regex only matches `(\d+)` — no base64 handling

### 2.2 BUG 2: DOMPurify does NOT cause image corruption (RULED OUT)

**File**: `frontend/src/views/Reader.vue`, line 181

```javascript
renderedDocx.value = DOMPurify.sanitize(renderDocxContent(doc.value.content_text, doc.value.id))
```

DOMPurify with default settings:
- **Allows**: `<img>` tags with `src`, `alt`, `loading` attributes
- **Allows**: URLs with query parameters (like `?token=...`)
- **Does NOT strip**: standard image attributes

Verified by checking DOMPurify's default allowlist: `<img>` is a safe element, `src` is a safe attribute. The `?token=` query parameter in the URL is not affected.

**Conclusion**: DOMPurify is NOT the cause of image corruption.

### 2.3 BUG 3: Image serving endpoint is correct (RULED OUT)

**File**: `backend/routers/files.py`, lines 189-221

The serving endpoint:
1. Authenticates user via JWT or query param token ✓
2. Checks document ownership (`doc.user_id == user.id`) ✓
3. Resolves image path via `file_service.get_docx_image_path()` ✓
4. Serves with correct MIME type from file extension ✓

**File**: `backend/services/file_service.py`, lines 82-94

```python
def get_docx_image_path(user_id: int, doc_id: int, index: int) -> Path | None:
    img_dir = STORAGE_PATH / str(user_id) / "docx_images" / str(doc_id)
    if not img_dir.exists():
        return None
    for f in sorted(img_dir.iterdir()):
        if f.stem == str(index) and f.is_file():
            return f
    return None
```

The path resolution uses `sorted()` iteration and `f.stem == str(index)` matching. This is correct — files are named `{index}{ext}` (e.g., `0.png`, `1.jpg`), so stem `0` matches index `0`.

**Conclusion**: The serving pipeline is correct. Image corruption is NOT caused by serving.

### 2.4 BUG 4: Image saving is correct but depends on extraction order (CONFIRMED)

**File**: `backend/services/file_service.py`, lines 54-71

```python
def save_docx_images(user_id: int, doc_id: int, images: list[tuple[str, bytes]]) -> int:
    img_dir = STORAGE_PATH / str(user_id) / "docx_images" / str(doc_id)
    img_dir.mkdir(parents=True, exist_ok=True)
    for i, (ext, data) in enumerate(images):
        filename = f"{i}{ext}"
        (img_dir / filename).write_bytes(data)
    return len(images)
```

Images are saved with sequential indices (`0.png`, `1.jpg`, etc.) based on their position in the `extracted_images` list. If the extraction order is wrong (due to the `break` bug in extract_service.py), the saved images will have wrong indices, and `[image:N]` markers will point to wrong files.

**This is the cause of 智能问答技术难点.docx image corruption**: images are extracted in wrong order due to the `break` bug, so `[image:0]` might point to image #3's data, `[image:1]` to image #1's data, etc.

---

## 3. The Missing Piece: Reprocessing

Even with all extraction bugs fixed, existing documents in the database still have their old `content_text` (with base64 markers or wrong image indices). Two approaches:

| Approach | Description | Risk |
|----------|-------------|------|
| A. Auto-migration | Script to reprocess all DOCX documents | Medium — needs careful testing |
| B. Manual re-upload | Users re-upload affected documents | Low risk, poor UX |
| C. Frontend dual-format | Frontend handles both formats (already approved) | Low risk, covers both |

**Recommendation**: Implement Option C (frontend dual-format) AND provide a reprocess API endpoint for users who want to fix existing documents.

---

## 4. Summary of Findings

| # | Bug | Location | Severity | Explains |
|---|-----|----------|----------|----------|
| 1 | Frontend only handles new [image:N] format | Reader.vue:189 | CRITICAL | 毕业论文.docx base64 text |
| 2 | Break in shapes loop = 1 image per paragraph | extract_service.py:100 | HIGH | Wrong image ordering |
| 3 | Anchored images not captured | extract_service.py:81 | HIGH | Missing images |
| 4 | Wrong extraction order → wrong image data | extract_service.py:84-100 | HIGH | 智能问答 corrupted images |

---

## 5. Recommended Fixes

1. **Reader.vue**: Add dual-format regex that matches both `[image:N]` and `[image: data:...;base64,...]`
2. **extract_service.py**: Remove `break`, process all shapes per paragraph
3. **extract_service.py**: Add anchored image support via XML traversal
4. **(Optional)** Add a reprocess endpoint for existing documents
