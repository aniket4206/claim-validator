# Story PE-1.1: Payer Route Model and Default Mapping Data

Status: done

## Story

As a developer,
I want a bundled payer-to-clearinghouse mapping table loaded from compressed JSON,
So that the library knows which clearinghouse handles each payer without manual configuration.

## Acceptance Criteria

1. **Given** the library is installed with default data, **When** `load_default_mapping()` is called, **Then** it returns a dict of ~2,000 payer ID -> `PayerRoute` mappings loaded from `payer_routing.json.gz`
2. **Given** the mapping is loaded, **Then** `PayerRoute` is a frozen dataclass with fields: `clearinghouse` (str), `payer_id_at_clearinghouse` (str), `priority` (int), `supports` (frozenset of str)
3. **Given** the mapping file exists in `shared/data/`, **Then** it follows the same gzip+JSON lazy-loading pattern as existing code tables (via `loader.load_compressed_json()`)
4. **Given** concurrent threads call `load_default_mapping()`, **Then** loading is thread-safe with double-check locking (reuses existing `_get_lock()` / `_tables` infrastructure in `loader.py`)

## Tasks / Subtasks

- [x] Task 1: Create PayerRoute model (AC: #2)
  - [x] 1.1 Create `src/claim_validator/routing/__init__.py` (empty package marker)
  - [x] 1.2 Create `src/claim_validator/routing/models.py` with frozen `PayerRoute` dataclass
  - [x] 1.3 Add `PayerRoutingError` exception to `src/claim_validator/exceptions.py`
- [x] Task 2: Create payer routing code table accessor (AC: #1, #3, #4)
  - [x] 2.1 Create `src/claim_validator/shared/code_tables/payer_routing.py` with `get_payer_routing_table()` and `load_default_mapping()` functions
  - [x] 2.2 Re-export `load_default_mapping` and `get_payer_routing_table` from `shared/code_tables/__init__.py`
- [x] Task 3: Create bundled payer_routing.json.gz data file (AC: #1)
  - [x] 3.1 Create `src/claim_validator/shared/data/payer_routing.json.gz` with ~2,000 payer-to-clearinghouse route entries
  - [x] 3.2 Data format: `{"PAYER_ID": [{"clearinghouse": "...", "payer_id_at_clearinghouse": "...", "priority": N, "supports": ["837P", ...]}]}`
  - [x] 3.3 Include routes for the 4 supported clearinghouses: stedi, claimmd, waystar, change (and future availity)
- [x] Task 4: Write tests (AC: #1-#4)
  - [x] 4.1 Create `tests/test_routing/__init__.py` and `tests/test_routing/conftest.py`
  - [x] 4.2 Create `tests/test_routing/test_models.py` — PayerRoute immutability, equality, hashing
  - [x] 4.3 Create `tests/test_routing/test_payer_routing.py` — loader caching, singleton identity (`is`), thread safety (8 threads), unknown payer returns empty list, minimum 2000 entries, data shape validation
  - [x] 4.4 Create `tests/test_routing/test_exceptions.py` — PayerRoutingError hierarchy

## Dev Notes

### Architecture Decisions

- **D44 (Open-Core Split):** Payer routing is core open-source functionality. No premium stubs, no feature flags. Must work standalone without platform installed.
- **D46 (Payer Routing Engine):** PayerRouter resolves payer ID to clearinghouse via bundled mapping. Lazy-loaded, thread-safe, offline-first. Override via `ClaimValidatorSettings.payer_routing_overrides`.
- **D47 (Multi-Clearinghouse Pool):** This story creates the data layer. Story 1.2 adds `PayerRouter` class. Story 1.3 adds `ClearinghouseClientPool`. Story 1.4 adds settings integration.

### Existing Code Table Pattern to Follow

The project has a well-established lazy-loading code table pattern. **You MUST reuse the existing infrastructure, NOT create new loading logic.**

**Loader:** `src/claim_validator/shared/code_tables/loader.py`
```python
# Double-check locking with per-table locks
_global_lock = threading.Lock()
_locks: dict[str, threading.Lock] = {}
_tables: dict[str, Any] = {}

def load_compressed_json(filename: str) -> dict[str, str]:
    """Load .json.gz from shared/data/ with lazy singleton caching."""
    table_name = filename.removesuffix(".json.gz")
    if table_name in _tables:
        return cast(dict[str, str], _tables[table_name])
    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:
            return cast(dict[str, str], _tables[table_name])
        data_pkg = files("claim_validator.shared.data")
        raw = data_pkg.joinpath(filename).read_bytes()
        table = json.loads(gzip.decompress(raw))
        _tables[table_name] = table
        return table
```

**Accessor pattern** (from `shared/code_tables/icd10.py`):
```python
def get_icd10_table() -> dict[str, str]:
    return load_compressed_json("icd10_cm.json.gz")

def lookup_icd10(code: str) -> str | None:
    table = get_icd10_table()
    return table.get(code.upper().strip())
```

**Your accessor** (`shared/code_tables/payer_routing.py`) should:
1. Call `load_compressed_json("payer_routing.json.gz")` to get raw dict
2. Convert raw JSON entries into `PayerRoute` frozen dataclass instances (cache this conversion)
3. Expose `get_payer_routing_table() -> dict[str, list[PayerRoute]]`
4. Expose `load_default_mapping() -> dict[str, list[PayerRoute]]` (alias or identical to above)

### PayerRoute Model Specification

```python
# src/claim_validator/routing/models.py
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class PayerRoute:
    """A single payer-to-clearinghouse route entry."""
    clearinghouse: str                    # e.g. "stedi", "claimmd", "change"
    payer_id_at_clearinghouse: str        # ID used with that clearinghouse
    priority: int                         # 1 = primary, 2 = first fallback, etc.
    supports: frozenset[str]             # e.g. frozenset({"837P", "270/271"})
```

**Critical:** Use `@dataclass(frozen=True)`, NOT Pydantic. This is a simple value object — Pydantic overhead is unnecessary. `frozen=True` makes it immutable and hashable. `slots=True` for memory efficiency since we create ~2,000+ of these.

### Data File Format

`payer_routing.json.gz` structure:
```json
{
  "60054": [
    {
      "clearinghouse": "stedi",
      "payer_id_at_clearinghouse": "AETNA",
      "priority": 1,
      "supports": ["837P", "270/271", "276/277"]
    },
    {
      "clearinghouse": "change",
      "payer_id_at_clearinghouse": "60054",
      "priority": 2,
      "supports": ["837P", "837I", "270/271", "276/277"]
    }
  ]
}
```

**Key constraints:**
- Top level: payer ID (str) -> list of route dicts
- Routes sorted by priority ascending (1 = best)
- `supports` is a list of transaction type strings in JSON, converted to `frozenset` in Python
- Minimum ~2,000 payer entries
- Include major US payers (Aetna, UnitedHealthcare, BCBS affiliates, Cigna, Humana, Medicare, Medicaid by state, etc.)

### Exception to Add

```python
# In src/claim_validator/exceptions.py
class PayerRoutingError(ClaimValidatorError):
    """Payer routing resolution failure (unknown payer ID, no routes)."""
```

This exception will be used by Story 1.2's `PayerRouter.route()` when a payer ID has no mappings.

### Project Structure Notes

- New `routing/` package: `src/claim_validator/routing/` — dedicated package for payer routing (NOT inside `clearinghouse/` — routing is a separate concern that connects payers to clearinghouses)
- Code table accessor: `src/claim_validator/shared/code_tables/payer_routing.py` — follows existing code table pattern, lives alongside `icd10.py`, `hcpcs.py`, `payer_directory.py`, etc.
- Data file: `src/claim_validator/shared/data/payer_routing.json.gz` — follows existing data file location
- Tests: `tests/test_routing/` — new test directory for routing module
- NO changes to `conf.py` in this story (settings integration is Story 1.4)
- NO changes to clearinghouse module (pool is Story 1.3)

### Anti-Patterns to Avoid

1. **DO NOT** create a new lazy-loading mechanism. Reuse `loader.load_compressed_json()`.
2. **DO NOT** use Pydantic for `PayerRoute`. It's a simple frozen dataclass — Pydantic adds unnecessary overhead for thousands of instances.
3. **DO NOT** put routing code inside `clearinghouse/`. Routing is a separate concern.
4. **DO NOT** add settings fields in this story. That's Story 1.4.
5. **DO NOT** create `PayerRouter` class in this story. That's Story 1.2.
6. **DO NOT** use `json.load()` directly — always go through `loader.load_compressed_json()`.
7. **DO NOT** log payer IDs in error messages (not PHI per se, but avoid leaking business data in logs).
8. **DO NOT** create the data file manually by hand-typing — write a generation script or use a well-known payer registry source.

### Testing Requirements

Follow existing test patterns exactly:

```python
# tests/test_routing/test_payer_routing.py
class TestLoadDefaultMapping:
    def setup_method(self) -> None:
        _clear_cache()  # Reset loader cache between tests

    def test_returns_dict(self) -> None:
        mapping = load_default_mapping()
        assert isinstance(mapping, dict)
        assert len(mapping) >= 2000

    def test_cached_same_object(self) -> None:
        m1 = load_default_mapping()
        m2 = load_default_mapping()
        assert m1 is m2  # Singleton identity

    def test_values_are_payer_route_lists(self) -> None:
        mapping = load_default_mapping()
        for payer_id, routes in mapping.items():
            assert isinstance(routes, list)
            for route in routes:
                assert isinstance(route, PayerRoute)

    def test_routes_sorted_by_priority(self) -> None:
        mapping = load_default_mapping()
        for routes in mapping.values():
            priorities = [r.priority for r in routes]
            assert priorities == sorted(priorities)

    def test_thread_safe_concurrent_load(self) -> None:
        # 8 threads, all get same object identity
        ...

    def test_supports_is_frozenset(self) -> None:
        mapping = load_default_mapping()
        for routes in mapping.values():
            for route in routes:
                assert isinstance(route.supports, frozenset)
```

```python
# tests/test_routing/test_models.py
class TestPayerRoute:
    def test_frozen_immutable(self) -> None:
        route = PayerRoute(clearinghouse="stedi", payer_id_at_clearinghouse="AETNA", priority=1, supports=frozenset({"837P"}))
        with pytest.raises(FrozenInstanceError):
            route.clearinghouse = "other"

    def test_hashable(self) -> None:
        route = PayerRoute(...)
        {route}  # Must be hashable

    def test_equality(self) -> None:
        r1 = PayerRoute(clearinghouse="stedi", payer_id_at_clearinghouse="X", priority=1, supports=frozenset())
        r2 = PayerRoute(clearinghouse="stedi", payer_id_at_clearinghouse="X", priority=1, supports=frozenset())
        assert r1 == r2
```

### Quality Requirements

- `from __future__ import annotations` at top of every new file
- All public classes and functions must have docstrings
- `ruff check` and `ruff format` must pass
- `mypy --strict` must pass (with pydantic plugin)
- All existing tests must continue to pass (2427 tests)
- Target >90% coverage for new code

### References

- [Source: _bmad-output/planning-artifacts/epics-platform-extension.md#Epic 1 Story 1.1]
- [Source: _bmad-output/planning-artifacts/architecture.md#D44-D47]
- [Source: src/claim_validator/shared/code_tables/loader.py — lazy-loading pattern]
- [Source: src/claim_validator/shared/code_tables/icd10.py — accessor pattern]
- [Source: src/claim_validator/shared/code_tables/payer_directory.py — lookup pattern]
- [Source: src/claim_validator/shared/code_tables/__init__.py — re-export pattern]
- [Source: src/claim_validator/exceptions.py — exception hierarchy]
- [Source: tests/test_shared/test_code_tables/test_loader.py — test patterns]
- [Source: _bmad-output/project-context.md — 62 implementation rules]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Created `routing/` package with `PayerRoute` frozen dataclass (`@dataclass(frozen=True, slots=True)`) and `PayerRoutingError` exception. 12 tests pass.
- Task 2: Created `shared/code_tables/payer_routing.py` accessor with `load_default_mapping()` and `get_payer_routing_table()`. Uses existing `loader.load_compressed_json()` infrastructure with an additional double-check locking layer for the PayerRoute conversion cache.
- Task 3: Generated `payer_routing.json.gz` with 2,201 payer entries across 4,485 routes to 5 clearinghouses (stedi, claimmd, waystar, change, availity). Includes Medicare, Medicaid (all 50 states), major commercial (Aetna, UHC, Cigna, Humana), BCBS affiliates, Tricare, VA, regional plans, CHIP, and more. File size: 28KB compressed.
- Task 4: 24 new tests covering model immutability/equality/hashing, exception hierarchy, loader caching/singleton identity, thread safety (8 threads), data shape validation, minimum entry count, known clearinghouse/transaction-type validation.
- Full regression: 2451 passed (was 2427), zero regressions. Ruff check + format clean.

### File List

- `src/claim_validator/routing/__init__.py` (new)
- `src/claim_validator/routing/models.py` (new)
- `src/claim_validator/shared/code_tables/payer_routing.py` (new)
- `src/claim_validator/shared/code_tables/__init__.py` (modified — re-exports)
- `src/claim_validator/shared/data/payer_routing.json.gz` (new)
- `src/claim_validator/exceptions.py` (modified — PayerRoutingError)
- `tests/test_routing/__init__.py` (new)
- `tests/test_routing/test_models.py` (new)
- `tests/test_routing/test_payer_routing.py` (new)
- `tests/test_routing/test_exceptions.py` (new)
- `scripts/generate_payer_routing.py` (new — data generation utility)
