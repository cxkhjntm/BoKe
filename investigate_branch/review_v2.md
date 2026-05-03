# Review V2: DOCX Image Fix Proposal

**Date**: 2026-05-03
**Branch**: `investigate/docx-image-extraction`
**Reviewer**: team-lead (acting as reviewer)
**Status**: **APPROVED** with minor notes

---

## 1. Diagnosis Review

### diagnosis_v2_1.md (Backend Extraction)

| Item | Verdict | Notes |
|------|---------|-------|
| Root cause identification | ✅ PASS | `break` bug correctly identified at line 100 |
| Anchored image gap | ✅ PASS | Correctly identifies `inline_shapes` limitation |
| Code evidence | ✅ PASS | Specific line numbers cited |
| Call chain | ✅ PASS | Clear trace from upload to extraction failure |

**Minor note**: The report could mention that `doc.inline_shapes` iteration order matches XML document order for inline elements, which is why the fix (removing `break`) preserves correct ordering.

### diagnosis_v2_2.md (Pipeline & Frontend)

| Item | Verdict | Notes |
|------|---------|-------|
| Root cause identification | ✅ PASS | Missing dual-format support correctly identified |
| DOMPurify ruling | ✅ PASS | Correct — DOMPurify allows `<img>` with `src` |
| Serving endpoint ruling | ✅ PASS | Correct — endpoint is functional |
| Image corruption pathway | ✅ PASS | Wrong extraction order → wrong file mapping |

**Verdict**: Both diagnosis reports are **COMPLETE** and **ACCURATE**.

---

## 2. Fix Proposal Review

### Fix A: Remove `break` (CRITICAL)

| Aspect | Assessment |
|--------|-----------|
| Correctness | ✅ Removing `break` allows all shapes per paragraph to be processed |
| Side effects | ⚠️ Minor: If shapes are NOT in document order, images could be misassigned. However, python-docx iterates `inline_shapes` in XML order, which matches visual order for inline elements. |
| Performance | ✅ Negligible — just removing one `break` statement |
| Testability | ✅ Existing test can be extended with multi-image paragraph |

**Verdict**: ✅ APPROVE

### Fix B: Anchored image support (HIGH)

| Aspect | Assessment |
|--------|-----------|
| Correctness | ✅ XML traversal approach is standard for accessing anchored elements |
| Complexity | ⚠️ Medium — needs namespace handling and position calculation |
| Risk | ⚠️ Low-medium — new code path, but isolated from existing logic |
| Recommendation | Defer to follow-up PR — not needed to fix the two reported bugs |

**Verdict**: ✅ APPROVE (recommend deferring to follow-up)

### Fix C: Frontend dual-format (CRITICAL)

| Aspect | Assessment |
|--------|-----------|
| Correctness | ✅ Regex handles both `[image:N]` and `[image: data:...;base64,...]` |
| Security | ⚠️ Need to ensure base64 data is sanitized before use in `src` attribute. DOMPurify already handles this — `data:` URIs are allowed for `<img src>`. |
| Performance | ✅ Regex is efficient, no performance concern |
| Backward compat | ✅ Solves the old-format rendering problem completely |

**Security note**: The base64 `src` value goes through DOMPurify sanitization (line 181), which allows `data:` URIs on `<img>` tags. This is safe — `data:image/...` cannot execute JavaScript.

**Verdict**: ✅ APPROVE

### Fix D: Logging (MEDIUM)

| Aspect | Assessment |
|--------|-----------|
| Correctness | ✅ `logger.warning()` is appropriate for extraction failures |
| Performance | ✅ No impact — logging only on error path |
| Observability | ✅ Significantly improves debuggability |

**Verdict**: ✅ APPROVE

---

## 3. Resource Assessment Review

| Claim | Assessment |
|-------|-----------|
| "No DB schema change" | ✅ Correct — content_text column unchanged |
| "No migration" | ✅ Correct |
| "~55 lines total changes" | ✅ Reasonable estimate |
| "LOW deployment risk" | ✅ Correct — changes are isolated to extraction + rendering |
| "Easy git revert" | ✅ Correct — single commit revertable |

**Verdict**: ✅ Resource assessment is **ACCURATE** and **REASONABLE**.

---

## 4. Final Verdict

**APPROVED** — All four fixes are safe, correct, and well-scoped.

### Recommended Implementation:
1. Apply Fix A + D together (backend extraction)
2. Apply Fix C (frontend rendering)
3. Defer Fix B (anchored images) to a follow-up PR

### Rollback Plan:
- `git revert <commit>` on the fix commit
- Old documents continue to work (they already don't render images)
- No database rollback needed

---

## 5. Post-Review Action Items

- [x] Implement Fix A: Remove `break` in extract_service.py (commit ae5d5e8)
- [x] Implement Fix D: Add extraction warning logs (commit ae5d5e8)
- [x] Implement Fix C: Frontend dual-format in Reader.vue (commit 09035db)
- [x] Run full test suite — 114 passed, 0 failed
- [ ] Manual verification with sample DOCX files (requires running app)
- [ ] (Follow-up) Implement Fix B: Anchored image support

## 6. Final Verification (2026-05-03)

| Check | Result |
|-------|--------|
| Full test suite | ✅ 114 passed, 0 failed |
| extract_service.py coverage | 80% |
| New multi-image test | ✅ Passes |
| Backward compat (base64 regex) | ✅ Regex matches both formats |
| DOMPurify safety | ✅ data: URIs allowed on img src |
| No schema changes | ✅ Confirmed |
| Rollback plan | ✅ git revert on fix commits |

**Status**: READY TO MERGE
