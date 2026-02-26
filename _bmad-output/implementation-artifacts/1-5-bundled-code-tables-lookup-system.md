# Story 1.5: Bundled Code Tables & Lookup System

Status: ready-for-dev

## Story

As a **developer**,
I want to look up ICD-10, HCPCS, taxonomy, and Place of Service codes against bundled tables,
so that I can validate codes offline with zero network calls and zero API keys.

## Acceptance Criteria

1. **Given** the installed package, **When** I call the ICD-10-CM lookup with a valid code (e.g., `"J06.9"`), **Then** it returns confirmation the code exists and the code description, and the first lookup loads the compressed table; subsequent lookups use the cached in-memory dict.

2. **Given** the installed package, **When** I call the HCPCS lookup with a valid code (e.g., `"99213"`), **Then** it confirms the code exists in the bundled HCPCS table.

3. **Given** the installed package, **When** I call the taxonomy lookup with a valid taxonomy code, **Then** it confirms the code exists in the bundled NUCC taxonomy table.

4. **Given** the installed package, **When** I call the Place of Service lookup with a valid POS code (e.g., `"11"`), **Then** it confirms the code exists in the bundled POS table.

5. **Given** the timely filing reference data, **When** I query filing deadlines for a common payer, **Then** default timely filing limits are returned (e.g., Medicare = 365 days).

6. **Given** two threads calling code table lookups concurrently, **When** both trigger the first load simultaneously, **Then** the table is loaded exactly once (double-check locking with `threading.Lock`) and both threads receive correct results.

7. **Given** a `data/manifest.json` file, **When** I inspect code table metadata, **Then** each table has version, effective_date, and code_count fields.

## Tasks / Subtasks

- [ ] Task 1: Create seed data files in `src/claim_validator/data/` (AC: #1-#5, #7)
  - [ ] Create `icd10_cm.json.gz` — representative subset (~200 codes for MVP)
  - [ ] Create `hcpcs.json.gz` — representative subset (~100 codes for MVP)
  - [ ] Create `taxonomy.json.gz` — representative subset (~50 codes for MVP)
  - [ ] Create `pos_codes.json.gz` — full set (~99 codes, small enough)
  - [ ] Create `timely_filing.json` — common payer deadlines
  - [ ] Create `manifest.json` — version metadata for each table
- [ ] Task 2: Implement `code_tables/loader.py` (AC: #1, #6)
  - [ ] Generic compressed JSON loader using `gzip` + `json` + `importlib.resources`
  - [ ] Lazy singleton pattern with `threading.Lock` and double-check locking
  - [ ] Stale table warning (log WARNING if >12 months old)
- [ ] Task 3: Implement lookup modules (AC: #1-#5)
  - [ ] `code_tables/icd10.py` — `lookup_icd10(code) -> CodeTableResult | None`
  - [ ] `code_tables/hcpcs.py` — `lookup_hcpcs(code) -> CodeTableResult | None`
  - [ ] `code_tables/taxonomy.py` — `lookup_taxonomy(code) -> CodeTableResult | None`
  - [ ] `code_tables/pos.py` — `lookup_pos(code) -> CodeTableResult | None`
  - [ ] `code_tables/timely_filing.py` — `get_filing_deadline(payer_id) -> int | None`
- [ ] Task 4: Wire up `code_tables/__init__.py` re-exports (AC: all)
- [ ] Task 5: Write tests in `tests/test_code_tables/` (AC: all)
  - [ ] `test_loader.py` — lazy loading, thread safety, compressed JSON
  - [ ] `test_icd10.py` — valid/invalid code lookups
  - [ ] `test_hcpcs.py` — valid/invalid code lookups
  - [ ] `test_taxonomy.py` — valid/invalid code lookups
  - [ ] `test_pos.py` — valid/invalid code lookups
  - [ ] `test_timely_filing.py` — payer deadline lookups
- [ ] Task 6: Verify tooling
  - [ ] `uv run ruff check .` — zero warnings
  - [ ] `uv run mypy src/` — zero errors
  - [ ] `uv run pytest` — all tests pass

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/` — edit existing placeholders in `src/claim_validator/code_tables/` and `src/claim_validator/data/`.

### Previous Story Intelligence (Stories 1.1-1.4)

- All models use `frozen=True`, `strict=False` via `ConfigDict`
- Pattern: `from __future__ import annotations` at top of every file
- Exceptions: `CodeTableError` exists in `exceptions.py` — use it for loading failures
- `pyproject.toml` dependencies: `pydantic>=2.0,<3.0`, `pydantic-settings>=2.0,<3.0`
- Re-export pattern: subpackage `__init__.py` → top-level `__init__.py` with `__all__`
- 79 tests passing, ruff/mypy/pytest all green
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- `data/` directory exists with `.gitkeep`; `code_tables/` directory exists with empty `__init__.py`

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **D1: Code table storage** | Compressed JSON (.json.gz). Standard library `gzip` + `json` only. No extra dependencies |
| **D2: Code table loading** | Lazy singleton with `threading.Lock`. Double-check locking. One-time ~200ms cost |
| **NFR4** | Code table lookup < 1ms (in-memory after first load) |
| **NFR5** | Memory footprint < 100MB with tables loaded |
| **NFR7** | Import time < 500ms — tables loaded lazily, NOT at import time |
| **NFR29** | Package data < 15MB compressed |

### Data File Format

Each `.json.gz` file contains a JSON object mapping `code -> description`:

```json
{
  "J06.9": "Acute upper respiratory infection, unspecified",
  "M54.5": "Low back pain",
  "E11.9": "Type 2 diabetes mellitus without complications"
}
```

The `timely_filing.json` file maps `payer_id -> days`:

```json
{
  "MEDICARE": 365,
  "MEDICAID": 365,
  "BCBS": 180,
  "UNITED": 180,
  "AETNA": 90,
  "CIGNA": 90,
  "_default": 365
}
```

The `manifest.json` contains version metadata:

```json
{
  "icd10_cm": {
    "version": "FY2026",
    "effective_date": "2025-10-01",
    "code_count": 200,
    "source": "CMS/CDC ICD-10-CM"
  },
  "hcpcs": {
    "version": "2026-Q1",
    "effective_date": "2026-01-01",
    "code_count": 100,
    "source": "CMS HCPCS"
  },
  "taxonomy": {
    "version": "26.0",
    "effective_date": "2026-01-01",
    "code_count": 50,
    "source": "NUCC"
  },
  "pos_codes": {
    "version": "2026",
    "effective_date": "2026-01-01",
    "code_count": 99,
    "source": "CMS"
  }
}
```

### Seed Data Strategy

For MVP, bundle **representative subsets** of each code table. This is sufficient for:
- Validating the loader infrastructure works
- Running all unit tests
- Demonstrating the lookup API

Full CMS data can be populated later via a `claim-validator update-codes` CLI (Phase 2). The loader infrastructure handles any size of data file identically.

**ICD-10-CM (~200 codes)**: Include common codes used in primary care, ER, and outpatient settings — the codes most likely to appear in test claims. Examples: J06.9, M54.5, E11.9, I10, Z00.00, etc.

**HCPCS (~100 codes)**: Include common E/M codes (99201-99215), common procedure codes. Note: CPT codes are technically HCPCS Level I (AMA copyrighted), but the 5-digit numeric codes (99213 etc.) are commonly used. We validate FORMAT only and include them in the HCPCS table for existence checking.

**Taxonomy (~50 codes)**: Include common provider types (207Q00000X = Family Medicine, 208D00000X = General Practice, etc.).

**POS (~99 codes)**: Include the full standard set — it's small. (11 = Office, 21 = Inpatient Hospital, 22 = Outpatient Hospital, etc.)

### Loader Implementation (D2)

```python
# src/claim_validator/code_tables/loader.py
import gzip
import json
import logging
import threading
from importlib.resources import files
from typing import Any

from claim_validator.exceptions import CodeTableError

logger = logging.getLogger(__name__)

_locks: dict[str, threading.Lock] = {}
_tables: dict[str, dict[str, str]] = {}
_global_lock = threading.Lock()


def _get_lock(table_name: str) -> threading.Lock:
    """Get or create a per-table lock."""
    if table_name not in _locks:
        with _global_lock:
            if table_name not in _locks:
                _locks[table_name] = threading.Lock()
    return _locks[table_name]


def load_compressed_json(filename: str) -> dict[str, str]:
    """Load a .json.gz file from package data. Lazy singleton."""
    table_name = filename.removesuffix(".json.gz")

    if table_name in _tables:
        return _tables[table_name]

    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:  # Double-check
            return _tables[table_name]

        try:
            data_files = files("claim_validator.data")
            resource = data_files.joinpath(filename)
            raw = resource.read_bytes()
            decompressed = gzip.decompress(raw)
            table = json.loads(decompressed)
        except Exception as exc:
            raise CodeTableError(
                f"Failed to load code table '{filename}': {exc}"
            ) from exc

        _tables[table_name] = table
        return table


def load_json(filename: str) -> Any:
    """Load a plain .json file from package data."""
    try:
        data_files = files("claim_validator.data")
        resource = data_files.joinpath(filename)
        return json.loads(resource.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CodeTableError(
            f"Failed to load '{filename}': {exc}"
        ) from exc
```

### Lookup Module Pattern

Each lookup module follows the same pattern:

```python
# src/claim_validator/code_tables/icd10.py
from __future__ import annotations

from claim_validator.code_tables.loader import load_compressed_json


def lookup_icd10(code: str) -> str | None:
    """Look up an ICD-10-CM code. Returns description or None."""
    table = load_compressed_json("icd10_cm.json.gz")
    # Normalize: strip dots for lookup, try both with and without
    normalized = code.upper().strip()
    return table.get(normalized) or table.get(normalized.replace(".", ""))
```

Return type is `str | None` — returns the description string if found, `None` if not. This is simple and efficient. Validators (Epic 2) wrap this into `Finding` objects.

### Timely Filing Module

```python
# src/claim_validator/code_tables/timely_filing.py
from __future__ import annotations

from claim_validator.code_tables.loader import load_json

_timely_filing: dict[str, int] | None = None


def get_filing_deadline(payer_id: str) -> int | None:
    """Get timely filing deadline in days for a payer.

    Returns the deadline in days, or None if payer unknown
    and no default exists.
    """
    global _timely_filing
    if _timely_filing is None:
        _timely_filing = load_json("timely_filing.json")

    normalized = payer_id.upper().strip()
    deadline = _timely_filing.get(normalized)
    if deadline is None:
        deadline = _timely_filing.get("_default")
    return deadline
```

### Package Data Access — `importlib.resources`

Python 3.11+ pattern for accessing package data:

```python
from importlib.resources import files

# Access data files bundled in src/claim_validator/data/
data_files = files("claim_validator.data")
resource = data_files.joinpath("icd10_cm.json.gz")
raw_bytes = resource.read_bytes()
```

**Critical**: The `data/` directory MUST have an `__init__.py` file (even empty) for `importlib.resources.files()` to find it as a package. Currently it only has `.gitkeep` — **add an empty `__init__.py`**.

### Anti-Patterns to Avoid

- **DO NOT** load tables at import time — violates NFR7 (<500ms import). Use lazy loading
- **DO NOT** use `pathlib.Path(__file__).parent / "data"` — won't work in zipped wheels. Use `importlib.resources`
- **DO NOT** use `pkg_resources` — deprecated, slow. Use `importlib.resources.files()`
- **DO NOT** add handlers to the logger — use `logging.getLogger(__name__)` only; let consumers configure
- **DO NOT** create separate classes for each code table — simple functions are sufficient for lookups
- **DO NOT** use `open()` for reading package data — use `importlib.resources` for wheel compatibility
- **DO NOT** store `dict[str, Any]` for code tables — use `dict[str, str]` (code → description)

### Thread Safety Testing (AC #6)

Use `concurrent.futures.ThreadPoolExecutor` to verify double-check locking:

```python
import concurrent.futures
from claim_validator.code_tables.icd10 import lookup_icd10

def test_concurrent_first_load():
    """Two threads loading simultaneously — table loaded exactly once."""
    results = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        futures = [pool.submit(lookup_icd10, "J06.9") for _ in range(4)]
        results = [f.result() for f in futures]
    assert all(r is not None for r in results)
    assert all(r == results[0] for r in results)
```

### `__init__.py` Re-exports

```python
# src/claim_validator/code_tables/__init__.py
from claim_validator.code_tables.hcpcs import lookup_hcpcs
from claim_validator.code_tables.icd10 import lookup_icd10
from claim_validator.code_tables.pos import lookup_pos
from claim_validator.code_tables.taxonomy import lookup_taxonomy
from claim_validator.code_tables.timely_filing import get_filing_deadline

__all__ = [
    "get_filing_deadline",
    "lookup_hcpcs",
    "lookup_icd10",
    "lookup_pos",
    "lookup_taxonomy",
]
```

These lookup functions are **internal** to the library — used by validators (Epic 2). They are NOT re-exported at the top-level `claim_validator/__init__.py`. They can be imported from `claim_validator.code_tables` by power users.

### Test Directory Structure

```
tests/test_code_tables/
├── __init__.py
├── conftest.py           # Shared fixtures (reset table cache between tests)
├── test_loader.py        # Loader mechanics, thread safety, error handling
├── test_icd10.py         # ICD-10-CM lookups
├── test_hcpcs.py         # HCPCS lookups
├── test_taxonomy.py      # Taxonomy lookups
├── test_pos.py           # POS lookups
└── test_timely_filing.py # Timely filing deadline lookups
```

**Important**: Tests MUST reset the module-level singleton caches between tests. Create a fixture in `conftest.py`:

```python
@pytest.fixture(autouse=True)
def _reset_table_caches():
    """Reset lazy-loaded table caches between tests."""
    from claim_validator.code_tables import loader
    loader._tables.clear()
    loader._locks.clear()
    yield
```

### File Targets

| File | Action | Contents |
|---|---|---|
| `src/claim_validator/data/__init__.py` | Create (empty) | Package marker for `importlib.resources` |
| `src/claim_validator/data/icd10_cm.json.gz` | Create | ~200 ICD-10-CM codes (compressed JSON) |
| `src/claim_validator/data/hcpcs.json.gz` | Create | ~100 HCPCS codes (compressed JSON) |
| `src/claim_validator/data/taxonomy.json.gz` | Create | ~50 taxonomy codes (compressed JSON) |
| `src/claim_validator/data/pos_codes.json.gz` | Create | ~99 POS codes (compressed JSON) |
| `src/claim_validator/data/timely_filing.json` | Create | Payer filing deadlines |
| `src/claim_validator/data/manifest.json` | Create | Version metadata per table |
| `src/claim_validator/code_tables/__init__.py` | Edit | Re-export lookup functions |
| `src/claim_validator/code_tables/loader.py` | Create | Generic lazy loader with threading |
| `src/claim_validator/code_tables/icd10.py` | Create | ICD-10-CM lookup |
| `src/claim_validator/code_tables/hcpcs.py` | Create | HCPCS lookup |
| `src/claim_validator/code_tables/taxonomy.py` | Create | Taxonomy lookup |
| `src/claim_validator/code_tables/pos.py` | Create | POS lookup |
| `src/claim_validator/code_tables/timely_filing.py` | Create | Timely filing deadlines |
| `tests/test_code_tables/__init__.py` | Create | Package marker |
| `tests/test_code_tables/conftest.py` | Create | Cache reset fixture |
| `tests/test_code_tables/test_loader.py` | Create | Loader tests |
| `tests/test_code_tables/test_icd10.py` | Create | ICD-10 lookup tests |
| `tests/test_code_tables/test_hcpcs.py` | Create | HCPCS lookup tests |
| `tests/test_code_tables/test_taxonomy.py` | Create | Taxonomy tests |
| `tests/test_code_tables/test_pos.py` | Create | POS tests |
| `tests/test_code_tables/test_timely_filing.py` | Create | Filing deadline tests |

### References

- [Source: _bmad-output/planning-artifacts/architecture.md#Data Architecture — D1, D2]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns — Lazy loading contract]
- [Source: _bmad-output/planning-artifacts/architecture.md#Structure Patterns — code_tables directory]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 1.5] — Full acceptance criteria
- [Source: CMS/CDC ICD-10-CM] — https://www.cdc.gov/nchs/icd/icd-10-cm/files.html
- [Source: CMS HCPCS] — https://www.cms.gov/medicare/coding-billing/healthcare-common-procedure-system
- [Source: NUCC Taxonomy] — https://www.nucc.org/index.php/code-sets-mainmenu-41/provider-taxonomy-mainmenu-40
- [Source: CMS POS Codes] — https://www.cms.gov/Medicare/Coding/place-of-servicecodes/Place_of_Service_Code_Set
- [Source: Python importlib.resources] — https://docs.python.org/3.11/library/importlib.resources.html

## Dev Agent Record

### Agent Model Used

### Debug Log References

### Completion Notes List

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
