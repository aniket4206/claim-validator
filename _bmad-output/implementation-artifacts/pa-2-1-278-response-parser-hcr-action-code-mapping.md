# Story PA-2.1: 278 Response Parser & HCR Action Code Mapping

Status: done

## Story

As a **developer**,
I want to parse raw 278 JSON responses into structured Pydantic models with HCR action codes mapped to human-readable decisions,
So that I can programmatically determine authorization status without reading the X12 278 specification.

## Acceptance Criteria

1. **Given** a raw 278 JSON dict from a clearinghouse with HCR01=A1 (approved)
   **When** `parse_278_response(raw_dict)` is called
   **Then** a `PriorAuthResponse` is returned with `action_code=CertificationActionCode.A1`, `is_approved=True`, `is_denied=False`, `is_pended=False`
   **And** `authorization_number` contains the extracted auth number
   **And** `effective_date` and `expiration_date` are populated

2. **Given** a 278 response with HCR01=A3 (denied)
   **When** `parse_278_response(raw_dict)` is called
   **Then** `is_denied=True`, `is_approved=False`
   **And** `decision_reason_code` and `decision_reason_description` are populated

3. **Given** a 278 response with HCR01=A4 (pended)
   **When** `parse_278_response(raw_dict)` is called
   **Then** `is_pended=True`, `is_approved=False`, `is_denied=False`

4. **Given** a 278 response with HCR01=A2 (partial approval)
   **When** `parse_278_response(raw_dict)` is called
   **Then** `action_code=CertificationActionCode.A2`
   **And** per-service-line decisions show which services were approved vs denied

5. **Given** a 278 response with per-service-line authorization decisions
   **When** I inspect `response.service_line_decisions`
   **Then** each `ServiceLineDecision` contains `cpt_code`, `action_code`, `authorization_number`, `approved_quantity`, and `denied_reason`

6. **Given** all 7 HCR action codes (A1, A2, A3, A4, A6, CT, NA)
   **When** each is processed by `parse_278_response()`
   **Then** the correct `CertificationActionCode` enum value is set
   **And** the correct convenience property returns `True` (`is_approved` for A1, `is_denied` for A3, etc.)

7. **Given** a 278 response with missing or unexpected fields
   **When** `parse_278_response(raw_dict)` is called
   **Then** missing fields return `None` (not exception) (FR31, NFR16)
   **And** unexpected fields are silently ignored

8. **Given** an unmapped HCR action code (future code not in enum)
   **When** `parse_278_response()` encounters it
   **Then** a WARNING finding is generated with the raw code value (NFR17)
   **And** no exception is raised

9. **Given** any `PriorAuthResponse`
   **When** I access `response.raw_response`
   **Then** the complete unmodified 278 JSON dict is available

10. **Given** the response parser
    **When** I verify it does not modify the input dict
    **Then** the original `raw_dict` is unchanged after parsing (NFR34)

11. **Given** `parse_278_response()` execution on a typical response
    **When** I measure performance
    **Then** it completes in under 50ms (NFR3)

12. **Given** a developer importing from the package
    **When** they write `from claim_validator import parse_278_response`
    **Then** the import succeeds and the function is available at the top level

## Tasks / Subtasks

- [x]Task 1: Create `parse_278_response()` in `prior_auth/response_parser.py` (AC: #1, #2, #3, #4, #6, #7, #8, #9, #10)
  - [x]Create `claim-validator/src/claim_validator/prior_auth/response_parser.py`
  - [x]Implement `parse_278_response(raw: dict) -> PriorAuthResponse` as a pure function
  - [x]Extract top-level HCR action code from `raw["action_code"]` or `raw["hcr01"]` (support both key conventions)
  - [x]Map action code string to `CertificationActionCode` enum via safe lookup
  - [x]Extract `authorization_number`, `effective_date`, `expiration_date` from top-level fields
  - [x]Extract `decision_reason_code` and `decision_reason_description` for denied/modified responses
  - [x]Parse `service_line_decisions` from raw `"service_lines"` list into `ServiceLineDecision` models
  - [x]Store the original unmodified dict in `raw_response` field
  - [x]Return a tuple `(PriorAuthResponse, list[Finding])` — the response model + any WARNING findings
  - [x]For unmapped HCR codes: return `action_code=None` + `Finding(code="PA_UNKNOWN_ACTION_CODE", severity=WARNING)`
  - [x]MUST NOT modify the input dict (copy.deepcopy for raw_response storage)
  - [x]MUST NOT make network calls
  - [x]Missing fields → `None` on the model, never raise exceptions
  - [x]Unexpected/extra keys in raw dict → silently ignored

- [x]Task 2: Create `ParsedResponse` helper type (AC: #8)
  - [x]Define `ParsedResponse = tuple[PriorAuthResponse, list[Finding]]` type alias in `response_parser.py`
  - [x]The tuple pattern lets the pipeline collect WARNING findings from parsing alongside the structured response

- [x]Task 3: Create 278 response test fixtures (AC: #1-#6)
  - [x]Create `claim-validator/tests/test_prior_auth/fixtures/` directory
  - [x]Create fixture factory functions in `claim-validator/tests/test_prior_auth/conftest.py` (or use existing conftest)
  - [x]`make_278_response(action_code="A1", **overrides) -> dict` — builds a realistic raw 278 JSON dict
  - [x]Fixture for A1 (approved) — includes authorization_number, effective_date, expiration_date
  - [x]Fixture for A3 (denied) — includes decision_reason_code, decision_reason_description
  - [x]Fixture for A4 (pended)
  - [x]Fixture for A2 (partial) — includes service_line_decisions with mixed approve/deny
  - [x]Fixture for A6 (modified)
  - [x]Fixture for CT (contact payer)
  - [x]Fixture for NA (no action required)
  - [x]Fixture with missing fields (minimal dict)
  - [x]Fixture with extra unexpected fields

- [x]Task 4: Create `test_response_parser.py` tests (AC: #1-#11)
  - [x]Create `claim-validator/tests/test_prior_auth/test_response_parser.py`
  - [x]TestParseApproved: A1 → `is_approved=True`, auth number, dates populated (AC #1)
  - [x]TestParseDenied: A3 → `is_denied=True`, reason code/description populated (AC #2)
  - [x]TestParsePended: A4 → `is_pended=True`, not approved, not denied (AC #3)
  - [x]TestParsePartial: A2 → service_line_decisions with mixed action codes (AC #4)
  - [x]TestServiceLineDecisions: each has cpt_code, action_code, auth_number, quantity, denied_reason (AC #5)
  - [x]TestAllSevenHCRCodes: parametrized test for all 7 codes → correct enum value (AC #6)
  - [x]TestConvenienceProperties: A1→is_approved, A3→is_denied, A4→is_pended (AC #6)
  - [x]TestMissingFields: minimal dict → None fields, no exceptions (AC #7)
  - [x]TestExtraFields: unexpected keys silently ignored (AC #7)
  - [x]TestUnmappedActionCode: unknown code → WARNING finding, no exception (AC #8)
  - [x]TestRawResponsePreserved: raw_response matches input dict (AC #9)
  - [x]TestInputDictUnmodified: original dict unchanged after parsing (AC #10)
  - [x]TestPerformance: < 50ms execution (AC #11)
  - [x]TestEmptyDict: empty `{}` → PriorAuthResponse with all None fields, no exception
  - [x]TestNoneValues: fields with None values → handled gracefully

- [x]Task 5: Add `parse_278_response` re-exports (AC: #12)
  - [x]Add `parse_278_response` to `claim-validator/src/claim_validator/prior_auth/__init__.py` imports and `__all__`
  - [x]Add `parse_278_response` to `claim-validator/src/claim_validator/__init__.py` imports and `__all__`
  - [x]Keep `__all__` lists alphabetically sorted

- [x]Task 6: Create `test_imports.py` updates for `parse_278_response` (AC: #12)
  - [x]Add import test: `from claim_validator.prior_auth import parse_278_response`
  - [x]Add import test: `from claim_validator import parse_278_response`

- [x]Task 7: Run full test suite and lint
  - [x]Run `PYTHONPATH=src .venv/bin/pytest` from `claim-validator/` directory
  - [x]Run `ruff check src/ tests/` from `claim-validator/` directory
  - [x]Fix any failures or lint issues
  - [x]Verify all existing 990 tests still pass (no regressions)

## Dev Notes

### Architecture Contract for `parse_278_response()`

**From architecture.md (D25, D29, D30):**

```python
def parse_278_response(raw: dict) -> tuple[PriorAuthResponse, list[Finding]]:
    """Parse a raw 278 JSON dict into a structured PriorAuthResponse.

    Pure function — no network calls, no side effects, no mutation of raw dict.

    Returns:
        Tuple of (PriorAuthResponse, list[Finding]) where findings contain
        any WARNING-level issues encountered during parsing (e.g., unmapped codes).
    """
```

**File location:** `claim-validator/src/claim_validator/prior_auth/response_parser.py`
**Test location:** `claim-validator/tests/test_prior_auth/test_response_parser.py`

### 278 Response JSON Structure (Expected Input)

The raw 278 JSON dict from clearinghouses follows this approximate structure. Field names may vary by clearinghouse provider, so support common key conventions:

```python
{
    "action_code": "A1",           # or "hcr01": "A1"
    "authorization_number": "AUTH12345",
    "effective_date": "2026-03-01",  # ISO date string
    "expiration_date": "2026-06-01",
    "decision_reason_code": "01",    # for denied/modified
    "decision_reason_description": "Additional info required",
    "service_lines": [
        {
            "cpt_code": "99213",
            "action_code": "A1",
            "authorization_number": "AUTH12345-L1",
            "approved_quantity": 4,
            "denied_reason": None
        }
    ]
}
```

### Existing Models (DO NOT MODIFY)

**PriorAuthResponse** — `claim-validator/src/claim_validator/prior_auth/models/response.py`:
```python
class PriorAuthResponse(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    action_code: CertificationActionCode | None = None
    authorization_number: str | None = None
    effective_date: date | None = None
    expiration_date: date | None = None
    decision_reason_code: str | None = None
    decision_reason_description: str | None = None
    service_line_decisions: list[ServiceLineDecision] = []
    errors: list[PriorAuthError] = []
    raw_response: dict[str, Any] | None = None

    @property
    def is_approved(self) -> bool:     # A1
    @property
    def is_denied(self) -> bool:       # A3
    @property
    def is_pended(self) -> bool:       # A4
```

**ServiceLineDecision** — same file:
```python
class ServiceLineDecision(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    cpt_code: str | None = None
    action_code: CertificationActionCode | None = None
    authorization_number: str | None = None
    approved_quantity: int | None = None
    denied_reason: str | None = None
```

**CertificationActionCode** — `claim-validator/src/claim_validator/prior_auth/constants.py`:
```python
class CertificationActionCode(StrEnum):
    CERTIFIED_IN_TOTAL = "A1"
    CERTIFIED_PARTIAL = "A2"
    NOT_CERTIFIED = "A3"
    PENDED = "A4"
    MODIFIED = "A6"
    CONTACT_PAYER = "CT"
    NO_ACTION_REQUIRED = "NA"
```

**HCR action code lookup** — `claim-validator/src/claim_validator/prior_auth/code_tables/hcr_actions.py`:
```python
def get_hcr_action_code(code: str) -> dict[str, str] | None:
    """Returns {description, category, suggested_action} or None."""
```

**PriorAuthError** — `claim-validator/src/claim_validator/prior_auth/models/response.py`:
```python
class PriorAuthError(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    rejection_code: str
    follow_up_code: str | None = None
    message: str = ""
    suggested_fix: str = ""
```

### Finding Code Reference (This Story)

| Finding Code | Severity | Field | When |
|---|---|---|---|
| `PA_UNKNOWN_ACTION_CODE` | WARNING | `action_code` | HCR code not in `CertificationActionCode` enum |

Note: AAA error findings (`AAA_PA_REJECTION`) are **Story 2.2's scope**, NOT this story. This story parses the HCR action codes and service lines only. If AAA segments exist in the raw dict, they should be preserved in `raw_response` but NOT parsed into `PriorAuthError` objects in this story.

### Key Implementation Details

1. **Date parsing:** `effective_date` and `expiration_date` come as ISO date strings — parse with `datetime.date.fromisoformat()`. If format is invalid or missing → `None`.

2. **Action code mapping:** Use `CertificationActionCode(raw_code)` with try/except `ValueError` for unmapped codes. Do NOT use the `get_hcr_action_code()` lookup table — that's for human-readable descriptions. The enum itself handles code-to-enum conversion.

3. **Raw response preservation:** Use `copy.deepcopy(raw)` when storing in `raw_response` field to ensure immutability guarantee (AC #10).

4. **Return type:** Return `tuple[PriorAuthResponse, list[Finding]]` — NOT just PriorAuthResponse. The pipeline needs the findings list to aggregate.

5. **Import chain for re-exports:**
   - `prior_auth/__init__.py` → import `parse_278_response` from `prior_auth.response_parser`
   - `claim_validator/__init__.py` → import `parse_278_response` from `prior_auth`

### Existing Code to Reuse (DO NOT DUPLICATE)

**Response parser pattern:** Follow the same pure-function pattern described in architecture for `parse_271_response()` — a standalone function, NOT a class. Takes raw dict, returns structured model + findings.

**Finding creation:**
```python
from claim_validator.constants import Severity
from claim_validator.models.results import Finding

Finding(
    code="PA_UNKNOWN_ACTION_CODE",
    message="Unknown HCR action code encountered in 278 response",
    severity=Severity.WARNING,
    field_name="action_code",
    suggestion="Check 278 response for updated action code values",
    context={"raw_code": raw_code_value},
)
```

### Project Structure Notes

**New files to create:**

```
claim-validator/src/claim_validator/prior_auth/
└── response_parser.py                  # parse_278_response() pure function

claim-validator/tests/test_prior_auth/
├── conftest.py                         # Add make_278_response() fixture factory (extend existing)
└── test_response_parser.py             # All parser tests (~15 tests)
```

**Existing files to modify:**

| File | Change |
|---|---|
| `claim-validator/src/claim_validator/prior_auth/__init__.py` | Add `parse_278_response` to imports and `__all__` |
| `claim-validator/src/claim_validator/__init__.py` | Add `parse_278_response` to imports and `__all__` |
| `claim-validator/tests/test_prior_auth/test_imports.py` | Add import tests for `parse_278_response` |

**Files NOT to touch:**
- `claim-validator/src/claim_validator/prior_auth/models/response.py` — `PriorAuthResponse`, `ServiceLineDecision`, `PriorAuthError` all exist and are correct
- `claim-validator/src/claim_validator/prior_auth/constants.py` — `CertificationActionCode` enum is complete (7 codes)
- `claim-validator/src/claim_validator/prior_auth/code_tables/hcr_actions.py` — lookup table exists, not needed for parsing
- `claim-validator/src/claim_validator/prior_auth/pipeline.py` — pipeline integration is PA Epic 3's scope
- `claim-validator/src/claim_validator/prior_auth/_api.py` — submit_prior_auth() already works
- All existing validators — do NOT modify
- `pyproject.toml` — no new dependencies

### HIPAA Compliance

- Finding `message` fields MUST NOT contain PHI values
- Good: `"Unknown HCR action code encountered in 278 response"` with raw code in `context` dict
- Bad: `"Unknown action code 'XX' for patient John Doe"` — exposes PHI
- The raw 278 response stored in `raw_response` may contain PHI — this is expected (it's for programmatic access, NOT for LLM). PHI stripping happens in Phase 3 (PA Epic 4) via `PriorAuthDeidentifier`.

### Performance (NFR3)

- Target: < 50ms for `parse_278_response()` on a typical 278 response
- Pure function with no I/O — should be well under 50ms
- `copy.deepcopy()` on raw dict is the heaviest operation — still fast for typical response sizes
- No code table lookups required (enum conversion is O(1))

### Previous Story Learnings (PA-1.1 through PA-1.5)

From PA-1.5:
- Test runner command: `PYTHONPATH=src .venv/bin/pytest` from `claim-validator/` directory
- Ruff lint: `ruff check src/ tests/` from `claim-validator/` directory
- Code review issue: `VALIDATOR_ERROR` finding code lacks `PA_` prefix — use `PA_` prefix for all new finding codes
- Keep `from __future__ import annotations` on every file
- Keep `__all__` lists alphabetically sorted
- Valid test data: NPI `"1234567893"`, HCPCS `A4206`/`G0008`, ICD-10 `J06.9`/`E11.9`

From PA-1.4:
- All validators subclass BaseValidator with `# type: ignore[override]` for PriorAuthRequest param
- Finding messages reference field NAMES only, never actual values (HIPAA NFR12)

From PA-1.2:
- Test files need `from __future__ import annotations`
- Re-export tests and performance tests are required

From PA-1.1:
- All models use `ConfigDict(frozen=True, strict=False)` — do NOT change
- Keep `__all__` lists alphabetically sorted

### References

- [Source: architecture.md — D25: PA model design, line 1945]
- [Source: architecture.md — D29: HCR action codes, line 1946]
- [Source: architecture.md — D30: AAA errors (dual access), line 1947]
- [Source: architecture.md — parse_278_response() contract, line 2100]
- [Source: architecture.md — Response parser naming: parse_278_response(), line 2137]
- [Source: architecture.md — Pipeline Phase 2 flow, lines 2047-2050]
- [Source: architecture.md — FR25-FR31: 278 Response Parsing, line 1815]
- [Source: epics.md — PA Epic 2, Story 2.1, lines 1264-1326]
- [Source: project-context.md — PA pipeline architecture, lines 74-86]
- [Source: project-context.md — Response Parser Contract, lines 106-113]
- [Source: project-context.md — Finding code prefixes (PA_, AAA_PA_REJECTION), lines 148-162]
- [Source: project-context.md — Model patterns (frozen, strict=False), lines 132-137]
- [Source: pa-1-5 story — Previous story learnings and test patterns]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- Full test suite: 1032 passed, 0 failed (42 new tests added)
- Ruff lint: All new/modified files pass (2 pre-existing issues in server.py not related to this story)
- Response parser tests: 41 tests all passing
- Performance: parse_278_response() well under 50ms target

### Completion Notes List

- All 7 tasks and all subtasks completed
- All 12 ACs satisfied
- `parse_278_response()` implemented as pure function returning `tuple[PriorAuthResponse, list[Finding]]`
- Supports both `action_code` and `hcr01` key conventions (action_code takes precedence)
- All 7 HCR codes (A1, A2, A3, A4, A6, CT, NA) mapped to CertificationActionCode enum
- Unmapped codes generate `PA_UNKNOWN_ACTION_CODE` WARNING finding (no exceptions)
- Missing fields gracefully handled as None (no exceptions)
- Extra/unexpected keys silently ignored
- Input dict preserved via `copy.deepcopy()` — original never mutated
- `raw_response` stores complete unmodified 278 JSON
- Date parsing handles ISO strings, date objects, and invalid values (returns None)
- Service line parsing handles non-list, non-dict, invalid quantity gracefully
- Case-insensitive action code handling (normalizes to uppercase)
- Re-exports added at `prior_auth/__init__.py` and `claim_validator/__init__.py`
- Import tests updated for `parse_278_response` at both levels
- `__all__` lists kept alphabetically sorted
- PHI safety: finding messages reference field names only, never actual values
- AAA error parsing explicitly NOT included (Story 2.2 scope)

### File List

**New source files:**
| File | Description |
|---|---|
| `src/claim_validator/prior_auth/response_parser.py` | parse_278_response() pure function, ParsedResponse type alias, _parse_action_code(), _parse_date(), _parse_service_lines() helpers |

**New test files:**
| File | Tests |
|---|---|
| `tests/test_prior_auth/test_response_parser.py` | 41 tests across 12 test classes |

**Modified files:**
| File | Change |
|---|---|
| `src/claim_validator/prior_auth/__init__.py` | Added `parse_278_response` import and `__all__` entry |
| `src/claim_validator/__init__.py` | Added `parse_278_response` import and `__all__` entry |
| `tests/test_prior_auth/test_imports.py` | Added `parse_278_response` import tests at both module and top levels, added to `__all__` symbol lists |
| `tests/test_prior_auth/conftest.py` | No changes (fixture factory is local to test file) |

## Senior Developer Code Review

### Review Summary

Code review completed. **7 issues found** (1 HIGH, 4 MEDIUM, 2 LOW). Issues #1 and #2 fixed automatically. Remaining items documented as non-blocking action items.

### Issues Found

| # | Severity | File:Line | Issue | Resolution |
|---|----------|-----------|-------|------------|
| 1 | HIGH | `response_parser.py:38` | `or` operator conflates missing key with falsy value (empty string falls through to `hcr01`) | **FIXED** — Changed to explicit `is None` check |
| 2 | MEDIUM | `conftest.py:22-39` | Dead `make_278_response()` function never used by any test | **FIXED** — Removed from conftest.py |
| 3 | MEDIUM | `test_response_parser.py` | `_make_278_response()` duplicated between test file and conftest (before fix #2) | Resolved by fix #2 — conftest copy removed, test-local copy is the canonical one |
| 4 | MEDIUM | Story Task 3 | Subtask "Create fixtures/ directory" marked [x] but directory not created | Non-blocking — fixtures embedded in test helper function, no directory needed |
| 5 | MEDIUM | `response_parser.py:117` | `_parse_date` accepts `datetime` unchanged (subclass of `date`) | Non-blocking — `datetime` IS-A `date`, Pydantic coerces correctly. No behavioral bug. |
| 6 | LOW | `response_parser.py:17` | `ParsedResponse` type alias not re-exported in `__init__.py` | Non-blocking — internal type alias, not part of public API |
| 7 | LOW | `test_response_parser.py:17-39` | Default fixture leaks `action_code` into service lines, caused 2 test failures during dev | Tests already fixed with explicit `service_lines=[]` overrides |

### Post-Review Test Results

- Full test suite: **1032 passed, 0 failed**
- No regressions after fixes #1 and #2
