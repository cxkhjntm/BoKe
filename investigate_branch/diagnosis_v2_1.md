# Diagnosis Report V2 — Backend Extraction Analysis

**Date**: 2026-05-03
**Branch**: `investigate/docx-image-extraction`
**Analyst**: Diagnoser 1 (team-lead fallback)
**Severity**: HIGH — multiple extraction defects causing missing and corrupted images

---

## 1. Problem Summary

After the first fix (commit `1ab6bf2`), two bugs remain:

| Document | Symptom |
|----------|---------|
| 毕业论文.docx | Still shows base64 text, images not rendering |
| 智能问答技术难点.docx | Images display but are corrupted/unreadable |

---

## 2. Root Cause Analysis

### 2.1 BUG 1: Only ONE image extracted per paragraph (CRITICAL)

**File**: `backend/services/extract_service.py`, lines 84-100

```python
for para in doc.paragraphs:
    if para.text.strip():
        result_parts.append(para.text)
    # Interleave inline shapes that belong to this paragraph
    while shape_idx < len(shapes):
        shape = shapes[shape_idx]
        try:
            rId = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            if rId in image_map:
                img_index = len(extracted_images)
                extracted_images.append(image_map[rId])
                result_parts.append(f"[image:{img_index}]")
            shape_idx += 1
        except Exception:
            shape_idx += 1
            continue
        break  # ← BUG: exits after first successful shape
```

**The `break` at line 100** exits the `while` loop after processing the FIRST inline shape in a paragraph. If a paragraph contains 2+ inline images, only the first is extracted with paragraph context. The remaining images fall through to the "remaining shapes" loop (lines 102-113) where they lose their paragraph association.

**Impact**:
- Images after the first in a paragraph are appended at the END of the document
- Document structure (text-image-text-image ordering) is broken
- For documents with many images per paragraph, this causes severe misalignment

**Evidence**: Test `test_extract_docx_with_image_placeholder` (test_extract.py:33) only tests ONE image per paragraph, so this bug was never caught.

### 2.2 BUG 2: Anchored/wrapped images completely missed (CRITICAL)

**File**: `backend/services/extract_service.py`, line 81

```python
shapes = list(doc.inline_shapes)
```

`doc.inline_shapes` only contains `<w:inline>` elements. DOCX files with **wrapped or floating images** use `<w:anchor>` elements, which are NOT included in `inline_shapes`. These images are:

- Not found in the shapes list
- Never extracted to disk
- Never get `[image:N]` markers
- Their binary data sits in `image_map` but is never consumed

**Impact**: Any DOCX with wrapped text around images (common in academic papers like 毕业论文.docx) will have those images completely missing.

**Evidence**: python-docx documentation confirms `inline_shapes` only covers inline elements. Anchored shapes require direct XML access via `doc.element.body.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}anchor')`.

### 2.3 BUG 3: Image ordering depends on iteration order (MEDIUM)

**File**: `backend/services/extract_service.py`, lines 67-76

```python
image_map = {}  # rId -> (extension, bytes)
for rel in doc.part.rels.values():
    if "image" in rel.reltype:
        ...
        image_map[rel.rId] = (ext, img_bytes)
```

The `image_map` is keyed by `rId` (relationship ID). The image data itself is correct, but the ORDER in which images appear in the document depends on:

1. The order of `doc.inline_shapes` (which follows document XML order)
2. The `break` bug causing some shapes to be deferred

If the DOCX has images referenced in a different order than they appear visually, the `[image:N]` indices may not match the visual order.

### 2.4 BUG 4: Exception swallowing hides extraction failures (MEDIUM)

**File**: `backend/services/extract_service.py`, lines 75-76 and 97-98

```python
except Exception:
    continue  # silently skip failed image extractions
```

If `rel.target_part.blob` raises an exception (e.g., external image reference, OLE object pretending to be an image), the image is silently skipped. No warning is logged. This makes it impossible to diagnose extraction failures without debugging.

---

## 3. Call Chain Analysis

### For 毕业论文.docx (images not rendering)

```
Upload → _extract_docx()
  → shapes = list(doc.inline_shapes)
  → If images are anchored (w:anchor): shapes is EMPTY or incomplete
  → No [image:N] markers generated
  → content_text has NO image references
  → Frontend renders plain text only
  → OR: if document was uploaded before fix, content_text still has old base64 format
```

### For 智能问答技术难点.docx (images corrupted)

```
Upload → _extract_docx()
  → image_map built correctly (all rIds captured)
  → shapes = list(doc.inline_shapes) — some images found
  → First image per paragraph extracted correctly
  → Subsequent images in same paragraph deferred to "remaining" loop
  → Images saved to disk in WRONG ORDER (deferred images appended last)
  → [image:N] markers reference wrong images
  → Frontend displays wrong image data for each position
  → Images appear "corrupted" because they're showing the WRONG image
```

---

## 4. Recommended Fixes

### Fix 1: Remove the `break` statement
Process ALL inline shapes per paragraph, not just the first.

### Fix 2: Add anchored image support
Access `w:anchor` elements via direct XML traversal and extract their images using the same blip/embed path.

### Fix 3: Log extraction warnings
Replace bare `except: continue` with logged warnings for debugging.

### Fix 4: Sort shapes by document position
Ensure shapes are processed in document order regardless of inline vs anchored.
