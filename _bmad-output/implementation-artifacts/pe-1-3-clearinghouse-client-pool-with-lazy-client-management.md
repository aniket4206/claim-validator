# Story PE-1.3: ClearinghouseClientPool with Lazy Client Management

Status: done

## Story

As a developer,
I want a single pool that manages multiple clearinghouse clients simultaneously,
So that I can submit claims to any clearinghouse without manually instantiating clients.

## Acceptance Criteria

1. **Given** a `ClearinghouseClientPool` initialized with a dict of provider configs, **When** `get_client(provider_name)` is called, **Then** it lazy-instantiates the correct `BaseClearinghouseClient` subclass on first call and caches it for reuse
2. **Given** a pool, **When** `submit_claim(claim, payer_id)` is called, **Then** it routes via `PayerRouter` then delegates to the correct client
3. **Given** a pool, **When** `check_eligibility(request, payer_id)` is called, **Then** it routes via `PayerRouter` then delegates to the correct client
4. **Given** a pool, **Then** clients are only instantiated when first requested, not at pool construction

## Tasks / Subtasks

- [x] Task 1: Create ClearinghouseClientPool class (AC: #1-#4)
  - [x] 1.1 Create `src/claim_validator/clearinghouse/pool.py` with `ClearinghouseClientPool`
  - [x] 1.2 Implement `get_client(provider_name)` with lazy instantiation via existing factory
  - [x] 1.3 Implement `submit_claim(claim_data, payer_id)` with PayerRouter routing
  - [x] 1.4 Implement `check_eligibility(request, payer_id)` with PayerRouter routing
  - [x] 1.5 Support context manager for cleanup (`close()`, `__enter__`, `__exit__`)
- [x] Task 2: Write tests (AC: #1-#4)
  - [x] 2.1 Create `tests/test_clearinghouse/test_pool.py`
  - [x] 2.2 Test lazy instantiation (client not created until get_client)
  - [x] 2.3 Test client caching (same object on repeated calls)
  - [x] 2.4 Test submit_claim routes to correct provider
  - [x] 2.5 Test check_eligibility routes to correct provider
  - [x] 2.6 Test unknown provider raises ConfigurationError
  - [x] 2.7 Test close() cleans up all instantiated clients

## Dev Notes

### Previous Story Intelligence

- `PayerRouter` at `routing/router.py` — `route(payer_id)` returns highest-priority `PayerRoute`
- `PayerRoute.clearinghouse` gives the provider name (e.g. "stedi")
- `get_clearinghouse_client(provider, **config)` in `clearinghouse/factory.py` creates clients
- `BaseClearinghouseClient` in `clearinghouse/base.py` — ABC with `submit_claim()`, `check_eligibility()`, `close()`
- Existing providers: stedi, claimmd, waystar (lazy-imported in factory)
- Avoid circular imports — `routing/__init__.py` does NOT eagerly re-export

### Implementation Approach

- Constructor takes `configs: dict[str, dict[str, Any]]` (provider -> config kwargs)
- Optional `router: PayerRouter | None` — creates default if None
- `get_client()` uses `get_clearinghouse_client()` factory, caches in `_clients` dict
- Thread-safe client instantiation via Lock
- `close()` iterates cached clients and calls `close()` on each

### References

- [Source: src/claim_validator/clearinghouse/factory.py — get_clearinghouse_client()]
- [Source: src/claim_validator/clearinghouse/base.py — BaseClearinghouseClient]
- [Source: src/claim_validator/routing/router.py — PayerRouter]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Created `ClearinghouseClientPool` with lazy client instantiation via existing factory, double-check locking for thread safety, PayerRouter-based routing for `submit_claim()` and `check_eligibility()`, context manager support.
- Task 2: 11 tests covering lazy instantiation, caching, routing, unknown provider errors, lifecycle/cleanup.
- Full regression: 2479 passed (was 2468), zero regressions.

### File List

- `src/claim_validator/clearinghouse/pool.py` (new)
- `tests/test_clearinghouse/test_pool.py` (new)
