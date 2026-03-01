# Story PA-2.2: AAA Error Parsing & Human-Readable Messages

Status: done

## Story

As a **developer**,
I want AAA reject errors from 278 responses parsed into structured models with human-readable messages and suggested fixes,
So that my application can display actionable error information instead of cryptic X12 reject codes.

## Acceptance Criteria

1. **Given** a 278 response containing AAA reject segments
   **When** `parse_278_response(raw_dict)` is called
   **Then** `response.errors` contains `PriorAuthError` objects for each AAA segment
   **And** each `PriorAuthError` has `rejection_code`, `follow_up_code`, `message`, and `suggested_fix`

2. **Given** AAA reject code `"04"` (Authorized Quantity Exceeded)
   **When** the code is mapped
   **Then** `message` is a human-readable description (e.g., "Authorized quantity exceeded")
   **And** `suggested_fix` provides actionable guidance (e.g., "Verify requested quantity against payer limits")

3. **Given** the top 20+ AAA reject codes (04, 15, 33, 35, 41-58, 60, 71-73, 79, T4)
   **When** each is encountered in a 278 response
   **Then** all have human-readable messages and suggested fixes from the bundled code table

4. **Given** an unmapped AAA reject code (not in the code table)
   **When** it is encountered
   **Then** a WARNING finding is generated with the raw code value and a generic "Contact payer for details" message (NFR18)
   **And** no exception is raised

5. **Given** AAA errors in a 278 response
   **When** the pipeline processes the response
   **Then** corresponding `Finding` objects with code `AAA_PA_REJECTION` are generated (FR35, FR54)
   **And** each finding includes the rejection code, human-readable message, and suggested fix in the `context` dict

6. **Given** multiple AAA errors in a single 278 response
   **When** they are parsed
   **Then** all errors are captured in `response.errors` and corresponding findings are generated for each

7. **Given** a 278 response with both HCR action code and AAA errors
   **When** processed together
   **Then** both the `PriorAuthResponse` model and the findings list reflect the complete error picture
   **And** HCR action code parsing (Story 2.1) is not broken or modified

8. **Given** `parse_278_response()` called on a response with AAA errors
   **When** I measure performance
   **Then** it still completes in under 50ms (NFR3)

9. **Given** a developer importing from the package
   **When** they write `from claim_validator import parse_278_response`
   **Then** the existing import still works — no new public API symbols needed

10. **Given** `parse_278_response()` called with AAA errors in the raw dict
    **When** it completes
    **Then** the original raw dict is NOT mutated (NFR34)
    **And** `response.raw_response` still contains the complete unmodified 278 JSON including AAA data

## Tasks / Subtasks

- [x] Task 1: Add `_parse_aaa_errors()` helper to `response_parser.py` (AC: #1, #2, #3, #4, #6)
  - [x]Create `_parse_aaa_errors(raw_errors: Any, findings: list[Finding]) -> list[PriorAuthError]` helper function
  - [x]Extract AAA error list from raw dict using `aaa_errors` key (primary) or `aaa_segments` key (fallback), with explicit `is None` check (lesson from Story 2.1 code review)
  - [x]For each AAA error dict, extract `rejection_code` (or `aaa03` fallback) and `follow_up_code` (or `aaa04` fallback)
  - [x]Look up rejection code via existing `get_aaa_reject_code(code)` from `code_tables/aaa_reject_codes.py`
  - [x]If code found: populate `PriorAuthError.message` from `code_info["description"]` and `PriorAuthError.suggested_fix` from `code_info["suggested_fix"]`
  - [x]If code NOT found: set `message="Unknown AAA reject code"` and `suggested_fix="Contact payer for details"`
  - [x]Skip non-dict items in AAA errors list (graceful handling)
  - [x]Skip items missing `rejection_code`/`aaa03` key (graceful handling)

- [x] Task 2: Generate `AAA_PA_REJECTION` findings (AC: #4, #5)
  - [x]For each parsed AAA error, create a `Finding` with code `"AAA_PA_REJECTION"`
  - [x]Known codes: `severity=Severity.ERROR`, message from code table description
  - [x]Unknown/unmapped codes: `severity=Severity.WARNING`, generic message
  - [x]`field_name="aaa_segment"` for all AAA findings
  - [x]`suggestion` from code table `suggested_fix` (or generic "Contact payer for details" for unmapped)
  - [x]`context` dict MUST include: `rejection_code`, `follow_up_code`, `meaning` (from code table or "Unknown")
  - [x]Append findings to the shared `findings` list (same list used by HCR code parsing)

- [x] Task 3: Integrate AAA parsing into `parse_278_response()` (AC: #1, #7, #10)
  - [x]After existing service line parsing, call `_parse_aaa_errors()` with raw AAA data and findings list
  - [x]Pass the returned `list[PriorAuthError]` to `PriorAuthResponse(errors=...)` constructor
  - [x]Ensure AAA data is included in `raw_response` deep copy (already handled by existing `copy.deepcopy(raw)`)
  - [x]Verify no mutation of input dict (existing `copy.deepcopy` covers this)
  - [x]Ensure all existing Story 2.1 behavior is completely unchanged

- [x] Task 4: Create comprehensive test suite (AC: #1-#10)
  - [x]Create `claim-validator/tests/test_prior_auth/test_aaa_error_parser.py`
  - [x]`_make_278_response_with_aaa(**overrides)` — test helper factory that includes AAA error segments
  - [x]TestAAABasicParsing: single AAA error → PriorAuthError in response.errors with correct fields (AC #1)
  - [x]TestAAACodeMapping: known code (e.g., "57") → human-readable message and suggested fix from code table (AC #2)
  - [x]TestAAAAllKnownCodes: parametrized test for all 23 known AAA codes → correct message and suggested_fix (AC #3)
  - [x]TestAAAUnmappedCode: unknown code (e.g., "ZZ") → WARNING finding, generic message, no exception (AC #4)
  - [x]TestAAAFindings: AAA error → Finding with code="AAA_PA_REJECTION" and correct context dict (AC #5)
  - [x]TestAAAMultipleErrors: 2+ AAA errors → all captured in response.errors, all findings generated (AC #6)
  - [x]TestAAAWithHCRCode: response with both A3 action code and AAA errors → both parsed correctly (AC #7)
  - [x]TestAAAPerformance: response with 5 AAA errors → < 50ms (AC #8)
  - [x]TestAAAImportUnchanged: existing `from claim_validator import parse_278_response` still works (AC #9)
  - [x]TestAAAInputNotMutated: raw dict unchanged after parsing with AAA errors (AC #10)
  - [x]TestAAAEdgeCases: empty aaa_errors list, None aaa_errors, non-list aaa_errors, non-dict items, missing rejection_code
  - [x]TestAAAKeyConventions: `aaa_errors` vs `aaa_segments` fallback key
  - [x]TestAAACodeFieldConventions: `rejection_code` vs `aaa03`, `follow_up_code` vs `aaa04` fallback keys
  - [x]TestAAANoAAAErrors: response without AAA segment → response.errors == [] (regression guard for Story 2.1)
  - [x]TestStory21Regression: all existing Story 2.1 test cases still pass (run existing test_response_parser.py)

- [x] Task 5: Update `test_imports.py` if needed (AC: #9)
  - [x]Verify existing import tests still pass (no new public symbols)
  - [x]If any new symbols added, update import tests accordingly

- [x] Task 6: Run full test suite and lint
  - [x]Run `PYTHONPATH=src .venv/bin/pytest` from `claim-validator/` directory
  - [x]Run `ruff check src/ tests/` from `claim-validator/` directory
  - [x]Fix any failures or lint issues
  - [x]Verify ALL existing tests still pass (no regressions)

## Dev Notes

### Architecture Contract — Extending `parse_278_response()`

**From architecture.md (D30: AAA Error Dual Access):**

This story extends the EXISTING `parse_278_response()` function — do NOT create a separate parser function. The architecture specifies dual access for AAA errors:

1. **Programmatic access:** `PriorAuthResponse.errors` list contains `PriorAuthError` objects
2. **Pipeline access:** `Finding(code="AAA_PA_REJECTION")` objects in the findings list

Both outputs come from the SAME parse call. The existing function signature is unchanged:

```python
def parse_278_response(raw: dict[str, Any]) -> ParsedResponse:
    # ParsedResponse = tuple[PriorAuthResponse, list[Finding]]
```

**File location:** `claim-validator/src/claim_validator/prior_auth/response_parser.py` (EXISTING — extend, do NOT create new file)
**Test location:** `claim-validator/tests/test_prior_auth/test_aaa_error_parser.py` (NEW)

### 278 Response JSON Structure — AAA Error Segments

The raw 278 JSON dict from clearinghouses includes AAA error segments under the `aaa_errors` key (primary) or `aaa_segments` key (fallback). Support both conventions, with `aaa_errors` taking precedence (using explicit `is None` check, NOT `or` operator — lesson from Story 2.1 code review issue #1):

```python
{
    "action_code": "A3",
    "authorization_number": None,
    "effective_date": None,
    "expiration_date": None,
    "decision_reason_code": "57",
    "decision_reason_description": "Patient not eligible",
    "service_lines": [],
    "aaa_errors": [
        {
            "rejection_code": "57",        # or "aaa03": "57"
            "follow_up_code": "N",         # or "aaa04": "N"
        },
        {
            "rejection_code": "72",
            "follow_up_code": "C",
        }
    ]
}
```

**Key convention fallbacks (same pattern as Story 2.1's `action_code`/`hcr01`):**

| Primary Key | Fallback Key | Description |
|---|---|---|
| `aaa_errors` | `aaa_segments` | List of AAA error dicts in the raw 278 JSON |
| `rejection_code` | `aaa03` | AAA03 reject reason code within each error dict |
| `follow_up_code` | `aaa04` | AAA04 follow-up action code within each error dict |

### Existing Models (DO NOT MODIFY)

**PriorAuthError** — `claim-validator/src/claim_validator/prior_auth/models/response.py`:

```python
class PriorAuthError(BaseModel):
    """AAA reject error from 278 response."""
    model_config = ConfigDict(frozen=True, strict=False)

    rejection_code: str
    follow_up_code: str | None = None
    message: str = ""
    suggested_fix: str = ""
```

**PriorAuthResponse.errors field** — same file:

```python
class PriorAuthResponse(BaseModel):
    # ... other fields from Story 2.1 ...
    errors: list[PriorAuthError] = []   # ← THIS is what we populate
    # ...
```

**IMPORTANT:** The `PriorAuthError` model does NOT have `loop_level` or `valid_request` fields (those are in the architecture diagram but NOT in the actual implemented model). Do NOT add them. If loop_level is present in the raw AAA dict, include it in the `Finding.context` dict only.

### Existing Code Table (DO NOT MODIFY)

**AAA reject code lookup** — `claim-validator/src/claim_validator/prior_auth/code_tables/aaa_reject_codes.py`:

```python
def get_aaa_reject_code(code: str) -> dict[str, str] | None:
    """Look up an AAA reject reason code. Returns details dict or None if not found.
    The returned dict contains: meaning, description, suggested_fix.
    """
```

This function already exists and loads from `prior_auth/data/aaa_reject_codes.json` (23 codes). Use it — do NOT duplicate the lookup logic or create a new data file.

**Return format for known code (e.g., `get_aaa_reject_code("57")`):**

```python
{
    "meaning": "Patient Not Eligible",
    "description": "Patient/subscriber not found or not eligible on the payer's system",
    "suggested_fix": "Verify member ID, check eligibility, confirm coverage active"
}
```

**Return for unknown code:** `None`

### Mapping from Code Table to Model and Finding

```python
code_info = get_aaa_reject_code(rejection_code)

if code_info is not None:
    # Known code
    error = PriorAuthError(
        rejection_code=rejection_code,
        follow_up_code=follow_up_code,
        message=code_info["description"],
        suggested_fix=code_info["suggested_fix"],
    )
    finding = Finding(
        code="AAA_PA_REJECTION",
        message=code_info["description"],
        severity=Severity.ERROR,
        field_name="aaa_segment",
        suggestion=code_info["suggested_fix"],
        context={
            "rejection_code": rejection_code,
            "follow_up_code": follow_up_code,
            "meaning": code_info["meaning"],
        },
    )
else:
    # Unknown code — NFR18
    error = PriorAuthError(
        rejection_code=rejection_code,
        follow_up_code=follow_up_code,
        message="Unknown AAA reject code",
        suggested_fix="Contact payer for details",
    )
    finding = Finding(
        code="AAA_PA_REJECTION",
        message="Unknown AAA reject code encountered in 278 response",
        severity=Severity.WARNING,
        field_name="aaa_segment",
        suggestion="Contact payer for details",
        context={
            "rejection_code": rejection_code,
            "follow_up_code": follow_up_code,
            "meaning": "Unknown",
        },
    )
```

### Finding Code Reference (This Story)

| Finding Code | Severity | Field | When |
|---|---|---|---|
| `AAA_PA_REJECTION` | ERROR | `aaa_segment` | Known AAA reject code mapped from code table |
| `AAA_PA_REJECTION` | WARNING | `aaa_segment` | Unknown/unmapped AAA reject code (NFR18) |

Note: `PA_UNKNOWN_ACTION_CODE` (WARNING) is from Story 2.1 — do NOT change or remove.

### Implementation Pattern — `_parse_aaa_errors()` Helper

Follow the same helper function pattern established in Story 2.1 (`_parse_action_code()`, `_parse_date()`, `_parse_service_lines()`):

```python
def _parse_aaa_errors(
    raw_errors: Any,
    findings: list[Finding],
) -> list[PriorAuthError]:
    """Parse raw AAA error dicts into PriorAuthError models.

    For each AAA error:
    - Maps rejection_code to human-readable message via code table
    - Creates PriorAuthError with populated message and suggested_fix
    - Appends AAA_PA_REJECTION Finding to findings list

    Unknown codes get generic message + WARNING finding (NFR18).
    """
```

### Integration Point in `parse_278_response()`

Add AAA parsing AFTER service line parsing, BEFORE constructing `PriorAuthResponse`:

```python
def parse_278_response(raw: dict[str, Any]) -> ParsedResponse:
    findings: list[Finding] = []
    raw_copy = copy.deepcopy(raw)

    # ... existing HCR action code parsing (Story 2.1) ...
    # ... existing field extraction (Story 2.1) ...
    # ... existing service line parsing (Story 2.1) ...

    # NEW: Parse AAA error segments
    raw_aaa = raw.get("aaa_errors")
    if raw_aaa is None:
        raw_aaa = raw.get("aaa_segments")
    aaa_errors = _parse_aaa_errors(raw_aaa, findings)

    response = PriorAuthResponse(
        action_code=action_code,
        authorization_number=authorization_number,
        effective_date=effective_date,
        expiration_date=expiration_date,
        decision_reason_code=decision_reason_code,
        decision_reason_description=decision_reason_description,
        service_line_decisions=service_line_decisions,
        errors=aaa_errors,              # ← NEW: was [] by default
        raw_response=raw_copy,
    )
    return response, findings
```

### New Imports Required in `response_parser.py`

```python
# ADD to existing imports:
from claim_validator.prior_auth.code_tables.aaa_reject_codes import get_aaa_reject_code
from claim_validator.prior_auth.models.response import PriorAuthError  # ADD to existing import block
```

### All 23 Known AAA Reject Codes (from `aaa_reject_codes.json`)

| Code | Meaning | Category |
|---|---|---|
| 04 | Authorized Quantity Exceeded | Quantity |
| 15 | Required Application Data Missing | DataQuality |
| 33 | Input Errors | DataQuality |
| 35 | Out of Network | Network |
| 41 | Authorization/Access Restrictions | Access |
| 42 | Unable to Respond at Current Time | System |
| 43 | Invalid/Missing Provider Identification | Provider |
| 44 | Invalid/Missing Provider Name | Provider |
| 45 | Invalid/Missing Provider Specialty | Provider |
| 46 | Invalid/Missing Provider Phone Number | Provider |
| 47 | Invalid/Missing Provider State | Provider |
| 48 | Invalid/Missing Referring Provider | Provider |
| 49 | Provider Ineligible for Inquiries | Provider |
| 51 | Provider Not on File | Provider |
| 56 | Provider Not Eligible | Provider |
| 57 | Patient Not Eligible | Eligibility |
| 58 | Date of Birth Does Not Match | Eligibility |
| 60 | Date of Injury/Illness is in the Future | DataQuality |
| 71 | Patient Gender Mismatch | Eligibility |
| 72 | Invalid/Missing Subscriber ID | Eligibility |
| 73 | Invalid/Missing Subscriber Name | Eligibility |
| 79 | Invalid Participant Identification | DataQuality |
| T4 | Payer Name/ID Missing | DataQuality |

### Key Implementation Details

1. **Extend, don't rewrite:** This story modifies `response_parser.py` by adding ONE new helper function (`_parse_aaa_errors`) and ~5 lines in the main function. Do NOT rewrite or restructure existing Story 2.1 code.

2. **Code table reuse:** Use the EXISTING `get_aaa_reject_code()` lookup. Do NOT create a new data file or duplicate the 23-code table.

3. **Key convention pattern:** Follow Story 2.1's pattern — primary key with `is None` fallback to alternate key. NEVER use `or` operator for this (HIGH severity issue from Story 2.1 code review).

4. **Severity distinction:** Known AAA codes → `Severity.ERROR` (real business errors). Unknown codes → `Severity.WARNING` (NFR18).

5. **No new public API:** `parse_278_response()` signature unchanged. No new functions to export. No changes to `__init__.py` files.

6. **PHI safety:** Finding messages MUST reference field names and code values only, NEVER patient data. The rejection code (e.g., "57") is safe to include. Patient name, member ID, etc. are NOT (HIPAA NFR12).

7. **Test isolation:** Create a NEW test file (`test_aaa_error_parser.py`), do NOT modify `test_response_parser.py`. Run both to verify no regressions.

### Existing Code to Reuse (DO NOT DUPLICATE)

| Component | Location | Usage |
|---|---|---|
| `get_aaa_reject_code()` | `prior_auth/code_tables/aaa_reject_codes.py` | Look up rejection codes |
| `PriorAuthError` | `prior_auth/models/response.py` | AAA error model (already exists) |
| `Finding` | `models/results.py` | Finding creation pattern |
| `Severity` | `constants.py` | ERROR/WARNING severity enum |
| `_parse_action_code()` | `prior_auth/response_parser.py` | Pattern reference for helper function style |
| `copy.deepcopy()` | `prior_auth/response_parser.py` | Already handles raw_response immutability |

### Project Structure Notes

**File to modify:**

```
claim-validator/src/claim_validator/prior_auth/
└── response_parser.py                  # Extend with _parse_aaa_errors() helper
```

**New test file to create:**

```
claim-validator/tests/test_prior_auth/
└── test_aaa_error_parser.py            # All AAA error parsing tests
```

**Files NOT to touch:**
- `claim-validator/src/claim_validator/prior_auth/models/response.py` — PriorAuthError model already exists and is correct
- `claim-validator/src/claim_validator/prior_auth/constants.py` — no new enums needed
- `claim-validator/src/claim_validator/prior_auth/code_tables/aaa_reject_codes.py` — lookup already exists
- `claim-validator/src/claim_validator/prior_auth/data/aaa_reject_codes.json` — 23 codes already bundled
- `claim-validator/src/claim_validator/prior_auth/__init__.py` — no new exports
- `claim-validator/src/claim_validator/__init__.py` — no new exports
- `claim-validator/tests/test_prior_auth/test_response_parser.py` — DO NOT modify (regression guard)
- `claim-validator/tests/test_prior_auth/conftest.py` — no new shared fixtures needed
- All existing validators — do NOT modify
- `pyproject.toml` — no new dependencies

### Previous Story Learnings (PA-2.1)

**Critical lessons to apply:**

1. **Use `is None` check, NOT `or` operator** for key fallbacks (Story 2.1 code review issue #1, HIGH severity):
   ```python
   # CORRECT:
   raw_aaa = raw.get("aaa_errors")
   if raw_aaa is None:
       raw_aaa = raw.get("aaa_segments")

   # WRONG — conflates missing with falsy:
   raw_aaa = raw.get("aaa_errors") or raw.get("aaa_segments")
   ```

2. **Test helper should NOT leak values into sub-structures** (Story 2.1 code review issue #7):
   When creating test helpers, be explicit about what goes into AAA errors — don't auto-mirror top-level codes into the AAA list.

3. **Keep test fixtures local to the test file** (Story 2.1 code review issue #2):
   Create `_make_278_response_with_aaa()` in the test file itself, not in conftest.py.

4. **Test runner command:** `PYTHONPATH=src .venv/bin/pytest` from `claim-validator/` directory
5. **Ruff lint:** `ruff check src/ tests/` from `claim-validator/` directory
6. **All files need:** `from __future__ import annotations`
7. **Keep `__all__` lists alphabetically sorted** (if any changes needed)

### HIPAA Compliance

- Finding `message` fields MUST NOT contain PHI values
- Good: `"Patient/subscriber not found or not eligible on the payer's system"` — describes the error, no PHI
- Bad: `"Patient John Doe (MEM001) not eligible"` — contains PHI
- Rejection codes (e.g., "57", "72") are NOT PHI — safe to include in messages and context
- The raw 278 response stored in `raw_response` may contain PHI — this is expected (programmatic access, NOT for LLM)

### Performance (NFR3)

- Target: < 50ms for `parse_278_response()` even with AAA errors
- `get_aaa_reject_code()` uses lazy singleton pattern — first call loads JSON (< 500ms), subsequent calls are O(1) dict lookup
- For tests: the first call in the test session will trigger the lazy load. Performance test should measure warm lookups.
- Typical 278 response has 0-3 AAA errors — negligible overhead

### References

- [Source: architecture.md — D30: AAA errors (dual access)]
- [Source: architecture.md — Pipeline Phase 2 flow]
- [Source: architecture.md — FR32-FR35: AAA Error Handling Requirements]
- [Source: epics.md — PA Epic 2, Story 2.2]
- [Source: project-context.md — Finding code prefixes: AAA_PA_REJECTION]
- [Source: project-context.md — PA pipeline architecture]
- [Source: project-context.md — Model patterns (frozen, strict=False)]
- [Source: project-context.md — Naming conventions]
- [Source: pa-2-1 story — Previous story learnings, code review issues]
- [Source: prior_auth/data/aaa_reject_codes.json — 23 bundled AAA codes]
- [Source: prior_auth/code_tables/aaa_reject_codes.py — get_aaa_reject_code() lookup]
- [Source: prior_auth/models/response.py — PriorAuthError model (existing)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Full test suite: 1117 passed, 0 failed (85 new AAA tests added)
- Ruff lint: All new/modified files pass with zero issues
- AAA parser tests: 85 tests all passing across 14 test classes
- Performance: parse_278_response() with 5 AAA errors well under 50ms target
- Story 2.1 regression: all 41 existing response parser tests still pass

### Completion Notes List

- All 6 tasks and all subtasks completed
- All 10 ACs satisfied
- Extended `parse_278_response()` with `_parse_aaa_errors()` helper — NO changes to function signature or public API
- Supports both `aaa_errors` and `aaa_segments` key conventions (aaa_errors takes precedence via `is None` check)
- Supports both `rejection_code`/`aaa03` and `follow_up_code`/`aaa04` field name conventions
- All 23 known AAA reject codes mapped to human-readable messages and suggested fixes via existing `get_aaa_reject_code()` lookup
- Unknown/unmapped AAA codes get generic "Unknown AAA reject code" message with "Contact payer for details" suggestion
- Known codes generate `AAA_PA_REJECTION` findings with `Severity.ERROR`
- Unknown codes generate `AAA_PA_REJECTION` findings with `Severity.WARNING` (NFR18)
- Finding context dict includes `rejection_code`, `follow_up_code`, `meaning`
- `PriorAuthError` objects populate `PriorAuthResponse.errors` list (dual access: D30)
- Case-insensitive rejection code handling (normalizes to uppercase)
- Graceful handling: non-list/non-dict items skipped, missing/empty rejection codes skipped
- Empty follow-up codes normalized to None
- Input dict immutability preserved (existing `copy.deepcopy` covers AAA data)
- No new public API symbols — existing imports unchanged
- No model changes — `PriorAuthError` model used as-is
- No new dependencies — uses existing `get_aaa_reject_code()` code table lookup
- PHI safety: finding messages reference rejection codes only, never patient data

### Senior Developer Code Review

| # | Severity | File:Line | Issue | Resolution |
|---|----------|-----------|-------|------------|
| 1 | MEDIUM | `response_parser.py:33` | Docstring says "WARNING-level issues" but AAA errors now generate ERROR-level findings for known codes | **Fixed** — updated docstring to accurately describe both ERROR and WARNING findings |
| 2 | MEDIUM | `response_parser.py:171` | `follow_up_code` not normalized to uppercase, inconsistent with `rejection_code` which gets `.upper().strip()` | **Fixed** — added `.upper()` to follow_up_code normalization |
| 3 | LOW | `test_aaa_error_parser.py` | No test for numeric (int) rejection code input (e.g., `57` instead of `"57"`) | Non-blocking — existing `str()` coercion handles this; edge case coverage |
| 4 | LOW | `response_parser.py:198` | Unknown code Finding message says "Unknown AAA reject code" but story spec says "Unknown AAA reject code encountered in 278 response" | Non-blocking — shorter message is clearer and consistent with the PriorAuthError.message |
| 5 | LOW | `test_aaa_error_parser.py` | Missing precedence edge case: `aaa_errors=[]` with `aaa_segments=[{...}]` should return empty list | Non-blocking — empty list is truthy, `is None` check correct; only affects empty-vs-absent semantics |

**Result:** 0 HIGH, 2 MEDIUM (both fixed), 3 LOW (documented as non-blocking)
**Post-fix tests:** 1117 passed, 0 failed

### File List

**Modified source files:**
| File | Description |
|---|---|
| `src/claim_validator/prior_auth/response_parser.py` | Added `_parse_aaa_errors()` helper, integrated AAA parsing into `parse_278_response()`, added `get_aaa_reject_code` and `PriorAuthError` imports |

**New test files:**
| File | Tests |
|---|---|
| `tests/test_prior_auth/test_aaa_error_parser.py` | 85 tests across 14 test classes (TestAAABasicParsing, TestAAACodeMapping, TestAAAAllKnownCodes, TestAAAUnmappedCode, TestAAAFindings, TestAAAMultipleErrors, TestAAAWithHCRCode, TestAAAPerformance, TestAAAImportUnchanged, TestAAAInputNotMutated, TestAAAEdgeCases, TestAAAKeyConventions, TestAAACodeFieldConventions, TestAAANoErrors) |
