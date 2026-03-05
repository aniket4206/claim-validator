# Story 1.2: Shared Code Tables Consolidation

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a library maintainer,
I want all code table loaders and data files consolidated in `shared/code_tables/` and `shared/data/`,
so that any module can look up any code table through one import path.

## Acceptance Criteria

1. **AC-1: Unified data directory exists**
   - `src/claim_validator/shared/data/__init__.py` exists (package marker for `importlib.resources`)
   - All 10 data files from the 3 domains are present in `shared/data/`
   - Compressed files remain compressed (`.json.gz`), plain files remain plain (`.json`)

2. **AC-2: Unified loader with lazy singleton caching**
   - `shared/code_tables/loader.py` provides `load_compressed_json()` and `load_json()` functions
   - First call loads from disk; subsequent calls return the cached dict
   - Thread-safe via double-check locking with per-table `threading.Lock`

3. **AC-3: Table accessor functions return correct data**
   - **Given** ICD-10, HCPCS, taxonomy, POS, payer directory, service types, HCR action codes, AAA reject codes, and timely filing JSON files exist in `shared/data/`
   - **When** `get_icd10_table()`, `get_hcpcs_table()`, `get_taxonomy_table()`, `get_pos_table()`, `get_payer_directory_table()`, `get_service_types_table()`, `get_hcr_action_codes_table()`, `get_aaa_reject_codes_table()`, `get_timely_filing_table()` are called
   - **Then** the correct code table dict is returned (non-empty, correct type)

4. **AC-4: Lookup convenience functions with normalization**
   - **Given** `lookup_icd10(code)` is called with `"J06.9"` or `"J069"` (with or without dot)
   - **Then** the description is returned regardless of dot format
   - **And** `lookup_hcpcs(code)`, `lookup_taxonomy(code)`, `lookup_pos(code)`, `lookup_payer(payer_id)`, `lookup_service_type(code)`, `lookup_hcr_action(code)`, `lookup_aaa_reject(code)`, `get_filing_deadline(payer_id)` all return correct lookups

5. **AC-5: Thread-safe lazy singleton loading**
   - **Given** a code table has not been loaded yet
   - **When** its accessor function is called for the first time
   - **Then** it loads lazily via singleton with `threading.Lock`
   - **And** subsequent calls return the cached instance without re-loading
   - **Given** two threads call the same code table accessor simultaneously
   - **When** both attempt first-time initialization
   - **Then** only one thread performs the load; the other gets the cached result

6. **AC-6: Cross-cutting quality**
   - All functions pass mypy strict, ruff clean, have docstrings
   - FR18, FR19, FR20 are satisfied
   - `shared/code_tables/__init__.py` re-exports all table accessors and lookup functions with `__all__`

## Tasks / Subtasks

- [x] Task 1: Create shared/data/ package with consolidated data files (AC: #1)
  - [x] 1.1: Create `src/claim_validator/shared/data/__init__.py` (package marker)
  - [x] 1.2: Copy compressed data files from `data/`: `icd10_cm.json.gz`, `hcpcs.json.gz`, `pos_codes.json.gz`, `taxonomy.json.gz`
  - [x] 1.3: Copy plain data file from `data/`: `timely_filing.json`
  - [x] 1.4: Copy plain data files from `eligibility/data/`: `payer_directory.json`, `service_types.json`
  - [x] 1.5: Copy plain data files from `prior_auth/data/`: `aaa_reject_codes.json`, `hcr_action_codes.json`, `pa_service_types.json` (renamed from `service_types.json`)
  - [x] 1.6: Create consolidated `manifest.json` with metadata for all tables
- [x] Task 2: Create unified loader module (AC: #2)
  - [x] 2.1: Create `src/claim_validator/shared/code_tables/__init__.py` (re-exports all functions with `__all__`)
  - [x] 2.2: Create `src/claim_validator/shared/code_tables/loader.py` with `load_compressed_json()` and `load_json()`
  - [x] 2.3: Implement centralized `_tables` dict + `_locks` dict + `_global_lock` (proven pattern from existing loaders)
  - [x] 2.4: Load from `claim_validator.shared.data` package via `importlib.resources.files()`
- [x] Task 3: Create table accessor + lookup modules (AC: #3, #4)
  - [x] 3.1: Create `shared/code_tables/icd10.py` — `get_icd10_table()` + `lookup_icd10()` (with dot-variant normalization)
  - [x] 3.2: Create `shared/code_tables/hcpcs.py` — `get_hcpcs_table()` + `lookup_hcpcs()` (case-insensitive)
  - [x] 3.3: Create `shared/code_tables/taxonomy.py` — `get_taxonomy_table()` + `lookup_taxonomy()` (case-insensitive)
  - [x] 3.4: Create `shared/code_tables/pos.py` — `get_pos_table()` + `lookup_pos()`
  - [x] 3.5: Create `shared/code_tables/payer_directory.py` — `get_payer_directory_table()` + `lookup_payer()` (case-insensitive)
  - [x] 3.6: Create `shared/code_tables/service_types.py` — `get_service_types_table()` + `lookup_service_type()` (case-insensitive)
  - [x] 3.7: Create `shared/code_tables/hcr_actions.py` — `get_hcr_action_codes_table()` + `lookup_hcr_action()` (case-insensitive)
  - [x] 3.8: Create `shared/code_tables/aaa_reject_codes.py` — `get_aaa_reject_codes_table()` + `lookup_aaa_reject()` (case-insensitive)
  - [x] 3.9: Create `shared/code_tables/timely_filing.py` — `get_timely_filing_table()` + `get_filing_deadline()` (with `_default` fallback)
- [x] Task 4: Create tests (AC: #2, #3, #4, #5)
  - [x] 4.1: Create `tests/test_shared/test_code_tables/__init__.py`
  - [x] 4.2: Create `tests/test_shared/test_code_tables/test_loader.py` — caching, thread safety, error handling
  - [x] 4.3: Create `tests/test_shared/test_code_tables/test_lookups.py` — all lookup functions with known codes, not-found returns None, normalization
  - [x] 4.4: Create `tests/test_shared/test_code_tables/test_table_accessors.py` — all get_*_table() return non-empty dicts of correct type
- [x] Task 5: Quality verification (AC: #6)
  - [x] 5.1: Run `mypy --strict` — zero errors on all new source files (12 files checked)
  - [x] 5.2: Run `ruff check` — all checks passed
  - [x] 5.3: Run `pytest tests/test_shared/test_code_tables/` — 47 passed
  - [x] 5.4: Verify all existing tests still pass (`pytest`) — 1698 passed, zero regressions

## Dev Notes

### Architecture Decision D39: Shared Code Tables (MANDATORY)

All code table loaders and data files must be consolidated under `shared/code_tables/` and `shared/data/`. The architecture specifies:

```
shared/
├── code_tables/                     # Unified code table access (D39)
│   ├── __init__.py                  # Re-exports all accessor + lookup functions
│   ├── loader.py                    # Lazy singleton loader with threading.Lock
│   ├── icd10.py                     # get_icd10_table() + lookup_icd10()
│   ├── hcpcs.py                     # get_hcpcs_table() + lookup_hcpcs()
│   ├── taxonomy.py                  # get_taxonomy_table() + lookup_taxonomy()
│   ├── pos.py                       # get_pos_table() + lookup_pos()
│   ├── payer_directory.py           # get_payer_directory_table() + lookup_payer()
│   ├── service_types.py             # get_service_types_table() + lookup_service_type()
│   ├── hcr_actions.py               # get_hcr_action_codes_table() + lookup_hcr_action()
│   ├── aaa_reject_codes.py          # get_aaa_reject_codes_table() + lookup_aaa_reject()
│   └── timely_filing.py             # get_timely_filing_table() + get_filing_deadline()
└── data/                            # All bundled data files
    ├── __init__.py                  # Package marker (for importlib.resources)
    ├── manifest.json                # Consolidated metadata
    ├── icd10_cm.json.gz             # ICD-10-CM codes (~126 codes, compressed)
    ├── hcpcs.json.gz                # HCPCS/CPT codes (~111 codes, compressed)
    ├── taxonomy.json.gz             # Provider taxonomy (~58 codes, compressed)
    ├── pos_codes.json.gz            # Place of service (~51 codes, compressed)
    ├── timely_filing.json           # Payer filing deadlines (~12 entries)
    ├── payer_directory.json          # Payer network directory (~3,400 entries)
    ├── service_types.json           # X12 service type codes (~184 codes)
    ├── pa_service_types.json        # PA-specific service type subset (~22 codes)
    ├── hcr_action_codes.json        # HCR certification action codes (~7 codes)
    └── aaa_reject_codes.json        # AAA reject reason codes (~23 codes)
```

### Architecture Decision D43: Clean Break

- Story 1.2 ONLY creates new files in `shared/code_tables/` and `shared/data/`
- Does NOT modify or remove existing `code_tables/`, `eligibility/code_tables/`, `prior_auth/code_tables/`
- Does NOT modify or remove existing `data/`, `eligibility/data/`, `prior_auth/data/`
- Existing domain loaders continue to work from their current paths
- Epic 3 will remove old directories and migrate imports to `shared.code_tables`

### Data File Consolidation Strategy

Data files are **copied** (not moved) to `shared/data/` for Story 1.2 to preserve D43 compliance. The old data directories remain functional until Epic 3 removes them. This avoids breaking existing loaders that use:
- `importlib.resources.files("claim_validator.data")` (claims)
- `importlib.resources.files("claim_validator.eligibility.data")` (eligibility)
- `importlib.resources.files("claim_validator.prior_auth.data")` (prior auth)

### Service Types Collision

Two `service_types.json` files exist with different content:
- **Eligibility**: 184 X12 005010X279A1 service type codes (comprehensive set)
- **Prior Auth**: 22 X12 005010X217 service type codes (PA-relevant subset)

Resolution: Keep both in `shared/data/`:
- `service_types.json` — comprehensive X12 set (from eligibility)
- `pa_service_types.json` — PA-specific subset (renamed from prior_auth `service_types.json`)

The `lookup_service_type()` function uses the comprehensive set. PA-specific lookups use `lookup_pa_service_type()` if needed, or validators can just use the comprehensive table.

### Unified Loader Pattern (Proven from Existing Code)

All 3 existing domains use an identical lazy singleton pattern with double-check locking. The unified loader consolidates this:

```python
"""Unified lazy loader for code table data files (compressed and plain JSON)."""

from __future__ import annotations

import gzip
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


def load_compressed_json(filename: str) -> dict[str, str]:
    """Load a .json.gz file from shared/data/ with lazy singleton caching."""
    table_name = filename.removesuffix(".json.gz")
    if table_name in _tables:
        return _tables[table_name]
    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:
            return _tables[table_name]
        try:
            data_pkg = files("claim_validator.shared.data")
            raw = data_pkg.joinpath(filename).read_bytes()
            table: dict[str, str] = json.loads(gzip.decompress(raw))
        except Exception as exc:
            raise CodeTableError(f"Failed to load code table '{filename}': {exc}") from exc
        _tables[table_name] = table
        return table


def load_json(filename: str) -> Any:
    """Load a plain .json file from shared/data/ with lazy singleton caching."""
    table_name = filename.removesuffix(".json")
    if table_name in _tables:
        return _tables[table_name]
    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:
            return _tables[table_name]
        try:
            data_pkg = files("claim_validator.shared.data")
            table = json.loads(data_pkg.joinpath(filename).read_text(encoding="utf-8"))
        except Exception as exc:
            raise CodeTableError(f"Failed to load '{filename}': {exc}") from exc
        _tables[table_name] = table
        return table
```

**Key difference from existing**: Both `load_compressed_json()` AND `load_json()` now use lazy singleton caching (existing claims `load_json()` was uncached). The `timely_filing.py` no longer needs its own separate singleton.

### Table Accessor + Lookup Function Pattern

Each code table module provides two functions:
1. **Table accessor**: `get_*_table() -> dict[str, ...]` — returns the full cached table
2. **Lookup function**: `lookup_*(code: str) -> ... | None` — convenience with normalization

Example (ICD-10 with dot-variant normalization):

```python
"""ICD-10-CM code table — shared accessor and lookup."""

from __future__ import annotations

from claim_validator.shared.code_tables.loader import load_compressed_json


def get_icd10_table() -> dict[str, str]:
    """Return the full ICD-10-CM code table (cached after first load)."""
    return load_compressed_json("icd10_cm.json.gz")


def lookup_icd10(code: str) -> str | None:
    """Look up an ICD-10-CM code. Returns description or None.

    Handles codes with or without the dot separator (e.g. "J06.9" or "J069").
    """
    table = get_icd10_table()
    normalized = code.upper().strip()
    result = table.get(normalized)
    if result is not None:
        return result
    dotless = normalized.replace(".", "")
    result = table.get(dotless)
    if result is not None:
        return result
    if "." not in normalized and len(normalized) > 3:
        dotted = normalized[:3] + "." + normalized[3:]
        result = table.get(dotted)
    return result
```

Simple lookup modules (no normalization beyond case + strip):

```python
def get_hcpcs_table() -> dict[str, str]:
    return load_compressed_json("hcpcs.json.gz")

def lookup_hcpcs(code: str) -> str | None:
    return get_hcpcs_table().get(code.upper().strip())
```

### Existing Code Table Data Sources

| Data File | Source Dir | Entries | Format | Notes |
|---|---|---|---|---|
| `icd10_cm.json.gz` | `data/` | ~126 | `{code: description}` compressed | Dot variants (J06.9 / J069) |
| `hcpcs.json.gz` | `data/` | ~111 | `{code: description}` compressed | |
| `taxonomy.json.gz` | `data/` | ~58 | `{code: description}` compressed | |
| `pos_codes.json.gz` | `data/` | ~51 | `{code: description}` compressed | |
| `timely_filing.json` | `data/` | ~12 | `{payer_id: days}` plain | Has `_default` key |
| `payer_directory.json` | `eligibility/data/` | ~3,400 | `{payer_id: {name, type}}` plain | Largest file (295K) |
| `service_types.json` | `eligibility/data/` | ~184 | `{code: description}` plain | Full X12 set |
| `pa_service_types.json` | `prior_auth/data/` (orig: `service_types.json`) | ~22 | `{code: description}` plain | PA subset, renamed |
| `hcr_action_codes.json` | `prior_auth/data/` | ~7 | `{code: {description, category, suggested_action}}` plain | |
| `aaa_reject_codes.json` | `prior_auth/data/` | ~23 | `{code: {meaning, description, suggested_fix}}` plain | |

### Lookup Function Return Types

| Function | Input | Return Type | Normalization |
|---|---|---|---|
| `lookup_icd10(code)` | `str` | `str \| None` | Upper, strip, dot-variant handling |
| `lookup_hcpcs(code)` | `str` | `str \| None` | Upper, strip |
| `lookup_taxonomy(code)` | `str` | `str \| None` | Upper, strip |
| `lookup_pos(code)` | `str` | `str \| None` | Strip (no case conversion) |
| `lookup_payer(payer_id)` | `str` | `dict[str, str] \| None` | Upper, strip; returns `{name, type}` |
| `lookup_service_type(code)` | `str` | `str \| None` | Upper, strip |
| `lookup_hcr_action(code)` | `str` | `dict[str, str] \| None` | Upper, strip; returns `{description, category, suggested_action}` |
| `lookup_aaa_reject(code)` | `str` | `dict[str, str] \| None` | Upper, strip; returns `{meaning, description, suggested_fix}` |
| `get_filing_deadline(payer_id)` | `str` | `int \| None` | Upper, strip; `_default` fallback |

### Exception Handling

All loaders raise `CodeTableError` (from `claim_validator.exceptions`) on file load failure. This matches the existing pattern:

```python
from claim_validator.exceptions import CodeTableError
```

**Never** catch `CodeTableError` silently — a missing code table is a fatal configuration error.

### Import Pattern

All new files must use `from __future__ import annotations`:

```python
"""ICD-10-CM code table — shared accessor and lookup."""

from __future__ import annotations

from claim_validator.shared.code_tables.loader import load_compressed_json
```

**NEVER import domain models** in `shared/code_tables/`.

### What Story 1.2 must NOT create/modify

- Do NOT modify existing `code_tables/`, `eligibility/code_tables/`, `prior_auth/code_tables/`
- Do NOT modify existing `data/`, `eligibility/data/`, `prior_auth/data/`
- Do NOT modify `claim_validator/__init__.py` — no new exports yet
- Do NOT create `shared/validators/diagnosis.py`, `procedure.py`, `payer_id.py` — Story 1.3
- Do NOT create `shared/deidentifier/` or `shared/pipeline/` — Stories 2.x

### Previous Story 1.1 Intelligence

**Learnings from Story 1.1 implementation:**
- **pytest**: Use `.venv/bin/python -m pytest` (NOT `.venv/bin/pytest` — shebang points to wrong venv)
- **PHI-leak tests**: Pass actual PHI values as inputs, then assert they don't appear in output (Story 1.1 review caught hollow test)
- **`from __future__ import annotations`**: Required on ALL new files (Story 1.1 review caught missing one)
- **D43 compliance**: Create new files only, leave existing code untouched
- **Test pattern**: valid input → correct result, invalid input → correct fallback, statelessness, thread safety

### Quality Requirements

- **mypy strict** — `python_version = "3.11"`, strict = true, pydantic plugin enabled
- **ruff** — line-length=100, rules E/F/I/N/W/UP
- **pytest** — all new + all existing tests must pass
- **Docstrings** — module-level AND function-level on all public functions (NFR27)
- **Thread-safe** — all singletons use `threading.Lock` with double-check locking (NFR14)
- **Lazy loading** — no code table loaded at import time (NFR2: <500ms import)

### Testing Requirements

1. **test_loader.py**: Caching (call twice, verify same object returned), error handling (missing file raises CodeTableError), `_tables` cache populated after first load
2. **test_table_accessors.py**: Each `get_*_table()` returns non-empty dict of correct type, spot-check known codes exist
3. **test_lookups.py**: Each lookup function: known-valid code returns description, unknown code returns None, case insensitivity, ICD-10 dot-variant handling, payer directory returns dict with name/type, timely filing default fallback
4. **Thread safety**: Use `threading.Thread` to call same accessor concurrently, verify no exceptions and correct return

### References

- [Source: architecture.md — D39: Shared code tables consolidation]
- [Source: architecture.md — D2: Lazy singleton with threading.Lock]
- [Source: architecture.md — D43: Clean break, import path migration]
- [Source: architecture.md — shared/code_tables/ directory layout, lines 3283-3304]
- [Source: architecture.md — shared/data/ layout, lines 3295-3304]
- [Source: architecture.md — Lazy singleton code example, lines 591-605]
- [Source: prd.md — FR18, FR19, FR20: Shared code table access requirements]
- [Source: prd.md — NFR2: <500ms import time, NFR14: Thread-safe singletons]
- [Source: epics.md — Story 1.2 acceptance criteria, lines 249-271]
- [Source: code_tables/loader.py — Existing claims loader (proven pattern)]
- [Source: eligibility/code_tables/loader.py — Existing eligibility loader]
- [Source: prior_auth/code_tables/loader.py — Existing PA loader]
- [Source: code_tables/icd10.py — ICD-10 dot-variant normalization logic]
- [Source: code_tables/timely_filing.py — Filing deadline with _default fallback]
- [Source: eligibility/code_tables/payer_directory.py — Payer lookup returning dict]
- [Source: prior_auth/code_tables/aaa_reject_codes.py — AAA lookup returning detail dict]
- [Source: prior_auth/code_tables/hcr_actions.py — HCR lookup returning detail dict]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

- POS lookup test fix: `lookup_pos("99")` returned "Other Place of Service" — code "99" is valid CMS POS code. Changed test to use `"ZZ"`.
- mypy strict: 7 `no-any-return` errors fixed by adding `typing.cast()` to loader.py cache returns and accessor functions wrapping `load_json()`.

### Completion Notes List

- All 10 data files consolidated in `shared/data/` (4 compressed + 6 plain JSON)
- Service types collision resolved: eligibility `service_types.json` (184 codes) kept as canonical; PA `service_types.json` (22 codes) renamed to `pa_service_types.json`
- `load_json()` now cached (improvement over existing claims loader which was uncached)
- `timely_filing.py` no longer needs its own separate singleton — uses unified loader cache
- 47 new tests (9 loader + 13 table accessors + 25 lookups)
- 1698 total tests pass (was 1651 before Story 1.2)
- mypy strict: 0 errors (12 source files)
- ruff: all checks passed
- D43 compliance verified: no existing files modified

### File List

**Source files (12):**
- `src/claim_validator/shared/data/__init__.py` (NEW)
- `src/claim_validator/shared/data/manifest.json` (NEW)
- `src/claim_validator/shared/data/icd10_cm.json.gz` (COPIED from `data/`)
- `src/claim_validator/shared/data/hcpcs.json.gz` (COPIED from `data/`)
- `src/claim_validator/shared/data/pos_codes.json.gz` (COPIED from `data/`)
- `src/claim_validator/shared/data/taxonomy.json.gz` (COPIED from `data/`)
- `src/claim_validator/shared/data/timely_filing.json` (COPIED from `data/`)
- `src/claim_validator/shared/data/payer_directory.json` (COPIED from `eligibility/data/`)
- `src/claim_validator/shared/data/service_types.json` (COPIED from `eligibility/data/`)
- `src/claim_validator/shared/data/pa_service_types.json` (COPIED+RENAMED from `prior_auth/data/service_types.json`)
- `src/claim_validator/shared/data/hcr_action_codes.json` (COPIED from `prior_auth/data/`)
- `src/claim_validator/shared/data/aaa_reject_codes.json` (COPIED from `prior_auth/data/`)
- `src/claim_validator/shared/code_tables/__init__.py` (NEW)
- `src/claim_validator/shared/code_tables/loader.py` (NEW)
- `src/claim_validator/shared/code_tables/icd10.py` (NEW)
- `src/claim_validator/shared/code_tables/hcpcs.py` (NEW)
- `src/claim_validator/shared/code_tables/taxonomy.py` (NEW)
- `src/claim_validator/shared/code_tables/pos.py` (NEW)
- `src/claim_validator/shared/code_tables/payer_directory.py` (NEW)
- `src/claim_validator/shared/code_tables/service_types.py` (NEW)
- `src/claim_validator/shared/code_tables/hcr_actions.py` (NEW)
- `src/claim_validator/shared/code_tables/aaa_reject_codes.py` (NEW)
- `src/claim_validator/shared/code_tables/timely_filing.py` (NEW)

**Test files (4):**
- `tests/test_shared/test_code_tables/__init__.py` (NEW)
- `tests/test_shared/test_code_tables/test_loader.py` (NEW)
- `tests/test_shared/test_code_tables/test_table_accessors.py` (NEW)
- `tests/test_shared/test_code_tables/test_lookups.py` (NEW)
