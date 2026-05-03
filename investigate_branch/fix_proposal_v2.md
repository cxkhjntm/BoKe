# Fix Proposal V2: DOCX Image Extraction & Rendering

**Date**: 2026-05-03
**Branch**: `investigate/docx-image-extraction`
**Status**: PROPOSED
**Based on**: `diagnosis_v2_1.md` and `diagnosis_v2_2.md`

---

## 1. Defect Summary

| # | Bug | Severity | File | Line(s) |
|---|-----|----------|------|---------|
| 1 | `break` in shapes loop → 1 image/paragraph | CRITICAL | extract_service.py | 100 |
| 2 | Anchored images (<w:anchor>) not captured | CRITICAL | extract_service.py | 81 |
| 3 | Frontend no dual-format support (Option C missing) | CRITICAL | Reader.vue | 189 |
| 4 | Silent exception swallowing | MEDIUM | extract_service.py | 75-76, 97-98 |

---

## 2. Fix Design

### 2.1 Fix A: Remove `break`, process all shapes per paragraph

**File**: `backend/services/extract_service.py`, lines 84-100

**Current** (buggy):
```python
for para in doc.paragraphs:
    if para.text.strip():
        result_parts.append(para.text)
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
        break  # ← REMOVES after first image
```

**Fixed**:
```python
for para in doc.paragraphs:
    if para.text.strip():
        result_parts.append(para.text)
    # Extract ALL inline shapes belonging to this paragraph
    while shape_idx < len(shapes):
        shape = shapes[shape_idx]
        try:
            rId = shape._inline.graphic.graphicData.pic.blipFill.blip.embed
            if rId in image_map:
                img_index = len(extracted_images)
                extracted_images.append(image_map[rId])
                result_parts.append(f"[image:{img_index}]")
        except Exception as e:
            logger.warning("Failed to extract inline shape %d: %s", shape_idx, e)
        shape_idx += 1
```

**Key change**: Remove `break`, add `shape_idx += 1` unconditionally. Also add warning log for failed extractions.

**Problem**: This approach still can't determine WHICH paragraph a shape belongs to — `doc.inline_shapes` doesn't carry paragraph association. The current approach assumes shapes appear in document order, which is generally true for inline shapes.

### 2.2 Fix B: Add anchored image support

**File**: `backend/services/extract_service.py`

Add a new function to extract anchored images from the DOCX XML:

```python
def _get_anchored_images(doc):
    """Extract image references from anchored (w:anchor) elements."""
    nsmap = {
        'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
        'wp': 'http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing',
        'a': 'http://schemas.openxmlformats.org/drawingml/2006/main',
        'r': 'http://schemas.openxmlformats.org/officeDocument/2006/relationships',
    }
    anchored = []
    for anchor in doc.element.body.findall('.//w:body//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}anchor', nsmap):
        # Navigate to the blip embed reference
        blip = anchor.find('.//' + '{http://schemas.openxmlformats.org/drawingml/2006/main}blip')
        if blip is not None:
            embed = blip.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed')
            if embed:
                anchored.append(embed)
    return anchored
```

Then merge anchored image rIds into the extraction pipeline.

**Note**: This is more complex because anchored images don't have a natural paragraph association. We need to determine their position in the document relative to paragraphs.

### 2.3 Fix C: Frontend dual-format rendering (Option C from V1)

**File**: `frontend/src/views/Reader.vue`, function `renderDocxContent()`

**Current** (only handles new format):
```javascript
const segments = text.split(/\[image:(\d+)\]/g)
```

**Fixed** (handles both formats):
```javascript
function renderDocxContent(text, docId) {
  // Match both [image:N] (new) and [image: data:...;base64,...] (old)
  const regex = /\[image:(?:(\d+)|\s*(data:[^;]+;base64,([A-Za-z0-9+/=\s]+)))\]/g
  const parts = []
  let lastIndex = 0
  let match

  while ((match = regex.exec(text)) !== null) {
    // Add text before this match
    if (match.index > lastIndex) {
      const textSegment = text.slice(lastIndex, match.index).trim()
      if (textSegment) {
        parts.push(textSegment.split(/\n\n+/).map(p => `<p>${escapeHtml(p.trim())}</p>`).join(''))
      }
    }

    if (match[1]) {
      // New format: [image:N]
      const imgIndex = parseInt(match[1], 10)
      const imgSrc = getDocxImageUrl(docId, imgIndex)
      parts.push(`<img src="${imgSrc}" alt="文档图片 ${imgIndex}" loading="lazy" />`)
    } else if (match[2]) {
      // Old format: [image: data:...;base64,...]
      const src = match[2].replace(/\s/g, '')  // strip whitespace from base64
      parts.push(`<img src="${src}" alt="文档图片" loading="lazy" />`)
    }

    lastIndex = match.index + match[0].length
  }

  // Add remaining text after last match
  if (lastIndex < text.length) {
    const textSegment = text.slice(lastIndex).trim()
    if (textSegment) {
      parts.push(textSegment.split(/\n\n+/).map(p => `<p>${escapeHtml(p.trim())}</p>`).join(''))
    }
  }

  return parts.join('')
}
```

### 2.4 Fix D: Log extraction warnings

**File**: `backend/services/extract_service.py`

Replace bare `except: continue` with logged warnings:
```python
except Exception as e:
    logger.warning("Failed to extract image from rel %s: %s", rel.rId, e)
    continue
```

---

## 3. Resource Impact Analysis

### 3.1 Storage

| Metric | Before Fix | After Fix | Delta |
|--------|-----------|-----------|-------|
| DB content_text | Same | Same | No change |
| Disk images | Same count, wrong order | Correct count, correct order | No size change |
| Log output | None | ~10 lines per failed extraction | Negligible |

### 3.2 CPU

| Operation | Before Fix | After Fix | Delta |
|-----------|-----------|-----------|-------|
| Upload processing | 1 image/para | All images/para | +negligible (loop iteration) |
| Anchored image extraction | N/A (skipped) | XML traversal | +0.1-0.5s per doc |
| Frontend render | Regex on [image:N] only | Regex on both formats | +negligible |

### 3.3 Memory

| Scenario | Before Fix | After Fix | Delta |
|----------|-----------|-----------|-------|
| Extraction | Same | Same | No change |
| Frontend base64 images | N/A (shown as text) | Inline base64 <img> | +image size in DOM (old format only) |

### 3.4 Development & Risk

| Dimension | Estimate |
|-----------|----------|
| Backend changes | 1 file (`extract_service.py`), ~30 lines modified |
| Frontend changes | 1 file (`Reader.vue`), ~25 lines modified |
| Dev time | 1-2 hours |
| Test time | 30 min (run existing + add new tests) |
| Deployment risk | LOW — no schema change, no migration |
| Rollback difficulty | EASY — `git revert` |
| Breaking changes | NONE — all changes are backward compatible |

---

## 4. Recommended Implementation Order

1. **Fix A** — Remove `break` in extract_service.py (highest impact, lowest risk)
2. **Fix D** — Add logging for extraction failures
3. **Fix C** — Frontend dual-format rendering in Reader.vue
4. **Fix B** — Anchored image support (more complex, can be a follow-up)

Fixes A+D+C address both reported bugs. Fix B is a robustness improvement for documents with wrapped images.

---

## 5. Verification Plan

1. Run existing tests: `pytest tests/test_extract.py -v`
2. Add test for multiple images per paragraph
3. Add test for base64 format detection in frontend
4. Manual test: re-upload 毕业论文.docx and 智能问答技术难点.docx
5. Verify images render correctly in Reader view
