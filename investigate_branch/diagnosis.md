# Diagnosis Report: DOCX Embedded Images Displayed as Base64 Text

**Date**: 2026-05-03
**Branch**: `investigate/docx-image-extraction`
**Severity**: HIGH (functional defect — images completely invisible in DOCX preview)

---

## 1. Problem Description

When a `.docx` file containing embedded images is uploaded, the document preview renders image data as a literal base64 text string:

```
[image: data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAABPM...]
```

instead of displaying the actual image. The text can be extremely long (megabytes), destroying readability.

## 2. Root Cause Analysis

The defect spans two layers — **backend extraction** and **frontend rendering** — with no bridge between them.

### 2.1 Backend: Inline Base64 Markers in `content_text`

**File**: `backend/services/extract_service.py`, function `_extract_docx()` (lines 46-98)

The extraction pipeline:
1. Builds an image map from DOCX relationships (lines 53-62): reads each image blob, base64-encodes it, stores `{rId: (content_type, base64_string)}`.
2. Iterates paragraphs and inline shapes in document order (lines 64-97).
3. For each inline shape, appends a marker string to the text output (line 79):
   ```python
   result_parts.append(f"[image: data:{ct};base64,{b64}]")
   ```
4. Joins all parts with `\n` and stores the result in `doc.content_text` (a single `Text` column in SQLite).

**Problem**: The entire base64-encoded image (potentially several MB) is embedded directly in the text content. There is no image extraction to separate files, no URL reference, and no structured marker format.

### 2.2 Frontend: Plain Text Rendering with No Image Parsing

**File**: `frontend/src/views/Reader.vue`, line 72-75

```vue
<div v-else-if="doc.file_type === 'docx'" class="text-viewer">
  <div v-if="doc.status === 'ready' && doc.content_text" class="text-content">{{ doc.content_text }}</div>
</div>
```

**Problem**: Vue's `{{ }}` text interpolation escapes all HTML. The base64 marker is rendered as literal text — it is never parsed into an `<img>` tag. Even if it were, `content_text` is treated as a plain string with no structured parsing.

### 2.3 No Supporting Infrastructure

- **No image storage**: Extracted images are not saved to disk; they exist only as base64 strings in the database text column.
- **No image serving endpoint**: The file serving router (`backend/routers/files.py`) only serves original files and thumbnails — there is no endpoint for extracted document images.
- **No image URL schema**: There is no mechanism to reference extracted images by URL.

## 3. Call Chain

```
User uploads .docx
  → POST /api/v1/documents (documents.py:109)
    → file_service.save_file() — saves original to storage/{user_id}/original/{uuid}.docx
    → document_service.create_document() — creates DB row with status="queued"
    → _dispatch_processing() — enqueues Celery task
      → process_document_task (tasks.py)
        → processing_service.process_document()
          → extract_service.extract_text(file_path, "docx")
            → _extract_docx(file_path)
              → Builds image_map from DOCX relationships
              → Iterates paragraphs + inline_shapes
              → Appends "[image: data:{ct};base64,{b64}]" markers
              → Returns joined text string
            → Stored in doc.content_text

User opens document preview
  → GET /api/v1/documents/{id}
    → Returns doc with content_text containing base64 markers
  → Reader.vue renders {{ doc.content_text }} as plain text
    → Base64 markers displayed as literal text strings ← DEFECT
```

## 4. Evidence

### 4.1 Code Evidence — Backend Marker Format
`backend/services/extract_service.py:79`:
```python
result_parts.append(f"[image: data:{ct};base64,{b64}]")
```

### 4.2 Code Evidence — Frontend Plain Text Rendering
`frontend/src/views/Reader.vue:73`:
```vue
<div class="text-content">{{ doc.content_text }}</div>
```

### 4.3 Data Model Limitation
`backend/models/document.py:29`:
```python
content_text = Column(Text, nullable=True)
```
Single text column — no structured content or separate image references.

### 4.4 No Image Serving Endpoint
`backend/routers/files.py` serves only:
- `GET /api/v1/files/{doc_id}/original` — the original uploaded file
- `GET /api/v1/files/{doc_id}/thumbnail` — the generated thumbnail

No endpoint exists for extracted document images.

## 5. Impact

- **Severity**: HIGH — images in DOCX documents are completely non-functional
- **Scope**: All uploaded `.docx` files containing images
- **User experience**: Base64 text blobs destroy readability; users see megabytes of encoded garbage
- **Data bloat**: Base64 encoding increases image size by ~33%, stored in the database text column

## 6. Trigger Conditions

1. Upload a `.docx` file containing at least one inline image
2. Wait for processing to complete (status = "ready")
3. Open the document in the Reader view
4. Observe `[image: data:image/png;base64,...]` as literal text instead of rendered image

## 7. Recommended Fix Direction

The fix requires changes at three layers:

1. **Backend extraction**: Save extracted images to disk (e.g., `storage/{user_id}/docx_images/{doc_id}/{index}.{ext}`), store only lightweight markers in `content_text` (e.g., `[image:docx_images/{doc_id}/0.png]`)
2. **Backend serving**: Add an endpoint to serve extracted DOCX images (with auth)
3. **Frontend rendering**: Parse image markers in `content_text`, split into text segments and `<img>` tags, render as structured HTML (similar to how Markdown is rendered with `v-html` + DOMPurify)
