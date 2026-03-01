# Story PA-1.2: PA Code Tables (HCR Action Codes, AAA Reject Codes, Service Types)

Status: done

## Story

As a **developer**,
I want bundled reference data for HCR action codes, AAA reject reason codes, and service type codes,
so that the PA module can map X12 278 codes to human-readable descriptions offline.

## Acceptance Criteria

1. **Given** the installed package
   **When** I call `get_hcr_action_code("A1")`
   **Then** it returns a dict with `description` ("Certified in Total"), `category` ("approved"), and `suggested_action`
   **And** all 7 HCR codes are mapped: A1, A2, A3, A4, A6, CT, NA

2. **Given** the HCR action code data
   **When** I inspect `prior_auth/data/hcr_action_codes.json`
   **Then** it contains all 7 action codes with descriptions, categories (approved/denied/pended/other), and suggested actions

3. **Given** the installed package
   **When** I call `get_aaa_reject_code("04")`
   **Then** it returns a dict with `meaning`, `description`, and `suggested_fix`
   **And** top 20+ codes are mapped (04, 15, 33, 35, 41-58, 60, 71-73, 79, T4)

4. **Given** the AAA reject code data
   **When** I inspect `prior_auth/data/aaa_reject_codes.json`
   **Then** it contains reject codes with human-readable messages and suggested corrective actions

5. **Given** the installed package
   **When** I call `get_pa_service_type("73")`
   **Then** it returns the service type description

6. **Given** two threads calling `get_hcr_action_code()` concurrently
   **When** both trigger the first load simultaneously
   **Then** the data is loaded exactly once (double-check locking with `threading.Lock`)
   **And** both threads receive correct results

7. **Given** any code table lookup with a non-existent code
   **When** I query it
   **Then** `None` is returned (no exception raised)

8. **Given** code table loading
   **When** I measure the first load time
   **Then** it completes in under 500ms
   **And** subsequent lookups complete in under 1ms

## Tasks / Subtasks

- [x] Task 1: Create `prior_auth/data/hcr_action_codes.json` (AC: #1, #2)
  - [x] 7 HCR action codes with `description`, `category`, `suggested_action` fields
  - [x] Categories: `approved` (A1), `partial` (A2), `denied` (A3), `pended` (A4), `modified` (A6), `contact` (CT), `no_action` (NA)
- [x] Task 2: Create `prior_auth/data/aaa_reject_codes.json` (AC: #3, #4)
  - [x] 23 AAA reject reason codes: 04, 15, 33, 35, 41-49, 51, 56, 57, 58, 60, 71, 72, 73, 79, T4
  - [x] Each entry: `meaning`, `description`, `suggested_fix`
- [x] Task 3: Create `prior_auth/data/service_types.json` (AC: #5)
  - [x] X12 service type codes relevant to PA (from UM segment UM04)
  - [x] Key codes: 01 (Medical Care), 02 (Surgical), 03 (Consultation), 04 (Diagnostic X-Ray), 05 (Diagnostic Lab), 06 (Radiation Therapy), 12 (DME Purchase), 14 (Renal), 18 (DME Rental), 42 (Home Health Care), 45 (Hospice), 48 (Hospital-Inpatient), 50 (Hospital-Outpatient), 54 (Long Term Care), 62 (MRI/CT), 73 (Mental Health), 86 (Emergency), 88 (Pharmacy), A4 (Psychiatric-Inpatient), A7 (Psychiatric-Outpatient), AL (Vision), BB (Partial Hospitalization)
- [x] Task 4: Create `prior_auth/data/manifest.json` (AC: #2, #4)
  - [x] Metadata for all 3 PA code tables: code counts, effective dates, sources
- [x] Task 5: Create PA code table loader `prior_auth/code_tables/loader.py` (AC: #6, #8)
  - [x] Lazy singleton with `threading.Lock` (double-check locking)
  - [x] `load_pa_json(filename: str) -> dict` using `importlib.resources` from `claim_validator.prior_auth.data`
  - [x] Per-table lock for thread safety
  - [x] Raises `CodeTableError` on failure
- [x] Task 6: Create `prior_auth/code_tables/hcr_actions.py` (AC: #1, #7)
  - [x] `get_hcr_action_code(code: str) -> dict | None`
  - [x] Normalizes input: `.upper().strip()`
  - [x] Returns `None` for unknown codes
- [x] Task 7: Create `prior_auth/code_tables/aaa_reject_codes.py` (AC: #3, #7)
  - [x] `get_aaa_reject_code(code: str) -> dict | None`
  - [x] Normalizes input: `.upper().strip()`
  - [x] Returns `None` for unknown codes
- [x] Task 8: Create `prior_auth/code_tables/service_types.py` (AC: #5, #7)
  - [x] `get_pa_service_type(code: str) -> str | None`
  - [x] Returns description string or `None` for unknown codes
- [x] Task 9: Update `prior_auth/code_tables/__init__.py` (AC: #1, #3, #5)
  - [x] Re-export `get_hcr_action_code`, `get_aaa_reject_code`, `get_pa_service_type`
  - [x] `__all__` list
- [x] Task 10: Update `prior_auth/data/__init__.py`
  - [x] Replace stub docstring with proper module docstring
- [x] Task 11: Create test files (AC: all)
  - [x] `tests/test_prior_auth/test_code_tables/__init__.py`
  - [x] `tests/test_prior_auth/test_code_tables/conftest.py` (cache reset fixture)
  - [x] `tests/test_prior_auth/test_code_tables/test_hcr_actions.py`
  - [x] `tests/test_prior_auth/test_code_tables/test_aaa_reject_codes.py`
  - [x] `tests/test_prior_auth/test_code_tables/test_service_types.py`
  - [x] `tests/test_prior_auth/test_code_tables/test_loader.py` (thread safety, manifest validation)

## Dev Notes

### Architecture Compliance (CRITICAL)

**Source: architecture.md — Decision D29**

- **D29 (HCR action codes):** `CertificationActionCode` StrEnum already exists in `prior_auth/constants.py` (from Story 1.1). This story creates the **JSON description table** and **lookup functions** that supplement the enum with human-readable data
- **D1/D2 (Code table pattern):** Follow the existing lazy singleton pattern with `threading.Lock`. PA code tables are small (<5KB each), so use **plain JSON** (not gzip compressed) — same approach as `timely_filing.json`
- The PA code tables have their OWN loader (`prior_auth/code_tables/loader.py`) that reads from `claim_validator.prior_auth.data` package, NOT from the top-level `claim_validator.data` directory. This keeps the PA module self-contained

### Code Table JSON Format (MUST FOLLOW)

**HCR Action Codes (`hcr_action_codes.json`):**

```json
{
  "A1": {
    "description": "Certified in Total",
    "category": "approved",
    "suggested_action": "Proceed with service; include authorization number on 837 claim"
  },
  "A3": {
    "description": "Not Certified",
    "category": "denied",
    "suggested_action": "File appeal or provide additional documentation"
  }
}
```

Return type: `dict | None` — returns the inner dict or `None` for unknown codes.

**AAA Reject Codes (`aaa_reject_codes.json`):**

```json
{
  "04": {
    "meaning": "Authorized Quantity Exceeded",
    "description": "Requested service quantity exceeds allowed limits",
    "suggested_fix": "Reduce requested quantity or provide clinical justification for higher quantity"
  },
  "72": {
    "meaning": "Invalid/Missing Subscriber ID",
    "description": "Member ID not found or incorrect format",
    "suggested_fix": "Verify member ID with patient's insurance card and resubmit"
  }
}
```

Return type: `dict | None` — returns the inner dict or `None` for unknown codes.

**Service Types (`service_types.json`):**

```json
{
  "01": "Medical Care",
  "02": "Surgical",
  "73": "Mental Health"
}
```

Return type: `str | None` — returns description string or `None`.

### PA Code Table Loader Pattern (MUST FOLLOW)

**Source: existing codebase — `code_tables/loader.py` and `code_tables/timely_filing.py`**

The PA module needs its own loader because it reads from `claim_validator.prior_auth.data`, not `claim_validator.data`. Follow the module-level cache pattern (like `timely_filing.py`):

```python
"""PA code table loader — lazy singleton with thread safety."""

from __future__ import annotations

import json
import threading
from importlib.resources import files
from typing import Any

from claim_validator.exceptions import CodeTableError

_global_lock = threading.Lock()
_locks: dict[str, threading.Lock] = {}
_tables: dict[str, Any] = {}


def _get_lock(table_name: str) -> threading.Lock:
    """Get or create a per-table lock (thread-safe)."""
    if table_name not in _locks:
        with _global_lock:
            if table_name not in _locks:
                _locks[table_name] = threading.Lock()
    return _locks[table_name]


def load_pa_json(filename: str) -> Any:
    """Load a JSON file from prior_auth/data/ with lazy singleton caching.

    First call loads from disk; subsequent calls return the cached dict.
    Thread-safe via double-check locking.
    """
    table_name = filename.removesuffix(".json")

    if table_name in _tables:
        return _tables[table_name]

    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:
            return _tables[table_name]

        try:
            data_pkg = files("claim_validator.prior_auth.data")
            resource = data_pkg.joinpath(filename)
            table = json.loads(resource.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CodeTableError(
                f"Failed to load PA code table '{filename}': {exc}"
            ) from exc

        _tables[table_name] = table
        return table
```

**Key differences from top-level loader:**
- Uses `files("claim_validator.prior_auth.data")` not `files("claim_validator.data")`
- No gzip decompression (plain JSON)
- Same double-check locking pattern
- Same `CodeTableError` on failure

### Lookup Function Pattern (MUST FOLLOW)

```python
"""HCR action code lookup for 278 response interpretation."""

from __future__ import annotations

from typing import Any

from claim_validator.prior_auth.code_tables.loader import load_pa_json


def get_hcr_action_code(code: str) -> dict[str, str] | None:
    """Look up an HCR action code. Returns details dict or None if not found.

    The returned dict contains: description, category, suggested_action.
    """
    table: dict[str, Any] = load_pa_json("hcr_action_codes.json")
    normalized = code.upper().strip()
    return table.get(normalized)
```

**Rules:**
- `from __future__ import annotations` at top
- Docstring on every public function
- Normalize input with `.upper().strip()`
- Use `.get()` for safe lookup (returns `None` for missing)
- Return type: `dict[str, str] | None` for HCR/AAA, `str | None` for service types
- No exceptions for missing codes — always return `None`

### Naming Conventions (MUST FOLLOW)

**Source: architecture.md — PA Naming Patterns, project-context.md**

| Element | Correct | Anti-Pattern |
|---|---|---|
| HCR lookup | `get_hcr_action_code()` | `lookup_hcr()`, `hcr_lookup()` |
| AAA lookup | `get_aaa_reject_code()` | `lookup_aaa()`, `aaa_lookup()` |
| Service type lookup | `get_pa_service_type()` | `lookup_service_type()`, `get_service_type()` (conflicts with eligibility) |
| Loader function | `load_pa_json()` | `load_json()` (conflicts with top-level) |
| Module file | `hcr_actions.py` | `hcr.py`, `action_codes.py` |
| Module file | `aaa_reject_codes.py` | `aaa.py`, `reject_codes.py` |
| Module file | `service_types.py` | `services.py`, `pa_services.py` |
| Data files | `hcr_action_codes.json` | `hcr.json`, `actions.json` |

### Test Patterns (MUST FOLLOW)

**Source: existing codebase — `tests/test_code_tables/`**

**Cache reset fixture (`conftest.py`):**

```python
"""Shared fixtures for PA code table tests."""

from __future__ import annotations

from collections.abc import Iterator

import pytest


@pytest.fixture(autouse=True)
def _reset_pa_table_caches() -> Iterator[None]:
    """Reset PA lazy-loaded table caches between tests."""
    from claim_validator.prior_auth.code_tables import loader

    loader._tables.clear()
    loader._locks.clear()
    yield
```

**Test coverage requirements:**
- Valid code lookup with assertion on returned fields
- Case insensitivity (lowercase input)
- Whitespace handling (` A1 ` should match `A1`)
- All known codes exist (iterate complete code list)
- Invalid/unknown code returns `None`
- Empty string returns `None`
- Thread safety: 8 concurrent loads → same object identity
- Manifest validation: code counts match actual table sizes
- First load time < 500ms
- Subsequent lookup time < 1ms

**Thread safety test pattern:**

```python
import concurrent.futures

class TestThreadSafety:
    def test_concurrent_first_load(self) -> None:
        """Multiple threads loading simultaneously — data loaded once."""
        results: list[Any] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(load_pa_json, "hcr_action_codes.json")
                for _ in range(8)
            ]
            results = [f.result() for f in futures]
        # All results should be the same object (identity check)
        assert all(r is results[0] for r in results)
```

### Project Structure Notes

**New files to create:**

```
src/claim_validator/prior_auth/
├── code_tables/
│   ├── __init__.py          # Re-exports: get_hcr_action_code, get_aaa_reject_code, get_pa_service_type
│   ├── loader.py            # PA-specific lazy singleton loader
│   ├── hcr_actions.py       # HCR action code lookup
│   ├── aaa_reject_codes.py  # AAA reject reason code lookup
│   └── service_types.py     # PA service type code lookup
├── data/
│   ├── __init__.py          # Updated docstring
│   ├── hcr_action_codes.json   # 7 HCR action codes
│   ├── aaa_reject_codes.json   # 23 AAA reject codes
│   ├── service_types.json      # ~22 PA-relevant service type codes
│   └── manifest.json           # Metadata for all 3 PA code tables

tests/test_prior_auth/
├── test_code_tables/
│   ├── __init__.py
│   ├── conftest.py              # Cache reset autouse fixture
│   ├── test_loader.py           # Loader mechanics, thread safety, manifest
│   ├── test_hcr_actions.py      # HCR action code lookups
│   ├── test_aaa_reject_codes.py # AAA reject code lookups
│   └── test_service_types.py    # Service type code lookups
```

**Existing files to modify:**

| File | Change |
|---|---|
| `src/claim_validator/prior_auth/code_tables/__init__.py` | Replace stub with re-exports and `__all__` |
| `src/claim_validator/prior_auth/data/__init__.py` | Replace stub docstring |

**Files NOT to touch:**
- `src/claim_validator/__init__.py` — no new top-level re-exports needed (code table lookups are internal)
- `src/claim_validator/conf.py` — no new settings fields needed
- `src/claim_validator/prior_auth/constants.py` — enums already exist from Story 1.1
- `src/claim_validator/prior_auth/models/` — no model changes
- `src/claim_validator/code_tables/loader.py` — PA has its own loader; do NOT modify the existing one
- `pyproject.toml` — no new dependencies; JSON data files included via existing `[tool.hatch.build]` patterns

### HCR Action Code Reference (Complete Data)

**Source: research — domain-healthcare-prior-authorization-278-research-2026-02-27.md, Section 1.4**

| Code | Description | Category | Suggested Action |
|------|-------------|----------|-----------------|
| A1 | Certified in Total | approved | Proceed with service; include authorization number on 837 claim |
| A2 | Certified Partial | partial | Review which services approved; may appeal denied items |
| A3 | Not Certified | denied | File appeal or provide additional documentation |
| A4 | Pended | pended | Submit additional documentation (275 transaction or fax) |
| A6 | Modified | modified | Review modifications (reduced units, different dates, etc.) |
| CT | Contact Payer | contact | Call payer for manual processing |
| NA | No Action Required | no_action | Proceed without authorization; PA not needed for this service |

### AAA Reject Code Reference (Complete Data)

**Source: research — Section 8.1**

| Code | Meaning | Description |
|------|---------|-------------|
| 04 | Authorized Quantity Exceeded | Requested service quantity exceeds allowed limits |
| 15 | Required Application Data Missing | Mandatory data elements not provided |
| 33 | Input Errors | Syntax or formatting errors in the request |
| 35 | Out of Network | Requesting or servicing provider is not in the payer's network |
| 41 | Authorization/Access Restrictions | Entity not authorized to submit/receive PA requests |
| 42 | Unable to Respond at Current Time | Payer system temporarily unavailable |
| 43 | Invalid/Missing Provider Identification | NPI or provider ID invalid or not on file |
| 44 | Invalid/Missing Provider Name | Provider name mismatch or missing |
| 45 | Invalid/Missing Provider Specialty | Provider specialty code invalid |
| 46 | Invalid/Missing Provider Phone Number | Required contact information missing |
| 47 | Invalid/Missing Provider State | Provider state not valid |
| 48 | Invalid/Missing Referring Provider | Referring provider information required but missing |
| 49 | Provider Ineligible for Inquiries | Provider not enrolled for electronic PA submission |
| 51 | Provider Not on File | Provider NPI not found in payer's directory |
| 56 | Provider Not Eligible | Provider not eligible to submit this type of request |
| 57 | Patient Not Eligible | Patient/subscriber not found or not eligible |
| 58 | Date of Birth Does Not Match | Patient DOB mismatch with payer records |
| 60 | Date of Injury/Illness is in the Future | Invalid date logic |
| 71 | Patient Gender Mismatch | Gender on request does not match payer records |
| 72 | Invalid/Missing Subscriber ID | Member ID not found or incorrect format |
| 73 | Invalid/Missing Subscriber Name | Subscriber name mismatch |
| 79 | Invalid Participant Identification | Generic identification error |
| T4 | Payer Name/ID Missing | Required payer identification not provided |

### PA Service Type Code Reference

**Source: X12 005010X217 UM04 (Service Type Code), research Section 1.4**

Key service type codes relevant to PA (subset of full X12 service type code set):

| Code | Description |
|------|-------------|
| 01 | Medical Care |
| 02 | Surgical |
| 03 | Consultation |
| 04 | Diagnostic X-Ray |
| 05 | Diagnostic Lab |
| 06 | Radiation Therapy |
| 12 | DME Purchase |
| 14 | Renal Dialysis |
| 18 | DME Rental |
| 42 | Home Health Care |
| 45 | Hospice |
| 48 | Hospital — Inpatient |
| 50 | Hospital — Outpatient |
| 54 | Long Term Care |
| 62 | MRI/CT Scan |
| 73 | Mental Health |
| 86 | Emergency Services |
| 88 | Pharmacy |
| A4 | Psychiatric — Inpatient |
| A7 | Psychiatric — Outpatient |
| AL | Vision |
| BB | Partial Hospitalization |

### HIPAA Compliance Notes

- Code tables contain NO PHI — only reference data (code descriptions, suggested actions)
- No logging of code table lookup inputs (defensive — could contain metadata derived from patient context)
- Thread-safe loading prevents data corruption in concurrent environments

### References

- [Source: architecture.md — D29 HCR action code mapping]
- [Source: architecture.md — D1/D2 Code table storage and loading patterns]
- [Source: architecture.md — D30 AAA error model]
- [Source: architecture.md — PA file structure and code_tables/ directory]
- [Source: research — domain-healthcare-prior-authorization-278-research-2026-02-27.md — Section 1.4 HCR Segment]
- [Source: research — Section 8.1 AAA Segment Reject Reason Codes]
- [Source: epics.md — PA Epic 1, Story 1.2 Acceptance Criteria]
- [Source: existing codebase — code_tables/loader.py, code_tables/timely_filing.py (pattern reference)]
- [Source: existing codebase — tests/test_code_tables/ (test pattern reference)]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- 2 ruff I001 import sorting issues in test files — auto-fixed with `--fix`
- Code review: 6 findings (3 MEDIUM, 3 LOW) — all fixed automatically

### Completion Notes List

- Created 3 JSON data files: `hcr_action_codes.json` (7 codes), `aaa_reject_codes.json` (23 codes), `service_types.json` (22 codes)
- Created `manifest.json` with code counts, effective dates, and source references for all 3 tables
- Created PA-specific lazy singleton loader (`loader.py`) using `importlib.resources` from `claim_validator.prior_auth.data` — follows same double-check locking pattern as existing `code_tables/loader.py` but reads from PA data package
- Created 3 lookup functions: `get_hcr_action_code()` (returns dict), `get_aaa_reject_code()` (returns dict), `get_pa_service_type()` (returns str)
- All lookups normalize input with `.upper().strip()` and return `None` for unknown codes
- Updated `code_tables/__init__.py` with re-exports and `__all__`
- 57 tests covering: all code lookups, case insensitivity, whitespace handling, unknown codes, field completeness, thread safety (8 concurrent loads), manifest validation (code counts match actual tables), error handling (CodeTableError for missing files), performance (AC8 timing), package re-exports (`__init__.py`)
- All 825 tests pass (57 new PA code table + 768 existing), zero regressions
- All ACs satisfied: AC1 (HCR 7 codes), AC2 (JSON structure), AC3 (AAA 23 codes), AC4 (AAA structure), AC5 (service types), AC6 (thread safety), AC7 (None for unknown), AC8 (explicit timing assertions: first load <500ms, cached lookup <1ms)

### Code Review Fixes

| # | Severity | Finding | Fix |
|---|----------|---------|-----|
| 1 | MEDIUM | No import/re-export test for `code_tables/__init__.py` | Added `TestPackageReExports` class (4 tests) in `test_loader.py` |
| 2 | MEDIUM | No explicit timing assertions for AC8 | Added `TestPerformance` class (2 tests) in `test_loader.py` — first load <500ms, cached <1ms |
| 3 | MEDIUM | `test_code_tables/__init__.py` missing `from __future__ import annotations` | Added the import |
| 4 | LOW | Task 2 description says "22 AAA codes" but implementation has 23 | Fixed to "23" in story file |
| 5 | LOW | Unicode em-dashes in `service_types.json` | Replaced with ASCII hyphens |
| 6 | LOW | Informational — return type annotation | No fix needed (informational only) |

### File List

**New files:**
- `src/claim_validator/prior_auth/data/hcr_action_codes.json`
- `src/claim_validator/prior_auth/data/aaa_reject_codes.json`
- `src/claim_validator/prior_auth/data/service_types.json`
- `src/claim_validator/prior_auth/data/manifest.json`
- `src/claim_validator/prior_auth/code_tables/loader.py`
- `src/claim_validator/prior_auth/code_tables/hcr_actions.py`
- `src/claim_validator/prior_auth/code_tables/aaa_reject_codes.py`
- `src/claim_validator/prior_auth/code_tables/service_types.py`
- `tests/test_prior_auth/test_code_tables/__init__.py`
- `tests/test_prior_auth/test_code_tables/conftest.py`
- `tests/test_prior_auth/test_code_tables/test_loader.py`
- `tests/test_prior_auth/test_code_tables/test_hcr_actions.py`
- `tests/test_prior_auth/test_code_tables/test_aaa_reject_codes.py`
- `tests/test_prior_auth/test_code_tables/test_service_types.py`

**Modified files:**
- `src/claim_validator/prior_auth/code_tables/__init__.py` (replaced stub with re-exports)
- `src/claim_validator/prior_auth/data/__init__.py` (replaced stub docstring)
