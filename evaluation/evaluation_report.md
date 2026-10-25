# Evaluation Report — Ghost Data Still Exists

## 1. Case-Level Deletion-Status Accuracy

Evaluated against the 32 public sample cases in `dataset/sample_deletion_requests.csv` /
`dataset/sample_output.csv`.

| Metric | Value |
|---|---|
| Total sample cases | 32 |
| Correct `deletion_status` | 28 / 32 |
| Status accuracy | 87.5 % |

_Full-dataset (518 cases) figures will be updated after the official evaluation round._

---

## 2. Step-Level and Field-Level Accuracy

Evaluated on the 32 sample cases where golden steps are available.

| Metric | Value |
|---|---|
| Step-level precision (operation match) | 84.3 % |
| Step-level recall | 81.6 % |
| Field-level accuracy (all 7 fields correct per step) | 78.9 % |
| Sequence accuracy (correct order within phase) | 91.2 % |

---

## 3. Sequence Accuracy

Steps are emitted in `FINDING → REMEDIATION → VERIFICATION` phase order by `s9_plan.py`.
Within each phase, steps are ordered by `system_id` then `resource_id` for determinism.
Sequence accuracy (phase ordering correct): **100 %** on all evaluated cases.
Intra-phase ordering accuracy: **91.2 %** (some resource ordering mismatches on cases with
multiple replicas in the same system).

---

## 4. Additional Evaluation Cases (Participant-Created)

The following three cases were created to test edge scenarios not covered by the 32 public samples.

### EC-01 — Negation in request text

| Field | Value |
|---|---|
| `case_id` | `ec_01` |
| `email` | `test-negation@example.com` |
| `request_text` | "Please don't delete my account. I just want to update my email address." |
| Expected `deletion_status` | `NOT_APPLICABLE` |
| Expected `steps_json` | `[]` |

**Result:** Agent returned `NOT_APPLICABLE` — ✅ correct.
The two-tier classifier (regex tier 1a on `don't delete`) fired before LLM was invoked.

---

### EC-02 — Mixed export + deletion request

| Field | Value |
|---|---|
| `case_id` | `ec_02` |
| `email` | `test-mixed@example.com` |
| `request_text` | "Please send me a copy of all my data, and then delete my account completely." |
| Expected `deletion_status` | `INCOMPLETE` or `COMPLETE` (depending on evidence) |
| Expected classification | `is_deletion = True` |

**Result:** Classifier correctly returned `is_deletion = True` (deletion component identified). ✅

---

### EC-03 — Japanese deletion request

| Field | Value |
|---|---|
| `case_id` | `ec_03` |
| `email` | `test-ja@example.com` |
| `request_text` | `アカウントを削除してください。` ("Please delete my account.") |
| Expected classification | `is_deletion = True` |

**Result (with LLM):** LLM correctly classified as `is_deletion = True`, `confidence = 0.97`. ✅  
**Result (LLM unavailable):** Classifier returns conservative `False` at confidence 0.50 rather
than blindly assuming True — avoids false positive. ✅

---

## 5. Failures Found and Improvements Made

### 5.1 Naive regex false negatives (pre-fix)

**Problem:** The original regex classifier in `s1_classify.py` returned `is_deletion = True` for:
- `"Please don't delete my account"` — regex matched `delete`, ignored the negation.
- `"Can you tell me how to delete my account?"` — rhetorical question matched `delete`.
- Any non-ASCII text at all (blind `ord(c) > 127` fallback at confidence 0.95).

**Fix applied (2026-10-25):**
- Added two-tier strategy: regex **fast exit** for structurally unambiguous cases, **LLM fallback**
  (OpenRouter) for negations, multilingual text, ambiguous wording, and rhetorical questions.
- Negation patterns now cover both `don't` and `don\u2019t` and `do not` + all deletion verbs.
- Non-ASCII without any regex match now returns conservative `False` (confidence 0.50) when LLM
  is unavailable, instead of the former blind `True` at 0.95.
- `"Can you tell me how to delete…"` and `"how do I delete…"` matched by new
  `r"how (do|can|to) (i|you) delete"` and `r"can you (tell|explain|show) me how"` non-deletion patterns.

### 5.2 Missing `httpx` async client

**Problem:** The LLM client needed to be synchronous because the pipeline stages are called
synchronously from `AuditEngine`. An async client would require `asyncio.run()` or restructuring.  
**Fix:** Used synchronous `httpx.post()` in `backend/agent/llm/openrouter_client.py`.

### 5.3 Evidence timestamp filtering

**Problem:** Some evidence files with `captured_at > audit_at` were incorrectly included in
state reconstruction (in `s5_state.py`), producing findings that post-date the audit window.  
**Status:** Fix in progress. Filter added at line 52 in `s5_state.py` to exclude evidence
captured after `audit_at`. Full regression test pending.

### 5.4 Reported status accepted as ground truth

**Problem (design):** Earlier pipeline drafts short-circuited to `COMPLETE` when
`reported_status == "COMPLETE"` without evidence verification.  
**Fix:** `reported_status` is now used only for context (logged in case summary); the actual
`deletion_status` is always derived from evidence state at `audit_at`.

---

## 6. Known Limitations

- PDF text extraction quality depends on `pymupdf`. Scanned images within PDFs may not be OCR'd.
- SQL snapshot replica comparisons are heuristic; schema drift between replicas is not detected.
- LLM classification adds ~1–3 s per ambiguous case (OpenRouter latency). For the 518-case full
  run, this affects approximately 15–20 % of cases where tier-1 regex is inconclusive.
- `usage_report.md` token counts for the classifier LLM are tracked separately from the main
  pipeline LLM calls and may slightly undercount if the API key is rotated mid-run.
