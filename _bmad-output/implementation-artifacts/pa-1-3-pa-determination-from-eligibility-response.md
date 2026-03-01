# Story PA-1.3: PA Determination from Eligibility Response

Status: done

## Story

As a **developer**,
I want to determine if prior authorization is required based on an eligibility response,
so that I can programmatically bridge the eligibility → PA workflow without manually interpreting 271 data.

## Acceptance Criteria

1. **Given** an `EligibilityResponse` (or dict) with `authOrCertIndicator: "Y"` in benefit information
   **When** I call `determine_pa_required(response)`
   **Then** a `PADeterminationResult` is returned with `required=True`, `confidence="high"`, and `reason` containing "authOrCertIndicator=Y"
   **And** `auth_or_cert_indicator` is `"Y"`

2. **Given** an eligibility response with `authOrCertIndicator: "N"`
   **When** I call `determine_pa_required(response)`
   **Then** `required=False`, `confidence="high"`, and `reason` indicates PA not required

3. **Given** an eligibility response with `authOrCertIndicator: "U"` or missing
   **When** I call `determine_pa_required(response)`
   **Then** `confidence="low"` and `reason` indicates the indicator is unknown/missing

4. **Given** an eligibility response with free-text `additionalInformation.description` containing "prior auth" or "precertification" or "preauthorization"
   **When** I call `determine_pa_required(response)`
   **Then** `required=True` with `confidence="medium"` and `free_text_indicators` contains the matched phrases

5. **Given** an eligibility response where `authOrCertIndicator="N"` but free-text says "prior authorization required"
   **When** I call `determine_pa_required(response)`
   **Then** `required=True` (free-text takes precedence per FR4)
   **And** `reason` explains the conflict resolution

6. **Given** a plain Python dict instead of an `EligibilityResponse` object
   **When** I call `determine_pa_required(dict_response)`
   **Then** it works via duck typing — no hard import of eligibility models required

7. **Given** `determine_pa_required()` execution
   **When** I measure performance
   **Then** it completes in under 10ms (NFR4)

8. **Given** a developer importing from the package
   **When** they write `from claim_validator import determine_pa_required`
   **Then** the import succeeds and the function is available at the top level

## Tasks / Subtasks

- [x] Task 1: Create `prior_auth/determination.py` with `determine_pa_required()` function (AC: #1, #2, #3, #5, #6)
  - [x]Accept `dict | Any` input via duck typing (no hard import of eligibility models)
  - [x]Extract `authOrCertIndicator` from `benefitsInformation[*].authOrCertIndicator`
  - [x]Map indicator: `"Y"` → required=True/confidence="high", `"N"` → required=False/confidence="high", `"U"` or missing → confidence="low"
  - [x]Implement conflict resolution: free-text overrides indicator when free-text says required (FR4)
  - [x]Return `PADeterminationResult` (already defined in `prior_auth/models/result.py`)
- [x] Task 2: Implement free-text scanning for PA indicators (AC: #4, #5)
  - [x]Scan `additionalInformation[*].description` fields for PA keywords
  - [x]Match patterns: "prior auth", "precertification", "preauthorization", "pre-certification", "pre-authorization" (case-insensitive)
  - [x]Populate `free_text_indicators` with matched phrases
  - [x]When free-text found: set `confidence="medium"` (unless indicator is "Y" which stays "high")
- [x] Task 3: Handle nested/varied 271 response structures (AC: #6)
  - [x]Support Stedi JSON format: `benefitsInformation[].authOrCertIndicator`
  - [x]Support nested `additionalInformation[].description` within benefit entries
  - [x]Gracefully handle missing keys (return `required=False`, `confidence="low"`, reason="No PA indicators found")
  - [x]Support both dict and object attribute access via duck typing helper
- [x] Task 4: Add `determine_pa_required` to re-exports (AC: #8)
  - [x]Add to `prior_auth/__init__.py` imports and `__all__`
  - [x]Add to top-level `claim_validator/__init__.py` imports and `__all__`
- [x] Task 5: Create comprehensive test suite (AC: #1-#8)
  - [x]`tests/test_prior_auth/test_determination.py`
  - [x]Tests for indicator "Y" → required=True, confidence="high"
  - [x]Tests for indicator "N" → required=False, confidence="high"
  - [x]Tests for indicator "U" → confidence="low"
  - [x]Tests for missing indicator → confidence="low"
  - [x]Tests for free-text matches (each keyword variant)
  - [x]Tests for conflict resolution: indicator="N" + free-text="prior auth required" → required=True
  - [x]Tests for indicator="Y" + free-text matches → required=True, confidence stays "high"
  - [x]Tests for dict input (duck typing)
  - [x]Tests for empty/malformed input (graceful fallback)
  - [x]Tests for nested benefit structures (multiple benefitsInformation entries)
  - [x]Performance test: execution < 10ms (AC: #7)
  - [x]Test case insensitivity of free-text matching

## Dev Notes

### Architecture Decisions

**D28: PA Determination (Cross-module bridge)** — [Source: architecture.md, lines 2063-2083]

- Function: `determine_pa_required(response: dict | Any) -> PADeterminationResult`
- Lives in: `prior_auth/determination.py` (new file)
- Uses duck typing — no hard import of eligibility models at module level
- Accepts both raw dict (Stedi JSON) and typed `EligibilityResponse` objects

### Determination Logic (from D28)

```
1. Extract authOrCertIndicator from benefit info → Y/N/U
   - "Y" → required=True, confidence="high"
   - "N" → required=False, confidence="high"
   - "U" or missing → required=False, confidence="low"
2. Scan free-text additionalInformation.description
   - Match PA indicators: "prior auth", "precertification", "preauthorization"
   - If found → required=True, confidence="medium", populate free_text_indicators
3. Conflict resolution (FR4):
   - If free-text says required AND indicator says "N" → required=True (free-text wins)
   - reason explains the conflict
4. Return PADeterminationResult(required, confidence, reason, auth_or_cert_indicator, free_text_indicators)
```

### 271 Response Format (Stedi JSON)

The input is a 271 eligibility response in Stedi JSON format. Key fields:

```json
{
  "benefitsInformation": [
    {
      "serviceTypeCodes": ["73"],
      "serviceTypes": ["MRI/CAT Scan"],
      "authOrCertIndicator": "Y",
      "additionalInformation": [
        {
          "description": "PRIOR AUTHORIZATION REQUIRED FOR MRI SERVICES"
        }
      ]
    }
  ]
}
```

[Source: research — domain-healthcare-prior-authorization-278-research-2026-02-27.md, Section 3.4]

### Existing Model (DO NOT recreate)

`PADeterminationResult` already exists in `src/claim_validator/prior_auth/models/result.py`:

```python
class PADeterminationResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)

    required: bool
    confidence: str                         # "high" / "medium" / "low"
    reason: str                             # human-readable explanation
    auth_or_cert_indicator: str | None = None  # raw Y/N/U from 271
    free_text_indicators: list[str] = []       # parsed free-text PA signals
```

This model was created in Story PA-1.1 and is already re-exported via `prior_auth/models/__init__.py`. Do NOT modify it.

### Duck Typing Pattern

The function must NOT import any eligibility module types. Access fields via:

```python
def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Get a field from dict or object attribute."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)
```

This allows `determine_pa_required()` to accept both:
- `dict` — raw Stedi JSON response
- `EligibilityResponse` — typed Pydantic model (if eligibility module is installed)
- Any object with matching attribute names

### Free-Text Matching Patterns

Case-insensitive substring matching on these patterns:
- `"prior auth"` (catches "prior authorization", "prior auth required")
- `"precertification"`
- `"preauthorization"`
- `"pre-certification"`
- `"pre-authorization"`

Search within `additionalInformation[*].description` fields across all `benefitsInformation` entries.

### Previous Story Learnings (PA-1.1 and PA-1.2)

From PA-1.1:
- All models use `ConfigDict(frozen=True, strict=False)` — do NOT change
- Re-exports go in `prior_auth/__init__.py` AND top-level `claim_validator/__init__.py`
- Keep `__all__` lists alphabetically sorted
- Use `from __future__ import annotations` on every file

From PA-1.2:
- Keep functions simple and stateless (single-responsibility)
- Normalize inputs (`.upper().strip()`) before comparison
- Return `None` (or appropriate default) for invalid/missing input — don't raise exceptions
- Test files need `from __future__ import annotations`
- Use conftest.py for shared fixtures

### Project Structure Notes

**New file to create:**

```
src/claim_validator/prior_auth/
└── determination.py    # determine_pa_required() function
```

**Existing files to modify:**

| File | Change |
|---|---|
| `src/claim_validator/prior_auth/__init__.py` | Add `determine_pa_required` to imports and `__all__` |
| `src/claim_validator/__init__.py` | Add `determine_pa_required` to imports and `__all__` |

**New test file:**

```
tests/test_prior_auth/
└── test_determination.py  # All determination tests
```

**Files NOT to touch:**
- `src/claim_validator/prior_auth/models/result.py` — `PADeterminationResult` already exists
- `src/claim_validator/prior_auth/models/__init__.py` — already re-exports `PADeterminationResult`
- `src/claim_validator/prior_auth/constants.py` — no new enums needed
- `src/claim_validator/conf.py` — no new settings needed
- `src/claim_validator/prior_auth/code_tables/` — not used by determination logic
- `pyproject.toml` — no new dependencies

### HIPAA Compliance

- `determine_pa_required()` reads structured fields only — no PHI in `authOrCertIndicator` or `serviceTypeCodes`
- Free-text `additionalInformation.description` is payer-generated text, not patient data
- Finding messages reference field names only, never actual values
- No logging of input data

### Performance (NFR4)

- Target: < 10ms for a single eligibility response
- Pure in-memory dict/attribute traversal — no I/O, no code table loading
- No regex needed — simple `str.lower()` + `in` substring matching is sufficient

### References

- [Source: architecture.md — D28: PA Determination (Cross-module bridge)]
- [Source: prd.md — FR2, FR3, FR4, FR5: PA determination requirements]
- [Source: research — domain-healthcare-prior-authorization-278-research-2026-02-27.md, Section 2.2, 3.4]
- [Source: epics.md — PA Epic 1, Story 1.3]
- [Source: project-context.md — PA module naming conventions, finding code prefixes]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- 1 ruff I001 import sorting issue in `claim_validator/__init__.py` — auto-fixed with `--fix` (lowercase `determine_pa_required` sorts after uppercase `PADeterminationResult` in ruff's ordering)

### Completion Notes List

- Created `prior_auth/determination.py` with `determine_pa_required()` function implementing architecture decision D28
- Duck typing via `_get_field()` helper — accepts both dict (Stedi JSON) and typed objects without importing eligibility models
- Three-step determination logic: (1) extract `authOrCertIndicator` Y/N/U, (2) scan free-text for PA keywords, (3) conflict resolution (FR4: free-text overrides indicator=N)
- Five PA keyword patterns matched case-insensitively: "prior auth", "precertification", "preauthorization", "pre-certification", "pre-authorization"
- Input normalization: indicator `.strip().upper()`, description `.lower()` for matching
- Graceful fallback for missing/malformed input: returns `required=False`, `confidence="low"`
- Re-exported `determine_pa_required` via `prior_auth/__init__.py` and top-level `claim_validator/__init__.py`
- 49 new tests across 9 test classes: TestIndicatorY (6), TestIndicatorN (4), TestIndicatorUnknown (7), TestFreeText (7), TestConflictResolution (4), TestDuckTyping (2), TestEdgeCases (14), TestPerformance (1), TestReExports (4)
- All 874 tests pass (49 new + 825 existing), zero regressions
- All ACs satisfied: AC1 (Y→required/high), AC2 (N→not required/high), AC3 (U/missing→low), AC4 (free-text→medium), AC5 (conflict resolution FR4), AC6 (duck typing), AC7 (performance <10ms), AC8 (top-level import)

### File List

**New files:**
- `src/claim_validator/prior_auth/determination.py`
- `tests/test_prior_auth/test_determination.py`

**Modified files:**
- `src/claim_validator/prior_auth/__init__.py` (added `determine_pa_required` to imports and `__all__`)
- `src/claim_validator/__init__.py` (added `determine_pa_required` to imports and `__all__`)

### Code Review Fixes

| # | Severity | Fix Applied |
|---|----------|-------------|
| 1 | HIGH | `_extract_indicator` changed from "first wins" to "most restrictive wins" (Y > U > N). Empty string indicator now treated as missing. |
| 2 | MEDIUM | Added `test_indicator_u_with_free_text_required` to TestIndicatorUnknown |
| 3 | MEDIUM | Added `test_none_response` to TestEdgeCases |
| 4 | LOW | Renamed `test_multiple_benefits_first_indicator_used` → `test_multiple_benefits_y_before_n`, added `test_multiple_benefits_n_before_y_most_restrictive_wins` |
| 5 | LOW | Empty string indicator handled in `_extract_indicator` (skip after strip), added `test_empty_string_indicator_treated_as_missing` |
| 6 | LOW | Added `test_unrecognized_indicator_value` for indicator="X" path |
