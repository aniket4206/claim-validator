# Story PE-1.5: Update Package Extras for New Clearinghouses

Status: done

## Story

As a developer,
I want to install only the clearinghouse clients I need via pip extras,
So that I don't pull unnecessary dependencies.

## Acceptance Criteria

1. `pip install claim-validator[change]` installs httpx
2. `[availity]`, `[resilience]`, `[all-clearinghouses]` extras available
3. `[resilience]` installs `tenacity>=8.2`
4. `[all-clearinghouses]` installs httpx for all clearinghouse clients
5. Existing extras (`[ai]`, `[server]`) remain unchanged

## Tasks / Subtasks

- [x] Task 1: Update pyproject.toml extras (AC: #1-#5)
  - [x] 1.1 Add `stedi`, `claimmd`, `waystar` extras (all need httpx>=0.27)
  - [x] 1.2 Add `change = ["httpx>=0.27"]`
  - [x] 1.3 Add `availity = ["httpx>=0.27"]`
  - [x] 1.4 Add `resilience = ["tenacity>=8.2"]`
  - [x] 1.5 Add `all-clearinghouses = ["httpx>=0.27", "tenacity>=8.2"]`
  - [x] 1.6 Updated `all` extra to include `all-clearinghouses`
- [x] Task 2: Verify (AC: #5)
  - [x] 2.1 Existing extras (ai, server, django, fastapi, dev) unchanged
  - [x] 2.2 `pip install -e .` succeeds, 2495 tests pass

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (1M context)

### Debug Log References

### Completion Notes List

- Task 1: Added 7 new extras to pyproject.toml: stedi, claimmd, waystar, change, availity, resilience, all-clearinghouses. Updated `all` to include `all-clearinghouses`.
- Task 2: `pip install -e .` succeeds. 2495 tests pass, zero regressions.

### File List

- `pyproject.toml` (modified — new optional-dependencies)
