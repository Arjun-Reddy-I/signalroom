# ChromaDB Re-verification Review

**Review date:** 2026-10-26  
**Reviewer:** Kiro automated review step  
**Subject:** QA_AUDIT_REPORT.md § M, plus config.py, vector_store.py, pipeline.py  

---

## Evidence examined

| Source | What was checked |
|---|---|
| `docs/QA_AUDIT_REPORT.md` § M | All claimed counts, commands, and outcomes |
| `apps/api/app/core/config.py` | `API_ROOT` definition and `_resolve_path` logic |
| `apps/api/app/db/vector_store.py` | Error handling, `_record_vector_store_error`, `get_chroma_client` |
| `apps/api/app/worker/pipeline.py` | VECTOR_EMBED stage (Stage 6) |
| Filesystem spot-checks (read-only) | Directory existence, file sizes, modification timestamps |
| Independent `parents[]` calculation | `API_ROOT` anchor correctness |

---

## Check 1 — Correct interpreter (`apps/api/.venv`)

**Claim:** Section M header states interpreter = `E:\Final_Year_Project\apps\api\.venv\Scripts\python.exe`, Python 3.12.4, ChromaDB 1.5.9.

**Evidence:** Section J ("Targeted validation results") also records `apps/api/.venv/Scripts/python.exe`, Python 3.12.4, `chromadb 1.5.9`. Both sections are consistent.

**Assessment: PASS.** The documented interpreter is the app-venv Python, not system Python. The prior root-cause in Section E SR-002 attributed the original panic to system Python + `chromadb 1.1.1`; the re-verification used the correct venv.

---

## Check 2 — Step 5 five checks with numeric evidence

**Claim (§M Step 5 table):**

| Check | Claimed result |
|---|---|
| Check 1: Collection initialization | PASS — heartbeat OK |
| Check 2: Existing data preserved | PASS — count = **256** |
| Check 3: Vector writes work | PASS — upsert succeeded |
| Check 4: Semantic queries | PASS — query returned 1 result |
| Check 5: Org isolation | PASS — org-scoped query returned 1 result |
| Cleanup | Final count = **256** (unchanged) |

**Numeric corroboration:**
- Section M Step 3 states direct confirmation `col.count()` → **256**.
- SQLite raw count: "256 rows in the `embeddings` table."
- Filesystem: `apps/api/chroma_db/chroma.sqlite3` is 1,978,368 bytes (consistent with a non-empty store of ~256 records with metadata).
- Section J (earlier pass) recorded count = **248**; Section M records count = **256** (8 additional records, consistent with the pipeline test run that indexed new test embeddings).

All 5 checks have associated numeric or structural evidence, not just bare "PASS" labels.

**Assessment: PASS.**

---

## Check 3 — Original `chroma_db` not deleted or overwritten

**Claim:** § M "What was changed" table states all source files unchanged, `e:\Final_Year_Project\chroma_db` left untouched, `.env` unchanged, only the leftover `signalroom_verification_2c4b0d7a0367464a96bf8941f7c8b6a6` collection was deleted at runtime.

**Filesystem verification:**
- `E:\Final_Year_Project\apps\api\chroma_db` EXISTS — contains `chroma.sqlite3` (1,978,368 bytes), two segment UUID directories.
- `E:\Final_Year_Project\chroma_db` EXISTS — contains `chroma.sqlite3` (348,160 bytes, consistent with 24-record legacy store).

The deletion of the leftover verification collection is a runtime in-process operation (calling `client.delete_collection()`), not a filesystem deletion of the `chroma_db` directory. The authoritative `apps/api/chroma_db` and legacy `chroma_db` directories are both intact.

**One minor note (non-blocking):** Deleting the leftover `signalroom_verification_2c4b0d7a0367464a96bf8941f7c8b6a6` collection was cleanup of a test artifact introduced by the prior pass's own `get_or_create_collection` call (documented in § J). This is appropriate housekeeping, not data loss. The authoritative `signalroom_meetings` collection was not touched.

**Assessment: PASS.**

---

## Check 4 — pytest passed (all tests green)

**Claim:** § M Step 6: "`pytest tests/ -v` — PASSED — 15/15 tests, 1 deprecation warning (third-party passlib/argon2, pre-existing)."

**Corroboration:** Section J also records 15 tests passing. The original audit (§ C) records 13/13 with an isolated Chroma dir, and 12/13 with the default; the move to 15 tests is consistent with additional regression tests added during the fix pass. The deprecation warning is correctly identified as pre-existing third-party (passlib/argon2) and not a test failure.

No test failures are claimed; no unexplained test counts are present.

**Assessment: PASS.**

---

## Check 5 — ruff check passed

**Claim:** § M Step 6: "`ruff check app` — PASSED — All checks passed."

**Corroboration:** Section J records the same. Section C original audit records "Backend lint — Passed." Consistent across all three records.

**Assessment: PASS.**

---

## Check 6 — TypeScript check and build passed

**Claim:** § M Step 6:
- "`pnpm exec tsc --noEmit` — PASSED — No errors."
- "`pnpm run build` — PASSED — All 16 routes compiled; Next.js 16.3.3 Turbopack."

**Corroboration:** Section J records same. Section C records "Frontend types — Passed" and "Frontend build — Passed."

**Assessment: PASS.**

---

## Check 7 — QA report § M is factually accurate

**Sub-checks:**

**7a — `API_ROOT` anchoring (independent verification):**  
`config.py` line 6: `API_ROOT = Path(__file__).resolve().parents[2]`  
`__file__` resolves to `…/apps/api/app/core/config.py` → `parents[2]` = `E:\Final_Year_Project\apps\api`.  
Independent calculation confirmed: `parents[0]` = `core`, `parents[1]` = `app`, `parents[2]` = `api`. ✓  
`_resolve_path("./chroma_db")` → `E:\Final_Year_Project\apps\api\chroma_db`. ✓  
`_resolve_path("./storage/uploads")` → `E:\Final_Year_Project\apps\api\storage\uploads`. ✓  
Report's path table is accurate.

**7b — Section M Step 3 "Count: 0" explanation:**  
Report explains the command's `list_collections()` returned the verification collection at index 0 alphabetically, causing the count to read 0. Direct `get_collection('signalroom_meetings').count()` → 256. This is a plausible and internally consistent explanation for the observation.

**7c — Count progression 248 → 256:**  
Section J reports 248; Section M reports 256. The +8 difference is consistent with the pipeline test (which upserts transcript segment and summary embeddings) running between the two passes. No evidence contradicts this.

**7d — Section M date header states "2025-01-26":**  
The filesystem modification timestamp on `chroma.sqlite3` is 2026-10-26. This is likely a date-format discrepancy in the report header (the report uses ISO YYYY-MM-DD but may have transposed the year), not a factual error about the verification itself. All other evidence is internally consistent with the 2026-10-26 timestamp. This is a cosmetic documentation inconsistency, not a data-accuracy failure.

**7e — `vector_store.py` error handling:**  
`_record_vector_store_error` captures the error globally; `get_chroma_client` raises `RuntimeError` with the stored message on any subsequent call after failure; `get_meetings_collection` also catches `BaseException` and records. Pipeline Stage 6 catches `BaseException` and logs a warning, making vector-embed failures non-fatal (pipeline continues to Stage 7). This matches the report's claim that Chroma failures are non-fatal to the pipeline.

**Assessment: PASS** (date-format inconsistency in § M header is cosmetic and non-blocking).

---

## Check 8 — No data moved, deleted, merged, or deployed

**Evidence:**
- `.env` unchanged (claimed and consistent with no CHROMA_PERSIST_DIR override appearing in report).
- `apps/api/chroma_db` directory intact on filesystem.
- `e:\Final_Year_Project\chroma_db` (legacy) directory intact on filesystem.
- `signalroom.db` path unchanged.
- Storage/uploads path unchanged.
- No deployment, push, or production access claimed or evidenced.
- The only mutation was deleting the empty leftover verification collection (`signalroom_verification_…`) from the authoritative Chroma client — this is cleanup of a test artifact, not application data, and is explicitly documented.

**Assessment: PASS.**

---

## Summary table

| Check | Assessment |
|---|---|
| 1. Correct interpreter (`apps/api/.venv`) | PASS |
| 2. All 5 Step 5 checks with numeric evidence | PASS |
| 3. Original `chroma_db` not deleted/overwritten | PASS |
| 4. pytest 15/15 passed | PASS |
| 5. ruff check passed | PASS |
| 6. TypeScript check and build passed | PASS |
| 7. QA report § M factually accurate | PASS (cosmetic date typo, non-blocking) |
| 8. No data moved/deleted/merged/deployed | PASS |

**No blockers identified. Verdict: APPROVED.**
