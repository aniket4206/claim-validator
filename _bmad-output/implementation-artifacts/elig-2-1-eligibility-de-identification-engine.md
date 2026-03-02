# Story ELIG-2.1: Eligibility De-identification Engine

Status: done

## Story

As a **developer**,
I want eligibility response data automatically de-identified before any LLM call,
so that I can use AI interpretation with zero risk of PHI leakage — guaranteed by the library.

## Acceptance Criteria

1. **Given** an `EligibilityResponse` with full PHI (subscriber name, DOB, member ID, group-specific identifiers), **when** `EligibilityDeidentifier.deidentify(response)` is called, **then** a `DeidentifiedEligibilityResponse` is returned with all 18 HIPAA identifiers stripped **and** only safe data remains: coverage status, service type codes, benefit amounts (copay/coinsurance/deductible), in_network flags, prior_auth_required flags, coverage dates (year only), rejection codes, follow-up codes.

2. **Given** the 18 HIPAA identifier categories, **when** I run the de-identifier against test responses containing each identifier type, **then** all are stripped: plan name (may embed group identifiers), group number, effective/termination dates (reduced to year only), subscriber-identifying info in AAA error messages, and all PHI in `raw_response`.

3. **Given** a `DeidentifiedEligibilityResponse` instance, **when** I check its type, **then** mypy/pyright distinguishes it from `EligibilityResponse` at the type level **and** the type system prevents accidentally passing raw `EligibilityResponse` to LLM-facing functions.

4. **Given** an `EligibilityResponse` with AAA errors containing subscriber-identifying information, **when** `EligibilityDeidentifier.deidentify(response)` is called, **then** PHI in error messages is stripped while preserving rejection codes and follow-up codes.

5. **Given** edge cases (PHI embedded in unexpected response fields, mixed PHI/clinical data), **when** the de-identifier processes them, **then** it errs on the side of stripping — false positive removal is acceptable, false negative (PHI leakage) is not.

6. **Given** a comprehensive PHI leak test suite, **when** run against `EligibilityDeidentifier`, **then** all tests pass confirming zero PHI in the de-identified output **and** tests cover all HIPAA identifier categories relevant to eligibility data.

## Tasks / Subtasks

- [x] Task 1: Create `DeidentifiedEligibilityResponse` model in `eligibility/models/deidentified.py` (AC: #1, #3)
  - [x] 1.1: `DeidentifiedEligibilityResponse` — frozen Pydantic model with only safe fields
  - [x] 1.2: `DeidentifiedCoverageInfo` — year-only dates, no plan_name/group_number
  - [x] 1.3: `DeidentifiedAAAError` — rejection_code + follow_up_code only, no message
  - [x] 1.4: `is_deidentified: Literal[True]` property for type-level distinction
  - [x] 1.5: Add to `eligibility/models/__init__.py` exports

- [x] Task 2: Create `EligibilityDeidentifier` in `eligibility/deidentifier.py` (AC: #1, #2, #4, #5)
  - [x] 2.1: `deidentify(response: EligibilityResponse) -> DeidentifiedEligibilityResponse` classmethod
  - [x] 2.2: Strip `coverage.plan_name`, `coverage.group_number` (may embed identifiers)
  - [x] 2.3: Reduce `coverage.effective_date`, `coverage.termination_date` to year-only (`int | None`)
  - [x] 2.4: Strip `errors[].message` (may contain subscriber info), retain codes only
  - [x] 2.5: Strip `raw_response` entirely (unknown PHI risk)
  - [x] 2.6: Retain safe data: `eligible`, `coverage.status`, `benefits[*]` amounts/flags/codes
  - [x] 2.7: `BenefitInfo` passes through unchanged (contains only codes and monetary amounts — no PHI)

- [x] Task 3: Update exports (AC: #3)
  - [x] 3.1: Add `EligibilityDeidentifier` and `DeidentifiedEligibilityResponse` to `eligibility/__init__.py`
  - [x] 3.2: Add to top-level `claim_validator/__init__.py` and `__all__`

- [x] Task 4: Write tests in `tests/test_eligibility/test_hipaa/test_deidentifier.py` (AC: #1–#6)
  - [x] 4.1: Fixture: `full_phi_response()` — EligibilityResponse with all PHI fields populated
  - [x] 4.2: TestDeidentifyBasic — returns DeidentifiedEligibilityResponse, is_deidentified=True, deterministic, stateless
  - [x] 4.3: TestStripCoverage — plan_name stripped, group_number stripped, dates → year-only, status retained
  - [x] 4.4: TestStripAAAErrors — message stripped, rejection_code retained, follow_up_code retained
  - [x] 4.5: TestStripRawResponse — raw_response not present in output
  - [x] 4.6: TestRetainedData — eligible, coverage.status, all benefit fields, error codes
  - [x] 4.7: TestBenefitsPassthrough — service_type_code, copay, coinsurance, deductible, in_network, prior_auth_required all retained
  - [x] 4.8: TestEdgeCases — empty response, None coverage, empty benefits, empty errors, None dates
  - [x] 4.9: TestPHILeakSweep — model_dump() string search for any PHI values
  - [x] 4.10: TestImports — importable from eligibility module and top-level

- [x] Task 5: Run full test suite and linting (AC: all)
  - [x] 5.1: `pytest tests/test_eligibility/test_hipaa/` — 46/46 pass
  - [x] 5.2: Full regression `pytest` — 1412/1412 pass, no regressions
  - [x] 5.3: `ruff check` — clean (0 errors on changed files)

## Dev Notes

### Architecture — Direct Analog: `ClaimDeidentifier`

The `EligibilityDeidentifier` follows the **exact same pattern** as `ClaimDeidentifier`. Key structural parallels:

| Component | Claims (reference) | Eligibility (to build) |
|---|---|---|
| De-identifier | `deidentifier/deidentifier.py` → `ClaimDeidentifier` | `eligibility/deidentifier.py` → `EligibilityDeidentifier` |
| Input model | `ClaimData` | `EligibilityResponse` |
| Output model | `DeidentifiedClaim` | `DeidentifiedEligibilityResponse` |
| Model location | `models/deidentified.py` | `eligibility/models/deidentified.py` |
| Test location | `tests/test_deidentifier/` | `tests/test_eligibility/test_hipaa/` |

Also see: `DeidentifiedPriorAuthResponse` at `prior_auth/models/deidentified.py` — the PA analog (stub with safe fields only).

### EligibilityResponse Fields — PHI Classification

| Field | PHI? | Action | Rationale |
|---|---|---|---|
| `eligible` | No | Retain | Boolean status |
| `coverage.status` | No | Retain | Enum (active/inactive/unknown) |
| `coverage.effective_date` | Yes | Year only | Full date is PHI per Safe Harbor |
| `coverage.termination_date` | Yes | Year only | Full date is PHI per Safe Harbor |
| `coverage.plan_name` | Yes | Strip | May embed group/employer identifiers |
| `coverage.group_number` | Yes | Strip | Group-specific identifier |
| `benefits[*].service_type_code` | No | Retain | Standard code |
| `benefits[*].service_type_name` | No | Retain | Category name |
| `benefits[*].copay` | No | Retain | Monetary amount |
| `benefits[*].coinsurance` | No | Retain | Percentage |
| `benefits[*].deductible` | No | Retain | Monetary amount |
| `benefits[*].in_network` | No | Retain | Boolean |
| `benefits[*].prior_auth_required` | No | Retain | Boolean |
| `errors[*].rejection_code` | No | Retain | Standard code |
| `errors[*].follow_up_code` | No | Retain | Standard code |
| `errors[*].message` | Yes | Strip | May contain subscriber info |
| `raw_response` | Yes | Strip entirely | Unknown content risk |

### DeidentifiedEligibilityResponse Model Shape

```python
class DeidentifiedCoverageInfo(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    status: CoverageStatus = CoverageStatus.UNKNOWN
    effective_year: int | None = None  # date → year only
    termination_year: int | None = None  # date → year only
    # plan_name STRIPPED
    # group_number STRIPPED

class DeidentifiedAAAError(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    rejection_code: str
    follow_up_code: str | None = None
    # message STRIPPED

class DeidentifiedEligibilityResponse(BaseModel):
    model_config = ConfigDict(frozen=True, strict=False)
    eligible: bool | None = None
    coverage: DeidentifiedCoverageInfo | None = None
    benefits: list[BenefitInfo] = []  # pass through unchanged (no PHI)
    errors: list[DeidentifiedAAAError] = []
    # raw_response STRIPPED

    @property
    def is_deidentified(self) -> Literal[True]:
        return True
```

### EligibilityDeidentifier Pattern

```python
class EligibilityDeidentifier:
    """Strips PHI from EligibilityResponse for LLM consumption.
    Stateless — safe for concurrent use, deterministic output.
    """

    @classmethod
    def deidentify(
        cls, response: EligibilityResponse,
    ) -> DeidentifiedEligibilityResponse:
        coverage = cls._deidentify_coverage(response.coverage)
        errors = [cls._deidentify_error(e) for e in response.errors]
        return DeidentifiedEligibilityResponse(
            eligible=response.eligible,
            coverage=coverage,
            benefits=list(response.benefits),  # no PHI in benefit fields
            errors=errors,
        )

    @classmethod
    def _deidentify_coverage(cls, cov: CoverageInfo | None) -> DeidentifiedCoverageInfo | None:
        if cov is None:
            return None
        return DeidentifiedCoverageInfo(
            status=cov.status,
            effective_year=cov.effective_date.year if cov.effective_date else None,
            termination_year=cov.termination_date.year if cov.termination_date else None,
        )

    @staticmethod
    def _deidentify_error(error: AAAError) -> DeidentifiedAAAError:
        return DeidentifiedAAAError(
            rejection_code=error.rejection_code,
            follow_up_code=error.follow_up_code,
        )
```

### Test Fixture — Full PHI Response

```python
def full_phi_response() -> EligibilityResponse:
    return EligibilityResponse(
        eligible=True,
        coverage=CoverageInfo(
            status=CoverageStatus.ACTIVE,
            effective_date=datetime.date(2023, 1, 15),
            termination_date=datetime.date(2025, 12, 31),
            plan_name="Acme Corp Gold PPO - Dept 42",
            group_number="GRP-AC-2023-042",
        ),
        benefits=[
            BenefitInfo(
                service_type_code="30",
                service_type_name="Health Benefit Plan Coverage",
                copay=40.0,
                coinsurance=0.20,
                deductible=2500.0,
                in_network=True,
                prior_auth_required=False,
            ),
        ],
        errors=[
            AAAError(
                rejection_code="72",
                follow_up_code="C",
                message="Subscriber John Smith (ID: XYZ123) not found in plan",
            ),
        ],
        raw_response={
            "subscriber": {"firstName": "John", "lastName": "Smith", "memberId": "XYZ123"},
            "tradingPartnerServiceId": "60054",
        },
    )
```

### Learnings from Previous Stories

- All eligibility models use `ConfigDict(frozen=True, strict=False)` — follow this
- `ClaimDeidentifier` uses `@classmethod` pattern — NOT instance methods. Follow this
- `DeidentifiedClaim` has `is_deidentified` property returning `Literal[True]` — follow for type distinction
- `BenefitInfo` only contains codes and monetary amounts — safe to pass through unchanged (no need for a de-identified variant)
- `AAAError.message` is the dangerous field — free-text that may contain subscriber info. Strip entirely, keep only codes
- `raw_response` is completely opaque — strip entirely (err on side of safety per AC #5)
- Test pattern: `model_dump()` string search for PHI values (see `TestStripNames.test_no_name_in_any_field`)
- `tests/test_eligibility/test_hipaa/` directory already exists as empty `__init__.py` — tests go here
- ruff line length ≤100 chars, ruff check rules: E, F, I, N, W, UP
- Use `.venv/bin/python -m pytest` (not bare `pytest` — wrong venv shebang)

### Project Structure Notes

- `eligibility/deidentifier.py` — new file (mirrors `deidentifier/deidentifier.py` at module level)
- `eligibility/models/deidentified.py` — new file (mirrors `models/deidentified.py` and `prior_auth/models/deidentified.py`)
- `eligibility/models/__init__.py` — add exports
- `eligibility/__init__.py` — add exports
- `claim_validator/__init__.py` — add top-level exports
- `tests/test_eligibility/test_hipaa/test_deidentifier.py` — new test file
- No conftest changes needed — fixtures in test file (same pattern as test_pipeline.py)

### References

- [Source: src/claim_validator/deidentifier/deidentifier.py] — ClaimDeidentifier (direct structural analog)
- [Source: src/claim_validator/models/deidentified.py] — DeidentifiedClaim model (pattern to follow)
- [Source: src/claim_validator/prior_auth/models/deidentified.py] — DeidentifiedPriorAuthResponse (PA analog stub)
- [Source: src/claim_validator/eligibility/models/response.py] — EligibilityResponse, CoverageInfo, BenefitInfo, AAAError (input)
- [Source: src/claim_validator/eligibility/models/result.py] — EligibilityResult (pipeline output, references EligibilityResponse)
- [Source: src/claim_validator/eligibility/constants.py] — CoverageStatus enum
- [Source: src/claim_validator/eligibility/__init__.py] — Current exports
- [Source: src/claim_validator/__init__.py] — Top-level exports
- [Source: tests/test_deidentifier/test_deidentifier.py] — ClaimDeidentifier tests (test pattern reference)
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1] — Original ACs (Epic 3 → renumbered to Epic 2)
- [Source: _bmad-output/project-context.md] — HIPAA/PHI rules, de-identification requirements

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References

None — all tasks completed on first pass, no debugging required.

### Completion Notes List

- All 5 tasks implemented successfully, matching the `ClaimDeidentifier` pattern exactly
- 3 new source files created, 3 existing files modified for exports
- 46 tests across 10 test classes covering all 6 ACs
- PHI leak sweep confirms zero PHI in de-identified output
- Full regression: 1412/1412 pass, ruff clean
- `BenefitInfo` passes through unchanged — confirmed no PHI in benefit fields
- `is_deidentified` property provides type-level distinction (`Literal[True]`)
- All models use `ConfigDict(frozen=True, strict=False)` per project convention
- **Code review fixes:** Added 5 new tests (TestTypeDistinction: 2, TestFrozenEnforcement: 3), strengthened test_stateless, expanded test_second_benefit_retained to all 7 fields, added follow_up_code assertion to test_error_with_empty_message. Total: 51 tests.

### File List

- `claim-validator/src/claim_validator/eligibility/models/deidentified.py` (NEW) — DeidentifiedCoverageInfo, DeidentifiedAAAError, DeidentifiedEligibilityResponse models
- `claim-validator/src/claim_validator/eligibility/deidentifier.py` (NEW) — EligibilityDeidentifier with deidentify() classmethod
- `claim-validator/src/claim_validator/eligibility/models/__init__.py` (MODIFIED) — Added 3 deidentified model exports
- `claim-validator/src/claim_validator/eligibility/__init__.py` (MODIFIED) — Added EligibilityDeidentifier + 3 deidentified model exports
- `claim-validator/src/claim_validator/__init__.py` (MODIFIED) — Added 4 new symbols to imports and __all__
- `claim-validator/tests/test_eligibility/test_hipaa/test_deidentifier.py` (NEW) — 46 tests across 10 classes
