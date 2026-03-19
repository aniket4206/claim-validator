# Story PE-1.4: Settings Integration and Backward Compatibility

Status: done

## Story

As a developer using the existing single-clearinghouse configuration,
I want the new multi-clearinghouse routing to be opt-in,
So that my existing `CLEARINGHOUSE_PROVIDER` env var setup continues to work unchanged.

## Acceptance Criteria

1. **Given** `ClaimValidatorSettings` with only `clearinghouse_config` set (existing pattern), **When** the pipeline runs, **Then** it behaves identically to current behavior — single clearinghouse, no routing
2. **Given** `clearinghouse_configs` dict is set in settings, **Then** a `ClearinghouseClientPool` can be created with all configured providers
3. **Given** `payer_routing_overrides` is set in settings, **Then** those overrides take precedence over bundled default mappings when constructing a `PayerRouter`
4. **Given** the new fields are added, **Then** all existing tests pass without modification

## Tasks / Subtasks

- [x] Task 1: Add new settings fields (AC: #2, #3)
  - [x] 1.1 Add `clearinghouse_configs: dict[str, dict[str, Any]] | None = None` to `ClaimValidatorSettings`
  - [x] 1.2 Add `payer_routing_overrides: dict[str, list[dict[str, Any]]] | None = None` to `ClaimValidatorSettings`
- [x] Task 2: Write tests (AC: #1-#4)
  - [x] 2.1 Test existing `clearinghouse_config` still works (backward compat)
  - [x] 2.2 Test `clearinghouse_configs` can be set and read
  - [x] 2.3 Test `payer_routing_overrides` can be set and read
  - [x] 2.4 Test defaults are None (opt-in behavior)
  - [x] 2.5 Verify all existing tests pass unchanged (2495 passed)

## Dev Notes

### Existing Pattern
- `clearinghouse_config: dict[str, Any] | None = None` — single provider, format `{"provider": "stedi", "api_key": "..."}`
- Used throughout pipeline, orchestrator, workflow stages

### New Fields
- `clearinghouse_configs` (plural) — `{"stedi": {"api_key": "..."}, "claimmd": {"account_key": "..."}}` — enables `ClearinghouseClientPool`
- `payer_routing_overrides` — `{"PAYER_ID": [{"clearinghouse": "stedi", ...}]}` — passed to `PayerRouter(custom_mappings=...)`

### Scope Boundaries
- This story ONLY adds settings fields
- Does NOT wire them into the pipeline/orchestrator (future integration story)
- Does NOT modify existing `clearinghouse_config` usage

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Added `clearinghouse_configs` and `payer_routing_overrides` to ClaimValidatorSettings. Both default to None (opt-in). Existing `clearinghouse_config` (singular) untouched.
- Task 2: 9 new tests — defaults, explicit values, env vars, backward compat, coexistence. 2495 total passing, zero regressions.

### File List

- `src/claim_validator/conf.py` (modified — 2 new fields)
- `tests/test_conf.py` (modified — TestMultiClearinghouseSettings class)
