# Design Review: DOCX Image Extraction Fix

**Date**: 2026-05-03
**Reviewer**: Agent (Reviewer Role)
**Verdict**: **APPROVE WITH MINOR NOTES**

---

## 1. Diagnosis Report Review

### Completeness: PASS
- Root cause clearly identified across both backend and frontend layers
- Call chain documented with exact file/line references
- Evidence includes actual code snippets
- Impact assessment is accurate

### Accuracy: PASS
- Confirmed: `extract_service.py:79` does use `[image: data:{ct};base64,{b64}]` format
- Confirmed: `Reader.vue:73` uses `{{ doc.content_text }}` (plain text interpolation)
- Confirmed: No image serving endpoint exists in `files.py`
- Confirmed: `content_text` is a single Text column with no structured data

### Minor Note
- The diagnosis correctly identifies the problem but could note that `inline_shapes` only captures inline images. Floating/anchored images (via `doc.inline_shapes` vs drawing ML) may not be captured. This is a pre-existing limitation, not introduced by this fix.

---

## 2. Fix Proposal Review

### Architecture: PASS
- Clean three-layer separation (extract → serve → render)
- Index-based marker format `[image:N]` is simple, unambiguous, and parseable
- Follows existing patterns (auth via query param for `<img>` tags, same as thumbnail endpoint)
- No DB schema change needed — `content_text` column reused with different content format

### Security: PASS
- Auth required on image serving endpoint (JWT + ownership check)
- Index-based lookup prevents path traversal (no user-controlled filenames)
- DOMPurify sanitization on frontend (existing pattern from Markdown rendering)
- No new attack surface introduced

### Resource Analysis: PASS
- Storage: significant DB reduction, modest disk increase — net positive
- CPU: negligible change
- Memory: improvement for image-heavy docs (no more base64 in DOM)
- Network: document API response shrinks dramatically; separate image requests add overhead but are standard web behavior

### Backward Compatibility: PASS (with note)
- Option C (frontend dual-format) is the right call — zero migration burden
- Old documents degrade gracefully (base64 text still visible, just not rendered as images)
- Users can re-upload to get the improved behavior

### Rollback Safety: PASS
- Pure code change, no DB migration
- `git revert` cleanly undoes everything
- Old documents unaffected (their content_text still has base64 markers)

---

## 3. Potential Issues to Watch

1. **Image ordering assumption**: The proposal assumes images are extracted in document order. The current `_extract_docx()` iterates `doc.inline_shapes` which may not perfectly match visual order in complex layouts. This is acceptable for v1 but worth noting.

2. **Large image count**: A DOCX with 100+ images would create 100+ HTTP requests on the frontend. Consider lazy loading (`loading="lazy"`) on `<img>` tags.

3. **Disk cleanup**: The `delete_docx_images()` function uses `shutil.rmtree()`. Ensure this is called in all document deletion paths (manual delete, admin delete, cascade).

4. **Existing test**: `tests/test_extract.py` likely tests the old base64 marker format. Tests will need updating.

---

## 4. Verdict

**APPROVE** — The diagnosis is complete and accurate. The fix proposal is well-architected, secure, and minimally invasive. No blocking issues found. The minor notes above are informational and do not require changes to the proposal.

Proceed to implementation.
