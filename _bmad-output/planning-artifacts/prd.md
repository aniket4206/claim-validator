---
stepsCompleted: ['step-01-init', 'step-02-discovery', 'step-03-success', 'step-04-journeys', 'step-05-domain', 'step-06-innovation', 'step-07-project-type', 'step-08-scoping', 'step-09-functional', 'step-10-nonfunctional', 'step-11-polish', 'step-12-complete']
inputDocuments:
  - '_bmad-output/planning-artifacts/product-brief-healthcare-claim-analyzer-2026-02-27.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/project-context.md'
  - 'docs/Claim-Eligibility-Check-Implementation-Guide.md'
workflowType: 'prd'
documentCounts:
  briefs: 1
  research: 0
  brainstorming: 0
  projectDocs: 3
classification:
  projectType: 'developer_tool'
  domain: 'healthcare'
  complexity: 'high'
  projectContext: 'brownfield'
---

# Product Requirements Document — claim-validator v3.0 Refactoring

**Author:** aniket
**Date:** 2026-03-02

## Executive Summary

Full codebase refactoring of `claim-validator` to eliminate duplicate code across three modules (claims, eligibility, prior auth), consolidate shared validation logic into common utilities, and build a unified sequential pipeline (Eligibility → Prior Auth → Claim Validation).

**Core Problem:** Changing one validation rule (e.g., NPI Luhn check) requires modifying 3+ files across 3 modules. De-identification, pipeline orchestration, and code table access are each implemented independently per module with near-identical logic.

**Solution:** Extract all shared logic into `shared/` module. Build a unified `process_claim()` API that orchestrates the full sequential flow with validation passthrough — rules validated at an earlier stage are trusted downstream. Ship as v3.0 with clean internal path changes.

**Key Decisions:**
- 4 public APIs: 3 existing (`validate()`, `check_eligibility()`, `submit_prior_auth()`) + 1 new (`process_claim()`)
- Clean break at v3.0 — new internal paths, no re-exports or deprecation shims
- Public API signatures unchanged — only internal structure changes
- All Python code refactored; existing .md documentation preserved

## Success Criteria

### User Success

| Criteria | Metric | Target |
|---|---|---|
| Single change propagation | Files edited to fix a shared validation rule | 1 file, not 3 |
| Unified pipeline | Full flow (Eligibility → PA → Claim) via single API call | `process_claim(request) -> WorkflowResult` |
| Standalone APIs preserved | `validate()`, `check_eligibility()`, `submit_prior_auth()` callable independently | 100% backward compatible signatures |
| No redundant validation | NPI check runs once in sequential mode, trusted downstream | Zero duplicate checks |

### Technical Success

| Criteria | Metric | Target |
|---|---|---|
| Zero duplicate validators | No validation function exists in more than one file | 0 duplicates |
| Shared utility module | Common validators in single location | `shared/` module |
| De-identification consolidation | Base de-identifier with domain config | 1 base class |
| Pipeline consolidation | Configurable pipeline engine | 1 base pipeline |
| Code reduction | Reduction in duplicated validator code | >30% |
| Test coverage maintained | All existing test scenarios covered | >= current coverage % |

### Business Success

| Criteria | Metric | Target |
|---|---|---|
| Maintenance effort | Files touched per bug fix | Single-point-of-change |
| Contributor onboarding | Patterns to learn | 1 pattern, not 3 |
| Future module cost | Effort to add new module (e.g., 837 submission) | <50% vs PA module build |

### Measurable Outcomes

- Every shared validation rule has exactly one canonical implementation
- Unified pipeline chains stages with validation result passthrough
- Full test suite passes against refactored code
- No regression in rule-based validation catch rates

## Product Scope

### MVP Strategy

**Approach:** Problem-solving refactoring — extract shared code first, then build unified pipeline on top. MVP complete when: (1) zero duplicate validators, (2) all 3 existing APIs use shared internals, (3) `process_claim()` orchestrates the full flow.

**Resource:** Solo developer (aniket), existing test suite as safety net.

### Phase 1 — MVP

| # | Capability | Rationale |
|---|---|---|
| 1 | Shared validators (`shared/validators/`) | NPI, date, member ID, demographics, diagnosis, procedure — written once |
| 2 | Base de-identifier (`shared/deidentifier/`) | One engine with domain config, replaces 3 implementations |
| 3 | Base pipeline engine (`shared/pipeline/`) | One configurable class, replaces 3 pipeline classes |
| 4 | Refactored claim module | `validate()` uses shared internals |
| 5 | Refactored eligibility module | `check_eligibility()` uses shared internals |
| 6 | Refactored prior auth module | `submit_prior_auth()` uses shared internals |
| 7 | Unified code table access (`shared/code_tables/`) | Single layer for ICD-10, HCPCS, taxonomy, payer directory, service types |
| 8 | WorkflowResult model | Per-stage results, execution times, stopped_at |
| 9 | Workflow orchestrator (`workflow/`) | `process_claim()` — Eligibility → PA determination → PA (if needed) → Claim |
| 10 | Validation passthrough | Downstream stages skip already-validated rules |
| 11 | All existing tests passing | Migrated suite with zero regressions |
| 12 | HIPAA compliance tests | Shared de-identifier verified for all 3 domains |

### Phase 2 — Growth

- Smart validation skipping configuration — per-stage rules for what to skip/re-run
- Workflow state object — carries rich context between stages
- Configurable stage ordering — custom stage sequences
- Performance benchmark suite — automated old vs new comparison
- `WorkflowResult` JSON serialization for logging/audit

### Phase 3 — Expansion

- Plugin system — third-party stages and validators
- New transaction types (835 remittance, 837P/837I) as pipeline stages
- Async pipeline support for batch processing
- Community validator registry

### Risk Mitigation

| Risk Type | Risk | Mitigation |
|---|---|---|
| Technical | Shared validators don't match domain-specific behavior | Diff-test: run old and new against same inputs, assert identical outputs |
| Technical | Pipeline consolidation introduces ordering bugs | Existing test suite — all tests must pass before merge |
| Technical | Performance regression from abstraction layers | Benchmark old vs new; <50ms rule-based budget is hard gate |
| Security | Shared de-identifier misses PHI field | Automated HIPAA test suite for all 3 domains |
| Security | Unified pipeline leaks PHI between stages | Fresh input per stage; PHI objects not passed to AI phase |
| Scope | Refactoring creep — temptation to redesign models, settings | Hard rule: only refactor validators, de-identifiers, pipelines |
| Resource | Solo developer, large scope | Incremental: shared → claim → eligibility → PA → workflow |

## User Journeys

### Journey 1: "Raj" — Full Workflow, One Call (Primary - Success Path)

**Opening Scene:** Raj is a senior Python dev at a health-tech company. His platform calls `check_eligibility()`, manually checks if PA is needed, calls `submit_prior_auth()`, and finally `validate()`. He has 200+ lines of glue code stitching these calls together.

**Rising Action:** He discovers `process_claim()`. Replaces 50+ lines of orchestration with a single call. The pipeline runs eligibility first, determines PA requirement from the 271 response, submits PA if required, and validates the claim. NPI, member ID, and demographics validated once at eligibility and trusted downstream.

**Climax:** A payer rejects claims with invalid service type codes. Raj fixes the shared `ServiceTypeValidator` in one file. The fix applies to all three modules instantly.

**Resolution:** Orchestration layer shrinks from 200 lines to 20. New devs learn one pipeline pattern, not three.

**Requirements revealed:** Unified pipeline API, validation passthrough, sequential execution, single-point-of-change.

### Journey 2: "Priya" — New Adopter (Primary - Onboarding)

**Opening Scene:** Priya is building a telehealth platform with no X12 EDI expertise. She wants eligibility + PA + claim validation in her FastAPI app.

**Rising Action:** She finds `process_claim()`, passes a dict with patient info, procedure codes, and payer ID. The pipeline returns a typed `WorkflowResult` with eligibility status, PA outcome, and claim validation results.

**Climax:** When eligibility fails, the pipeline stops early and reports exactly why — no wasted PA or claim validation calls.

**Resolution:** Ships her MVP in a weekend. Never touched X12, never thought about which stage validates what.

**Requirements revealed:** Dict-in/model-out, early termination, clear per-stage error reporting, zero domain knowledge for basic usage.

### Journey 3: Aniket — Maintainer Bug Fix (Contributor - Pain Path)

**Opening Scene:** NPI Luhn check has a bug. Currently exists in 3 files across 3 modules.

**Rising Action:** Opens `claim_validator/shared/validators/npi.py` — the single canonical implementation. Fixes the bug once.

**Climax:** Runs test suite once. All NPI tests across claims, eligibility, and PA pass. No grep-and-pray.

**Resolution:** 30-minute multi-file fix becomes 5-minute single-file fix.

**Requirements revealed:** Shared validator module, single canonical implementation, unified test coverage, validator registration per stage.

### Journey 4: "DevOps Dan" — Monitoring (Secondary - Operations)

**Opening Scene:** Dan monitors three separate pipeline metrics with three different error patterns. Debugging requires identifying which module threw which error.

**Rising Action:** Unified pipeline gives a single `WorkflowResult` with per-stage execution times, findings, and clear stop-point identification.

**Climax:** Clearinghouse timeout during PA: `WorkflowResult` shows eligibility passed (120ms), PA failed (`CLEARINGHOUSE_PA_TIMEOUT`, 30002ms), claim skipped.

**Resolution:** One dashboard for the full workflow. Debugging takes minutes, not hours.

**Requirements revealed:** Per-stage metrics, consistent error codes, stage identification, early termination reporting.

### Journey Requirements Summary

| Capability | Journeys | Priority |
|---|---|---|
| Unified `process_claim()` API | Raj, Priya, Dan | Must-have |
| Shared validators in single module | Aniket, Raj | Must-have |
| Validation result passthrough | Raj, Priya | Must-have |
| Early termination on stage failure | Priya, Dan | Must-have |
| Per-stage execution metrics | Dan, Raj | Must-have |
| Dict-in / typed-model-out | Priya | Must-have |
| Single validator registration system | Aniket | Must-have |
| Consistent error code patterns | Dan, Aniket | Should-have |
| Standalone module APIs still work | Raj | Should-have |

## Domain-Specific Requirements

### HIPAA Compliance

- Shared de-identifier strips all 18 HIPAA identifiers — no regression from current 3 separate implementations
- PHI dual-path preserved: clearinghouse receives raw PHI (covered entity), AI path strips PHI
- Zero PHI in logs, findings, exceptions — findings reference field names, never values
- Ages 90+ capped to 90 per HIPAA Safe Harbor
- PHI not persisted in memory beyond a single API call; `process_claim()` clears intermediate PHI between stages

### Technical Constraints

- Stateless validators — `validate(input) -> output`, no side effects (thread safety)
- Code tables remain bundled (ICD-10, HCPCS, taxonomy, payer directory) with lazy singleton + `threading.Lock`
- Performance budgets preserved: <50ms rule-based, <500ms import, <1ms code table lookup

### Integration Contracts

- `BaseClearinghouseClient` ABC unchanged — existing implementations (StediClient) work without modification
- `BaseLLMClient` ABC unchanged — existing providers (Anthropic, OpenAI) work without modification
- `ClaimValidatorSettings` env vars (`CLAIM_VALIDATOR_*` prefix) continue to work

## Developer Tool Specific Requirements

### API Surface

| API | Purpose | Status |
|---|---|---|
| `validate(claim) -> PipelineResult` | Claim validation (rule-based + AI) | Existing — refactored internals |
| `check_eligibility(request) -> EligibilityResult` | Eligibility verification (270/271) | Existing — refactored internals |
| `submit_prior_auth(request) -> PriorAuthResult` | Prior authorization (278) | Existing — refactored internals |
| `process_claim(request) -> WorkflowResult` | Unified sequential pipeline | **NEW** |

All 4 APIs accept dict or typed Pydantic model. All return typed Pydantic result models.

### Module Structure

```
src/claim_validator/
├── shared/                    # NEW — common utilities
│   ├── validators/            # NPI, date, member_id, demographics, diagnosis, procedure
│   ├── deidentifier/          # Base de-identifier with domain config
│   ├── pipeline/              # Base pipeline engine
│   └── code_tables/           # Unified code table access
├── workflow/                  # NEW — unified sequential pipeline
│   ├── orchestrator.py        # process_claim() implementation
│   ├── models.py              # WorkflowResult, WorkflowRequest
│   └── stage.py               # Stage abstraction
├── validators/                # Claim-specific (uses shared internally)
├── eligibility/               # Eligibility-specific (uses shared internally)
├── prior_auth/                # PA-specific (uses shared internally)
└── ...                        # Existing: models, llm, conf, exceptions
```

### Migration

- Clean break at v3.0 — new internal paths, no re-exports
- Public API signatures unchanged
- New `process_claim()` and `WorkflowResult` added to top-level exports
- Package name, PyPI distribution, optional extras unchanged

### Code Example

```python
from claim_validator import process_claim

result = process_claim({
    "subscriber_id": "MEM001",
    "payer_id": "BCBS",
    "npi": "1234567893",
    "diagnosis_codes": [{"code": "M54.5"}],
    "procedure_code": "99213",
    "service_date": "2026-03-15",
})

print(result.eligibility.eligible)        # True/False
print(result.prior_auth.approved)         # True/False/None (if PA not needed)
print(result.claim_validation.passed)     # True/False
print(result.stopped_at)                  # Which stage failed, if any
```

## Functional Requirements

### Shared Validators (Deduplication)

- **FR1:** Single canonical NPI validator used by all modules
- **FR2:** Single canonical date validator (service date, DOB) used by all modules
- **FR3:** Single canonical member ID validator used by all modules
- **FR4:** Single canonical demographics validator (patient name, gender, DOB) used by all modules
- **FR5:** Single canonical diagnosis code validator (ICD-10 against bundled code table) used by all modules
- **FR6:** Single canonical procedure code validator (CPT/HCPCS against bundled code table) used by all modules
- **FR7:** Single canonical payer ID validator used by all modules
- **FR8:** Shared validators produce `Finding` objects in the same format regardless of invoking module
- **FR9:** Shared validators can be registered for specific pipeline stages via configuration

### Shared De-identification

- **FR10:** Single base de-identifier strips all 18 HIPAA identifiers
- **FR11:** Base de-identifier accepts domain-specific configuration for domain-specific fields
- **FR12:** De-identifier caps ages 90+ to 90 per HIPAA Safe Harbor
- **FR13:** De-identifier reduces dates to year-only before LLM consumption

### Shared Pipeline Engine

- **FR14:** Single configurable pipeline engine supports multi-phase execution (rule-based → clearinghouse → AI)
- **FR15:** Pipeline supports gating between phases (skip clearinghouse if rule-based fails)
- **FR16:** Pipeline produces per-phase results with execution timing
- **FR17:** Pipeline accepts different validator sets, clearinghouse clients, and AI interpreters per domain

### Shared Code Tables

- **FR18:** Unified code table access layer for ICD-10, HCPCS, taxonomy, payer directory, and service types
- **FR19:** Code tables loaded via lazy singleton with thread-safe locking
- **FR20:** Any module can look up any code table through the shared layer

### Unified Workflow Orchestrator

- **FR21:** `process_claim(request)` executes full sequential pipeline: Eligibility → PA determination → PA submission (if needed) → Claim validation
- **FR22:** Orchestrator accepts a single dict or typed model with all workflow data
- **FR23:** Orchestrator returns `WorkflowResult` with per-stage results (eligibility, prior_auth, claim_validation)
- **FR24:** Orchestrator performs PA determination from 271 response; runs PA submission only if required
- **FR25:** Orchestrator stops early on stage failure; reports failed stage via `stopped_at`
- **FR26:** Orchestrator tracks per-stage execution times
- **FR27:** Orchestrator supports validation passthrough — already-validated rules not re-run downstream

### Validation Passthrough

- **FR28:** Pipeline tracks which validators have run and their results
- **FR29:** Downstream stages query prior validation and skip redundant checks
- **FR30:** Standalone mode (not via orchestrator) runs full validator set per module

### Existing API Preservation

- **FR31:** `validate(claim)` standalone produces identical behavior to current implementation
- **FR32:** `check_eligibility(request)` standalone produces identical behavior to current implementation
- **FR33:** `submit_prior_auth(request)` standalone produces identical behavior to current implementation
- **FR34:** All 4 APIs accept both dict and typed Pydantic model input

### Result Models

- **FR35:** `WorkflowResult` contains: `eligibility` (EligibilityResult), `prior_auth` (PriorAuthResult | None), `claim_validation` (PipelineResult), `stopped_at` (stage name | None), `stage_results` (ordered list)
- **FR36:** `WorkflowResult` exposes per-stage execution time
- **FR37:** `WorkflowResult` exposes aggregate `passed` boolean (True only if all stages passed)

### HIPAA Compliance

- **FR38:** Shared de-identifier passes all existing HIPAA tests for claims, eligibility, and prior auth
- **FR39:** PHI does not persist in memory beyond a single API call
- **FR40:** Unified pipeline de-identifies before every LLM call — PHI-containing objects never reach AI phase

### Configuration

- **FR41:** Developers configure which shared validators run at each stage via settings
- **FR42:** Developers configure pipeline gating behavior via settings
- **FR43:** All existing `CLAIM_VALIDATOR_*` environment variables continue to work

## Non-Functional Requirements

### Performance

- **NFR1:** Rule-based validation <50ms per claim (no regression)
- **NFR2:** Import time <500ms (shared imports add no overhead)
- **NFR3:** Code table lookup <1ms (shared access adds zero measurable overhead)
- **NFR4:** `process_claim()` full workflow (rule-based only) <150ms (3 stages x 50ms)
- **NFR5:** Shared validator indirection <5ms overhead vs direct call
- **NFR6:** `process_claim()` memory footprint does not exceed sum of 3 individual calls

### Security

- **NFR7:** Zero PHI transmitted to any LLM
- **NFR8:** Zero PHI in logs, findings, exceptions, or error messages
- **NFR9:** PHI cleared from memory after each API call completes
- **NFR10:** All 18 HIPAA identifiers stripped — verified by automated tests per domain
- **NFR11:** No telemetry, analytics, or network calls from rule-based path

### Scalability

- **NFR12:** All shared validators stateless — thread-safe
- **NFR13:** Pipeline instances safe for concurrent use (no shared mutable state)
- **NFR14:** Code table singletons use `threading.Lock` for thread-safe initialization
- **NFR15:** O(n) linear scaling maintained

### Integration

- **NFR16:** `BaseClearinghouseClient` ABC unchanged — existing implementations work unmodified
- **NFR17:** `BaseLLMClient` ABC unchanged — existing providers work unmodified
- **NFR18:** `ClaimValidatorSettings` env var interface unchanged
- **NFR19:** Python 3.11, 3.12, 3.13 compatible
- **NFR20:** Linux, macOS, Windows

### Code Quality

- **NFR21:** Zero duplicate validation logic (measurable by grep/AST)
- **NFR22:** Test coverage >= current percentage
- **NFR23:** All existing tests pass or migrated with equivalent coverage
- **NFR24:** mypy strict — zero errors
- **NFR25:** ruff clean — zero warnings (line-length=100, rules E/F/I/N/W/UP)
- **NFR26:** Wheel size <15MB
- **NFR27:** All public classes and functions have docstrings
