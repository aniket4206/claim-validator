# Story PE-1.2: PayerRouter with Route and Fallback

Status: done

## Story

As a developer,
I want to resolve a payer ID to the correct clearinghouse provider,
So that claims are automatically routed without manual clearinghouse selection.

## Acceptance Criteria

1. **Given** a `PayerRouter` initialized with default or custom mappings, **When** `route(payer_id)` is called with a known payer ID, **Then** it returns the highest-priority `PayerRoute` for that payer
2. **Given** a `PayerRouter`, **When** `route_with_fallback(payer_id)` is called, **Then** it returns an ordered list of all `PayerRoute` options for that payer sorted by priority
3. **Given** a `PayerRouter`, **When** `route(payer_id)` or `route_with_fallback(payer_id)` is called with an unknown payer ID, **Then** it raises `PayerRoutingError` with a descriptive message
4. **Given** a `PayerRouter`, **Then** it is stateless and thread-safe (no mutable instance state after construction)

## Tasks / Subtasks

- [x] Task 1: Create PayerRouter class (AC: #1, #2, #3, #4)
  - [x] 1.1 Create `src/claim_validator/routing/router.py` with `PayerRouter` class
  - [x] 1.2 Implement `route(payer_id) -> PayerRoute` — returns highest-priority route
  - [x] 1.3 Implement `route_with_fallback(payer_id) -> list[PayerRoute]` — returns all routes sorted by priority
  - [x] 1.4 Raise `PayerRoutingError` for unknown payer IDs
  - [x] 1.5 Accept optional custom mappings override in constructor
- [x] Task 2: Re-export and integrate (AC: #1)
  - [x] 2.1 Docstring-based public API reference in `routing/__init__.py` (no eager re-export to avoid circular import with code_tables)
- [x] Task 3: Write tests (AC: #1-#4)
  - [x] 3.1 Create `tests/test_routing/test_router.py` with comprehensive tests
  - [x] 3.2 Test `route()` returns highest-priority PayerRoute for known payer
  - [x] 3.3 Test `route_with_fallback()` returns ordered list
  - [x] 3.4 Test unknown payer raises PayerRoutingError
  - [x] 3.5 Test custom mappings override default
  - [x] 3.6 Test thread safety with concurrent route calls
  - [x] 3.7 Test statelessness (no side effects between calls)

## Dev Notes

### Architecture Decisions

- **D46 (Payer Routing Engine):** `PayerRouter` is the resolution interface. Stateless, thread-safe, offline-first. Override via custom mappings dict passed to constructor.
- **D47 (Multi-Clearinghouse Pool):** Story 1.3 will use `PayerRouter` inside `ClearinghouseClientPool`. This story just creates the router.

### Previous Story Intelligence (PE-1.1)

- `PayerRoute` frozen dataclass exists at `src/claim_validator/routing/models.py`
- `load_default_mapping()` returns `dict[str, list[PayerRoute]]` from `shared/code_tables/payer_routing.py`
- `PayerRoutingError` exception exists at `src/claim_validator/exceptions.py`
- 2,201 payer entries in `payer_routing.json.gz`, routes sorted by priority
- Routing package: `src/claim_validator/routing/` already has `__init__.py` and `models.py`
- Tests at `tests/test_routing/` — follow same patterns

### Implementation Specification

```python
# src/claim_validator/routing/router.py
class PayerRouter:
    """Resolves payer IDs to clearinghouse routes.

    Stateless after construction. Thread-safe (mapping is frozen after init).
    """

    def __init__(
        self,
        custom_mappings: dict[str, list[PayerRoute]] | None = None,
    ) -> None:
        # Merge: custom overrides take precedence over defaults
        defaults = load_default_mapping()
        if custom_mappings:
            merged = {**defaults, **custom_mappings}
        else:
            merged = defaults
        # Store as immutable reference — no mutation after init
        self._mappings = merged

    def route(self, payer_id: str) -> PayerRoute:
        """Return the highest-priority route for the given payer.

        Raises PayerRoutingError if payer_id is unknown.
        """
        routes = self._mappings.get(payer_id.upper().strip())
        if not routes:
            raise PayerRoutingError(f"No routes found for payer ID '{payer_id}'")
        return routes[0]  # Already sorted by priority

    def route_with_fallback(self, payer_id: str) -> list[PayerRoute]:
        """Return all routes for the payer, ordered by priority.

        Raises PayerRoutingError if payer_id is unknown.
        """
        routes = self._mappings.get(payer_id.upper().strip())
        if not routes:
            raise PayerRoutingError(f"No routes found for payer ID '{payer_id}'")
        return list(routes)  # Return a copy
```

### Anti-Patterns to Avoid

1. **DO NOT** store mutable state — `PayerRouter` must be stateless after `__init__`
2. **DO NOT** normalize payer IDs during init (normalize on lookup only)
3. **DO NOT** create the `ClearinghouseClientPool` — that's Story 1.3
4. **DO NOT** add settings integration — that's Story 1.4
5. **DO NOT** add filter-by-transaction-type to `route()` — keep it simple, Story 1.3 can filter

### Testing Requirements

- Test with real data (default mappings from payer_routing.json.gz)
- Test with custom mappings that override specific payers
- Test payer ID normalization (case-insensitive, whitespace trimming)
- Test PayerRoutingError message content
- Test thread safety (8 concurrent route calls)
- Test that `route()` returns same PayerRoute as `route_with_fallback()[0]`

### References

- [Source: _bmad-output/planning-artifacts/epics-platform-extension.md#Story 1.2]
- [Source: src/claim_validator/routing/models.py — PayerRoute dataclass]
- [Source: src/claim_validator/shared/code_tables/payer_routing.py — load_default_mapping()]
- [Source: src/claim_validator/exceptions.py — PayerRoutingError]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Created `PayerRouter` class with `route()` and `route_with_fallback()`. Constructor accepts optional `custom_mappings` that override defaults. Custom mappings are sorted by priority during init. Returns defensive copies from `route_with_fallback()`. Payer ID normalization (uppercase + strip) on lookup.
- Task 2: Avoided eager re-export in `routing/__init__.py` to prevent circular import chain (code_tables/__init__ -> payer_routing -> routing.models -> routing/__init__ -> routing.router -> code_tables.payer_routing). Import directly from `routing.router`.
- Task 3: 17 tests covering route resolution, fallback ordering, case insensitivity, whitespace handling, unknown payer errors, custom mapping overrides, thread safety (8 threads), and statelessness.
- Full regression: 2468 passed (was 2451), zero regressions. Ruff clean.

### File List

- `src/claim_validator/routing/router.py` (new)
- `src/claim_validator/routing/__init__.py` (modified — docstring API ref, no eager re-export)
- `tests/test_routing/test_router.py` (new)
