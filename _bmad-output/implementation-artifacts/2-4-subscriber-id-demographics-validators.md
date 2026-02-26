# Story 2.4: Subscriber ID & Demographics Validators

Status: review

## Story

As a **developer**,
I want subscriber IDs and patient demographics validated for consistency,
so that claims with missing insurance info or contradictory demographics are caught before submission.

## Acceptance Criteria

1. **Given** a claim with a valid subscriber/insurance ID (non-empty, alphanumeric pattern), **When** `SubscriberIDValidator.validate(claim)` is called, **Then** the output contains zero subscriber-related findings.

2. **Given** a claim with an empty or whitespace-only subscriber ID, **When** `SubscriberIDValidator.validate(claim)` is called, **Then** the validator produces zero findings (CompletenessValidator handles required-ness).

3. **Given** a claim with a subscriber ID containing only special characters (e.g., `"!!@@##"`), **When** `SubscriberIDValidator.validate(claim)` is called, **Then** the output contains a `Finding` with code `INVALID_SUBSCRIBER_ID_FORMAT`, severity `ERROR`.

4. **Given** a claim with consistent demographics (valid DOB in past, valid gender), **When** `DemographicsValidator.validate(claim)` is called, **Then** the output contains zero demographics-related findings.

5. **Given** a claim with a date of birth in the future, **When** `DemographicsValidator.validate(claim)` is called, **Then** the output contains a finding with code `FUTURE_DOB` and severity `ERROR`.

6. **Given** a claim with a patient_dob that is not a valid date string, **When** `DemographicsValidator.validate(claim)` is called, **Then** the output contains a finding with code `INVALID_DOB_FORMAT` and severity `ERROR`.

7. **Given** a claim with patient_gender not in recognized values (`"M"`, `"F"`, `"U"`), **When** `DemographicsValidator.validate(claim)` is called, **Then** the output contains a finding with code `INVALID_GENDER` and severity `ERROR`.

8. **Given** a claim where patient_relationship is `"self"` but subscriber and patient names differ, **When** `DemographicsValidator.validate(claim)` is called, **Then** the output contains a finding with code `SELF_RELATIONSHIP_MISMATCH` and severity `WARNING`.

9. **Given** any demographics finding, **When** I inspect the `message`, **Then** it references field names (e.g., `"patient_dob"`) but never actual DOB values, names, or other PHI.

10. **Given** a claim with None/empty patient_dob or patient_gender, **When** `DemographicsValidator.validate(claim)` is called, **Then** the validator produces zero findings for those fields (CompletenessValidator handles required-ness).

## Tasks / Subtasks

- [x] Task 1: Implement `SubscriberIDValidator` in `src/claim_validator/validators/rule_based/subscriber_id.py` (AC: #1-#3)
  - [x] Subclass `BaseValidator` with `name = "SubscriberIDValidator"`
  - [x] Skip if subscriber_id is None or empty (CompletenessValidator handles required check)
  - [x] Validate format: must contain at least one alphanumeric character
  - [x] Finding code `INVALID_SUBSCRIBER_ID_FORMAT`, severity `ERROR`
  - [x] No PHI in messages — never include the actual subscriber ID value
- [x] Task 2: Implement `DemographicsValidator` in `src/claim_validator/validators/rule_based/demographics.py` (AC: #4-#10)
  - [x] Subclass `BaseValidator` with `name = "DemographicsValidator"`
  - [x] Validate `patient_dob` format: must be valid YYYY-MM-DD date string (skip if None/empty)
  - [x] Validate `patient_dob` not in the future (skip if None/empty or invalid format)
  - [x] Validate `patient_gender` is one of `"M"`, `"F"`, `"U"` (case-insensitive, skip if None/empty)
  - [x] Validate relationship-name consistency: if `patient_relationship == "self"` and subscriber names present, warn if names differ
  - [x] No PHI in messages — never include actual DOB, name, or gender values
- [x] Task 3: Write tests in `tests/test_validators/test_rule_based/test_subscriber_id.py` (AC: #1-#3, #9)
  - [x] Test valid subscriber ID → zero findings
  - [x] Test None subscriber_id → no findings (CompletenessValidator handles required)
  - [x] Test empty string subscriber_id → no findings
  - [x] Test subscriber ID with only special characters → `INVALID_SUBSCRIBER_ID_FORMAT`
  - [x] Test subscriber ID with alphanumeric + special chars → zero findings (valid)
  - [x] Test no PHI in finding messages
  - [x] Test severity is ERROR
  - [x] Test suggestion present
  - [x] Test validator statelessness
- [x] Task 4: Write tests in `tests/test_validators/test_rule_based/test_demographics.py` (AC: #4-#10)
  - [x] Test valid demographics → zero findings
  - [x] Test future DOB → `FUTURE_DOB` finding
  - [x] Test invalid DOB format (e.g., `"not-a-date"`, `"13/01/1990"`) → `INVALID_DOB_FORMAT`
  - [x] Test valid DOB formats: `"1990-01-15"`, `"2000-12-31"`
  - [x] Test None patient_dob → no DOB findings
  - [x] Test empty patient_dob → no DOB findings
  - [x] Test invalid gender (e.g., `"X"`, `"male"`) → `INVALID_GENDER`
  - [x] Test valid genders: `"M"`, `"F"`, `"U"`, `"m"`, `"f"`, `"u"` (case-insensitive)
  - [x] Test None patient_gender → no gender findings
  - [x] Test empty patient_gender → no gender findings
  - [x] Test relationship "self" with matching subscriber/patient names → no findings
  - [x] Test relationship "self" with differing subscriber/patient names → `SELF_RELATIONSHIP_MISMATCH` WARNING
  - [x] Test relationship "self" but subscriber names not provided → no findings (can't compare)
  - [x] Test relationship not "self" → no relationship findings regardless of names
  - [x] Test None patient_relationship → no relationship findings
  - [x] Test no PHI in any finding messages
  - [x] Test all DOB/gender severities are ERROR, relationship mismatch is WARNING
  - [x] Test validator statelessness
- [x] Task 5: Update `validators/rule_based/__init__.py` re-exports
  - [x] Add `SubscriberIDValidator` and `DemographicsValidator` re-exports
- [x] Task 6: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors (32 source files)
  - [x] `uv run pytest` — all 280 tests pass (224 existing + 56 new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### Previous Story Intelligence (Story 2.3)

- NPIValidator established the pattern: module-level constants, class with `name`, `validate()` building findings list, `self._make_output(findings)`
- Private `_check_*` method for reusable validation logic within a validator
- Test pattern: helper `_valid_claim_dict()` returning baseline valid claim, class-based tests with `setup_method`
- Line iteration: `for idx, line in enumerate(claim.lines, start=1)` — line_number is 1-indexed
- Empty/whitespace strings handled via `not value or not value.strip()`
- Format check short-circuits before deeper validation (e.g., format before Luhn)
- 224 tests passing, ruff/mypy clean (30 source files)
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- `test_rule_based/` directory and `__init__.py` already exist

### Relevant ClaimData Fields

| Field | Location | Type | Required? | Validator Scope |
|---|---|---|---|---|
| `subscriber_id` | `ClaimData` | `str \| None = None` | Yes (CompletenessValidator) | SubscriberIDValidator — format |
| `subscriber_first_name` | `ClaimData` | `str \| None = None` | No | DemographicsValidator — relationship consistency |
| `subscriber_last_name` | `ClaimData` | `str \| None = None` | No | DemographicsValidator — relationship consistency |
| `subscriber_dob` | `ClaimData` | `str \| None = None` | No | Not validated by DemographicsValidator (optional field) |
| `subscriber_gender` | `ClaimData` | `str \| None = None` | No | Not validated by DemographicsValidator (optional field) |
| `patient_first_name` | `ClaimData` | `str \| None = None` | Yes (CompletenessValidator) | DemographicsValidator — relationship consistency |
| `patient_last_name` | `ClaimData` | `str \| None = None` | Yes (CompletenessValidator) | DemographicsValidator — relationship consistency |
| `patient_dob` | `ClaimData` | `str \| None = None` | Yes (CompletenessValidator) | DemographicsValidator — format + future check |
| `patient_gender` | `ClaimData` | `str \| None = None` | Yes (CompletenessValidator) | DemographicsValidator — valid values |
| `patient_relationship` | `ClaimData` | `str \| None = None` | No | DemographicsValidator — self-relationship check |

### Finding Codes

| Code | Validator | Meaning | Severity |
|---|---|---|---|
| `INVALID_SUBSCRIBER_ID_FORMAT` | SubscriberIDValidator | Subscriber ID has no alphanumeric characters | `ERROR` |
| `INVALID_DOB_FORMAT` | DemographicsValidator | patient_dob is not a valid YYYY-MM-DD date | `ERROR` |
| `FUTURE_DOB` | DemographicsValidator | patient_dob is in the future | `ERROR` |
| `INVALID_GENDER` | DemographicsValidator | patient_gender not in M/F/U | `ERROR` |
| `SELF_RELATIONSHIP_MISMATCH` | DemographicsValidator | Relationship is "self" but subscriber/patient names differ | `WARNING` |

### Implementation Spec

#### SubscriberIDValidator

```python
# src/claim_validator/validators/rule_based/subscriber_id.py
from __future__ import annotations

import re

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

# At least one alphanumeric character
_SUBSCRIBER_ID_PATTERN = re.compile(r"[A-Za-z0-9]")


class SubscriberIDValidator(BaseValidator):
    """Validates subscriber/insurance ID format."""

    name = "SubscriberIDValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        sub_id = claim.subscriber_id
        if not sub_id or not sub_id.strip():
            return self._make_output(findings)  # CompletenessValidator handles required

        if not _SUBSCRIBER_ID_PATTERN.search(sub_id.strip()):
            findings.append(
                self._make_finding(
                    code="INVALID_SUBSCRIBER_ID_FORMAT",
                    message="Subscriber ID in 'subscriber_id' must contain at least one alphanumeric character",
                    severity=Severity.ERROR,
                    field_name="subscriber_id",
                    suggestion="Verify the subscriber/insurance ID from the insurance card (CMS-1500 Box 1a)",
                )
            )

        return self._make_output(findings)
```

#### DemographicsValidator

```python
# src/claim_validator/validators/rule_based/demographics.py
from __future__ import annotations

import datetime

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator

_VALID_GENDERS = {"M", "F", "U"}


class DemographicsValidator(BaseValidator):
    """Validates patient demographics consistency."""

    name = "DemographicsValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings: list[Finding] = []

        self._check_dob(claim, findings)
        self._check_gender(claim, findings)
        self._check_self_relationship(claim, findings)

        return self._make_output(findings)

    def _check_dob(self, claim: ClaimData, findings: list[Finding]) -> None:
        dob = claim.patient_dob
        if not dob or not dob.strip():
            return  # CompletenessValidator handles required

        try:
            dob_date = datetime.date.fromisoformat(dob.strip())
        except ValueError:
            findings.append(
                self._make_finding(
                    code="INVALID_DOB_FORMAT",
                    message="Field 'patient_dob' must be a valid date in YYYY-MM-DD format",
                    severity=Severity.ERROR,
                    field_name="patient_dob",
                    suggestion="Provide date of birth in YYYY-MM-DD format (CMS-1500 Box 3)",
                )
            )
            return  # Can't check future if format is invalid

        if dob_date > datetime.date.today():
            findings.append(
                self._make_finding(
                    code="FUTURE_DOB",
                    message="Field 'patient_dob' is in the future",
                    severity=Severity.ERROR,
                    field_name="patient_dob",
                    suggestion="Verify the patient date of birth (CMS-1500 Box 3)",
                )
            )

    def _check_gender(self, claim: ClaimData, findings: list[Finding]) -> None:
        gender = claim.patient_gender
        if not gender or not gender.strip():
            return  # CompletenessValidator handles required

        if gender.strip().upper() not in _VALID_GENDERS:
            findings.append(
                self._make_finding(
                    code="INVALID_GENDER",
                    message="Field 'patient_gender' must be one of: M, F, U",
                    severity=Severity.ERROR,
                    field_name="patient_gender",
                    suggestion="Use M (male), F (female), or U (unknown) for patient gender (CMS-1500 Box 3)",
                )
            )

    def _check_self_relationship(self, claim: ClaimData, findings: list[Finding]) -> None:
        rel = claim.patient_relationship
        if not rel or rel.strip().lower() != "self":
            return  # Only check when relationship is "self"

        # Need subscriber names to compare
        sub_first = claim.subscriber_first_name
        sub_last = claim.subscriber_last_name
        pat_first = claim.patient_first_name
        pat_last = claim.patient_last_name

        if not sub_first or not sub_last:
            return  # Can't compare if subscriber names aren't provided

        if not pat_first or not pat_last:
            return  # Can't compare if patient names aren't provided

        # Case-insensitive comparison
        first_match = sub_first.strip().lower() == pat_first.strip().lower()
        last_match = sub_last.strip().lower() == pat_last.strip().lower()

        if not (first_match and last_match):
            findings.append(
                self._make_finding(
                    code="SELF_RELATIONSHIP_MISMATCH",
                    message="Patient relationship is 'self' but subscriber and patient names differ",
                    severity=Severity.WARNING,
                    field_name="patient_relationship",
                    suggestion="When relationship is 'self', subscriber and patient should be the same person (CMS-1500 Box 6)",
                )
            )
```

### Key Design Decisions

- **SubscriberIDValidator** only checks format (at least one alphanumeric) — presence is CompletenessValidator's job
- **DemographicsValidator** validates DOB format, future DOB, gender values, and self-relationship consistency
- DOB format check uses `datetime.date.fromisoformat()` — supports YYYY-MM-DD natively in Python 3.11+
- Gender validation is case-insensitive (accepts `"m"`, `"M"`)
- Self-relationship check compares names case-insensitively; skips if either party's names are missing
- Self-relationship mismatch is `WARNING` (not `ERROR`) — names may differ for legitimate reasons (legal name change, nickname)
- None/empty fields silently skipped — CompletenessValidator handles required field presence
- Messages reference field names not actual values (no PHI)

### Anti-Patterns to Avoid

- **DO NOT** include the subscriber ID value in finding messages — that's PHI
- **DO NOT** include DOB values, names, or gender values in messages — that's PHI
- **DO NOT** validate fields that are None or empty — CompletenessValidator handles that
- **DO NOT** make network calls — rule-based validators are offline only
- **DO NOT** store state between validate() calls
- **DO NOT** raise exceptions for validation failures — return findings
- **DO NOT** validate subscriber_dob or subscriber_gender — only patient demographics are validated (subscriber fields are optional insurance info)

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **FR9** | Validate subscriber/insurance ID presence and format |
| **FR10** | Validate patient demographics consistency |
| **NFR1** | Rule-based latency < 50ms — string checks only, no I/O |
| **NFR8** | Zero network calls for rule-based |
| **NFR10** | No PHI in outputs — field names only in messages |
| **NFR15** | Stateless validation |
| **D10** | Dotted paths: `claim_validator.validators.rule_based.subscriber_id.SubscriberIDValidator`, `claim_validator.validators.rule_based.demographics.DemographicsValidator` |

### conf.py Default Validators

Both validators are already listed in `DEFAULT_RULE_VALIDATORS` in `conf.py`:
```python
"claim_validator.validators.rule_based.subscriber_id.SubscriberIDValidator",
"claim_validator.validators.rule_based.demographics.DemographicsValidator",
```
No configuration changes needed.

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 2.4] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Pipeline Architecture — D10]
- [Source: _bmad-output/planning-artifacts/prd.md#FR9] — Subscriber ID validation
- [Source: _bmad-output/planning-artifacts/prd.md#FR10] — Patient demographics consistency
- [Source: CMS-1500 Form] — Box 1a (Subscriber ID), Box 2 (Patient Name), Box 3 (DOB, Gender), Box 6 (Relationship)

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6 (claude-opus-4-6)

### Debug Log References
- RED phase: Tests written first for both validators, confirmed ImportError (modules not yet created)
- GREEN phase: Both implementations created, ruff flagged 5 E501 line-length violations
- Fix: Wrapped long message/suggestion strings with implicit concatenation to stay under 100 chars
- Final: 280 tests pass, ruff clean, mypy clean (32 source files)

### Completion Notes List
- All 10 acceptance criteria satisfied
- 56 new tests across 10 test classes:
  - test_subscriber_id.py: TestSubscriberIDValidatorValid (6), TestSubscriberIDValidatorSkipEmpty (3), TestSubscriberIDValidatorInvalid (3), TestSubscriberIDValidatorFindings (1), TestSubscriberIDValidatorStatelessness (3) = 16 tests
  - test_demographics.py: TestDemographicsValidatorValid (4), TestDemographicsValidatorDOB (9), TestDemographicsValidatorGender (11), TestDemographicsValidatorRelationship (10), TestDemographicsValidatorFindings (3), TestDemographicsValidatorStatelessness (3) = 40 tests
- Implementation follows established BaseValidator pattern from Story 2.1/2.2/2.3
- DOB format check uses datetime.date.fromisoformat() — short-circuits before future check
- Gender validation is case-insensitive (M/F/U)
- Self-relationship mismatch is WARNING (not ERROR) — names may legitimately differ
- No PHI in any finding messages or suggestions
- Stateless validation confirmed for both validators

### File List
- `src/claim_validator/validators/rule_based/subscriber_id.py` — NEW: SubscriberIDValidator
- `src/claim_validator/validators/rule_based/demographics.py` — NEW: DemographicsValidator
- `src/claim_validator/validators/rule_based/__init__.py` — MODIFIED: Added SubscriberIDValidator and DemographicsValidator re-exports
- `tests/test_validators/test_rule_based/test_subscriber_id.py` — NEW: 16 tests for SubscriberIDValidator
- `tests/test_validators/test_rule_based/test_demographics.py` — NEW: 40 tests for DemographicsValidator

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-18 | All tasks done, 280 tests pass, ruff/mypy clean |
