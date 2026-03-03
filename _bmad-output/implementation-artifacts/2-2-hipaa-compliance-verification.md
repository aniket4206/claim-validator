# Story 2.2: HIPAA Compliance Verification

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a security-conscious developer,
I want automated tests verifying the shared de-identifier strips all 18 HIPAA identifiers for all 3 domains,
so that no PHI reaches LLM providers or persists beyond a single API call.

## Acceptance Criteria

1. **AC-1: Claims domain PHI verification**
   - **Given** test inputs containing all applicable HIPAA identifier types for claims domain
   - **When** `BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)` is called
   - **Then** the output contains zero PHI — name fields are `None`, dates are year-only ints, subscriber_id is `None`, addresses are `None`, DOB is capped age int
   - **And** no raw PHI value (name, SSN, address, etc.) appears anywhere in the output dict values

2. **AC-2: Eligibility domain PHI verification**
   - **Given** test inputs containing all applicable HIPAA identifier types for eligibility domain
   - **When** `BaseDeidentifier(ELIGIBILITY_DEID_CONFIG).deidentify(data)` is called
   - **Then** the output contains zero PHI — subscriber_name is `None`, dates are year-only ints, member_id and group_number are `None`
   - **And** non-PHI fields (plan_name, payer_id, coverage status) pass through unchanged

3. **AC-3: Prior auth domain PHI verification**
   - **Given** test inputs containing all applicable HIPAA identifier types for prior auth domain
   - **When** `BaseDeidentifier(PA_DEID_CONFIG).deidentify(data)` is called
   - **Then** the output contains zero PHI — patient_name is `None`, dates are year-only ints, auth_number and member_id are `None`, address is `None`, DOB is capped age int

4. **AC-4: PHI leak scan across all domains**
   - **Given** a de-identified output dict from any domain
   - **When** inspected for PHI leakage
   - **Then** no value in the output matches any input PHI value (names, IDs, addresses, full dates)
   - **And** findings/messages reference field names only, never PHI values (FR40)

5. **AC-5: HIPAA Safe Harbor age cap verification (FR12)**
   - **Given** input records with DOB computing to ages 89, 90, 91, 95, 100+
   - **When** de-identification runs for claims and prior auth
   - **Then** ages <= 90 pass through as-is; ages > 90 are capped to 90

6. **AC-6: Date reduction verification (FR13)**
   - **Given** input records with various date formats (ISO strings, None, invalid)
   - **When** de-identification runs
   - **Then** valid dates are reduced to year-only int, None stays None, invalid dates become None

7. **AC-7: Backward compatibility (FR38)**
   - **Given** all existing tests pass before Story 2.2
   - **When** Story 2.2 tests are added
   - **Then** all 1903+ existing tests still pass with zero regressions
   - **And** no existing source files are modified

8. **AC-8: Cross-cutting quality**
   - All new test files pass ruff clean
   - Test file structure follows `tests/test_shared/test_deidentifier/` pattern
   - No new source files created — this story is tests-only

## Tasks / Subtasks

- [x] Task 1: Create HIPAA compliance test module (AC: #8)
  - [x] 1.1: Create `tests/test_shared/test_deidentifier/test_hipaa_compliance.py`
- [x] Task 2: Claims domain PHI verification tests (AC: #1, #4, #5, #6)
  - [x] 2.1: Test all name fields stripped to `None` for claims
  - [x] 2.2: Test all date fields reduced to year-only int for claims
  - [x] 2.3: Test subscriber_id stripped to `None`
  - [x] 2.4: Test all address fields stripped to `None` for claims
  - [x] 2.5: Test DOB age cap at 90 for claims
  - [x] 2.6: Test comprehensive PHI leak scan — no raw PHI value in output values
  - [x] 2.7: Test non-PHI fields preserved (diagnosis_code, procedure_code, npi, charge_amount)
- [x] Task 3: Eligibility domain PHI verification tests (AC: #2, #4, #6)
  - [x] 3.1: Test subscriber_name stripped to `None`
  - [x] 3.2: Test date fields reduced to year-only int for eligibility
  - [x] 3.3: Test member_id and group_number stripped to `None`
  - [x] 3.4: Test no age processing (eligibility has no DOB field)
  - [x] 3.5: Test comprehensive PHI leak scan for eligibility
  - [x] 3.6: Test non-PHI fields preserved (plan_name, payer_id, coverage_active)
- [x] Task 4: Prior auth domain PHI verification tests (AC: #3, #4, #5, #6)
  - [x] 4.1: Test patient_name stripped to `None`
  - [x] 4.2: Test date fields reduced to year-only int for PA
  - [x] 4.3: Test authorization_number and member_id stripped to `None`
  - [x] 4.4: Test patient_address stripped to `None`
  - [x] 4.5: Test DOB age cap at 90 for PA
  - [x] 4.6: Test comprehensive PHI leak scan for PA
  - [x] 4.7: Test non-PHI fields preserved (diagnosis_code, procedure_code, status)
- [x] Task 5: HIPAA Safe Harbor edge case tests (AC: #5, #6)
  - [x] 5.1: Test age boundary cases — ages 89, 90, 91, 95, 100 for both claims and PA
  - [x] 5.2: Test date edge cases — ISO strings, None, empty string, invalid string, datetime.date objects
  - [x] 5.3: Test future DOB returns None (not negative age)
  - [x] 5.4: Test None DOB returns None (graceful handling)
- [x] Task 6: Cross-domain PHI leak scanning tests (AC: #4)
  - [x] 6.1: Parametrized test across all 3 domain configs: assert no input PHI value appears in any output value
  - [x] 6.2: Test with realistic PHI data — real-looking names, SSNs, addresses, DOBs
  - [x] 6.3: Verify output dict keys are preserved (only values change)
- [x] Task 7: Quality verification (AC: #7, #8)
  - [x] 7.1: Run `ruff check` on all new test files
  - [x] 7.2: Run `pytest tests/test_shared/test_deidentifier/test_hipaa_compliance.py` — all pass
  - [x] 7.3: Run full `pytest` — all 1903+ existing tests still pass, zero regressions

## Dev Notes

### Story Scope: Tests Only

This story creates a HIPAA compliance verification test suite. **No source files are created or modified.** All tests exercise the existing `BaseDeidentifier` and domain configs from Story 2.1.

The test file goes in `tests/test_shared/test_deidentifier/test_hipaa_compliance.py` — a single comprehensive test module covering all 3 domains from a HIPAA compliance perspective.

### Architecture Decision D5/D6: PHI Boundary (Context Only)

D5: De-identification is pipeline-integrated — automatic before any AI validator. Zero bypass risk.
D6: Type-driven + runtime PHI boundary (belt-and-suspenders). `DeidentifiedClaim` type is the only type accepted by `BaseLLMClient.send()`.

For Story 2.2, we verify the `BaseDeidentifier` correctly strips PHI for all 3 domains. The pipeline integration (D5) and type-driven boundary (D6) are Epic 3/4 concerns.

### Architecture Decision D35: Shared De-identifier (What We're Testing)

`BaseDeidentifier` operates on `dict[str, Any]` with `DeidentificationConfig`. Domain subclasses (Epic 3) will set config only, never override `deidentify()`.

**Enforcement Guideline #4:** Domain de-identifiers set config in `__init__`, never override `deidentify()`.
**Enforcement Guideline #9:** Every validator test MUST include a PHI-leak assertion.

### HIPAA Safe Harbor 18 Identifiers — What's Applicable

The 18 HIPAA Safe Harbor identifiers (45 CFR §164.514(b)):

| # | Identifier | Applicable to this library? | How handled |
|---|-----------|---------------------------|-------------|
| 1 | Names | Yes | `name_fields` → `None` |
| 2 | Geographic data < state | Yes (addresses) | `address_fields` → `None` |
| 3 | Dates (except year) | Yes | `date_fields` → year-only int |
| 4 | Phone numbers | No — not in claim/elig/PA models | N/A |
| 5 | Fax numbers | No | N/A |
| 6 | Email addresses | No | N/A |
| 7 | SSNs | No — not in any domain model | N/A |
| 8 | Medical record numbers | No | N/A |
| 9 | Health plan beneficiary numbers | Yes | `id_fields` → `None` |
| 10 | Account numbers | No | N/A |
| 11 | Certificate/license numbers | No | N/A |
| 12 | Vehicle identifiers | No | N/A |
| 13 | Device identifiers | No | N/A |
| 14 | Web URLs | No | N/A |
| 15 | IP addresses | No | N/A |
| 16 | Biometric identifiers | No | N/A |
| 17 | Full-face photographs | No | N/A |
| 18 | Other unique identifiers | Partial — subscriber_id, member_id, auth_number, group_number | `id_fields` → `None` |

**Key insight:** Identifiers 4-18 (phone, fax, email, SSN, etc.) are NOT present in any domain model. The library processes structured healthcare transaction data (837/835/270/271/278 formats) which don't contain these fields. Tests should verify coverage of the identifiers that ARE present, not hypothetical ones.

### NFR Requirements for HIPAA Tests

- **NFR7:** Zero PHI transmitted to any LLM
- **NFR8:** Zero PHI in logs, findings, exceptions, or error messages
- **NFR9:** PHI cleared from memory after each API call completes
- **NFR10:** All 18 HIPAA identifiers stripped — verified by automated tests per domain

### Test Design Pattern

Use comprehensive PHI leak scanning per domain:

```python
def _assert_no_phi_leak(input_data: dict, output_data: dict) -> None:
    """Assert no raw PHI value from input appears in output values."""
    output_values = set(_flatten_values(output_data))
    for key, value in input_data.items():
        if isinstance(value, str) and value:  # Only check non-empty strings
            assert value not in output_values, (
                f"PHI leak: input['{key}'] = '{value}' found in output"
            )
```

Use parametrized tests across domains for cross-cutting verification:

```python
@pytest.mark.parametrize(
    ("config", "sample_data"),
    [
        (CLAIM_DEID_CONFIG, CLAIM_SAMPLE),
        (ELIGIBILITY_DEID_CONFIG, ELIG_SAMPLE),
        (PA_DEID_CONFIG, PA_SAMPLE),
    ],
    ids=["claim", "eligibility", "prior_auth"],
)
def test_no_phi_leak(config, sample_data):
    ...
```

### Existing Domain Deidentifiers (DO NOT MODIFY)

| Domain | File | Status |
|--------|------|--------|
| Claims | `deidentifier/deidentifier.py` | NOT MODIFIED — Epic 3 |
| Eligibility | `eligibility/deidentifier.py` | NOT MODIFIED — Epic 3 |
| Prior Auth | `prior_auth/deidentifier.py` | NOT MODIFIED — Epic 3 |

### D43: Clean Break

- Story 2.2 ONLY creates new test files
- Does NOT modify existing source files
- Does NOT modify existing test files
- Does NOT create new source files

### Previous Story Intelligence

**Story 2.1 (BaseDeidentifier and domain configurations):**
- `BaseDeidentifier.deidentify()` operates on `dict[str, Any]` — shallow copy via `{**data}`
- `DeidentificationConfig` has `__post_init__` validation preventing `age_field` overlap with `date_fields`
- `compute_age()` returns `None` for future DOB (negative age guard added in code review)
- `extract_year()` handles ISO strings, `datetime.date` objects, and None
- Domain configs: `CLAIM_DEID_CONFIG`, `ELIGIBILITY_DEID_CONFIG`, `PA_DEID_CONFIG` in `shared/deidentifier/config.py`
- Import path: `from claim_validator.shared.deidentifier.config import CLAIM_DEID_CONFIG, ...`
- Import path: `from claim_validator.shared.deidentifier.base import BaseDeidentifier`

**Story 1.1-1.4 Learnings:**
- Use `.venv/bin/python -m pytest` (NOT `.venv/bin/pytest` — stale shebang)
- Run ruff on ALL files including test files
- `from __future__ import annotations` on ALL new files
- PHI-leak tests: pass actual PHI values, assert they don't appear in output

### What Story 2.2 Must NOT Create/Modify

- Do NOT modify existing domain deidentifiers — Epic 3
- Do NOT modify `BaseDeidentifier` or `DeidentificationConfig` — Story 2.1 (done)
- Do NOT create new source files — this is a tests-only story
- Do NOT modify existing test files — add new test file only
- Do NOT modify `conf.py`, pipelines, or models

### Quality Requirements

- **ruff** — run on ALL new test files
- **pytest** — all new + all existing tests must pass (1903+)
- **Docstrings** — module-level and test class docstrings
- **No source changes** — this story adds tests only

### Testing Strategy

Single test file `test_hipaa_compliance.py` organized by:
1. **Per-domain test classes** — `TestClaimHipaaCompliance`, `TestEligibilityHipaaCompliance`, `TestPaHipaaCompliance`
2. **Cross-domain test class** — `TestCrossDomainPhiLeakScan` with parametrized tests
3. **Safe Harbor edge case class** — `TestHipaaSafeHarborEdgeCases` for age cap and date reduction boundaries
4. **Helper function** — `_assert_no_phi_leak()` for reusable PHI scanning

### References

- [Source: architecture.md — D5: Pipeline-integrated de-identification]
- [Source: architecture.md — D6: Type-driven + runtime PHI boundary]
- [Source: architecture.md — D35: Shared de-identifier base]
- [Source: architecture.md — D43: Clean break, import path migration]
- [Source: architecture.md — Enforcement Guideline #9: PHI-leak assertion in every test]
- [Source: epics.md — Epic 2, Story 2.2 acceptance criteria]
- [Source: epics.md — FR38: Shared de-identifier passes all existing HIPAA tests]
- [Source: epics.md — FR39: PHI does not persist beyond a single API call]
- [Source: epics.md — FR40: Pipeline de-identifies before every LLM call]
- [Source: epics.md — NFR7-NFR10: Zero PHI requirements]
- [Source: 2-1-basedeidentifier-and-domain-configurations.md — Previous story learnings]

## Dev Agent Record

### Agent Model Used

Claude Opus 4.6

### Debug Log References

- Ruff check: All checks passed on `test_hipaa_compliance.py`
- New tests: 67 passed in 0.70s
- Full regression: 1970 passed in 6.28s (1903 existing + 67 new, zero regressions)

### Completion Notes List

- Created single comprehensive HIPAA compliance test module with 67 tests
- 5 test classes: `TestClaimHipaaCompliance` (16 tests), `TestEligibilityHipaaCompliance` (10 tests), `TestPaHipaaCompliance` (12 tests), `TestHipaaSafeHarborEdgeCases` (20 tests), `TestCrossDomainPhiLeakScan` (9 tests)
- Config-aware `_assert_no_phi_leak()` helper checks only PHI field values (not non-PHI passthrough fields) for accurate leak detection; error messages reference field names only, never PHI values (AC-4/FR40)
- `_phi_field_names()` helper extracts all PHI field names from a `DeidentificationConfig`
- Parametrized age boundary tests cover ages 89, 90, 91, 95, 100 for both claims and PA domains via shared `_AGE_BOUNDARY_CASES` constant
- Date edge cases cover ISO strings, None, empty string, invalid string, and `datetime.date` objects
- DOB edge cases include `datetime.date` objects (returns None — `compute_age` accepts str only), future DOB, and None DOB
- Realistic PHI data tests use diverse names (hyphenated, apostrophe, multi-word), realistic IDs, and full addresses
- No source files created or modified — tests-only story (D43 clean break)
- All 8 ACs satisfied
- Code review fixes: PHI-safe assertion messages (#1), stronger age assertions (#2), DRY parametrize constants (#3), datetime.date DOB test (#4)

### Change Log

- 2026-03-03: Story 2.2 implemented — HIPAA compliance verification test suite (66 tests, tests-only)
- 2026-03-03: Code review fixes — 1 MEDIUM + 4 LOW issues resolved (67 tests after adding datetime.date DOB edge case)

### File List

- `tests/test_shared/test_deidentifier/test_hipaa_compliance.py` — NEW (67 tests)
