# Story 3.1: HIPAA De-identification Engine

Status: review

## Story

As a **developer**,
I want claims automatically de-identified before any LLM call,
so that I can use AI validation with zero risk of PHI leakage — guaranteed by the library.

## Acceptance Criteria

1. **Given** a `ClaimData` instance with full PHI (patient name, DOB, subscriber ID, etc.), **When** `ClaimDeidentifier.deidentify(claim)` is called, **Then** a `DeidentifiedClaim` is returned with all 18 HIPAA identifiers stripped. **And** only clinically relevant, non-PHI data remains: codes, charges, payer ID, NPI, patient age, gender, state, service year.

2. **Given** the 18 HIPAA identifier categories, **When** I run the de-identifier against test claims containing each identifier type, **Then** all 18 types are removed: names, geographic data (below state), dates (except year), phone/fax, email, SSN, medical record numbers, health plan beneficiary numbers, account numbers, certificate/license numbers, vehicle identifiers, device identifiers, URLs, IP addresses, biometric identifiers, full-face photos, any other unique number.

3. **Given** a `DeidentifiedClaim` instance, **When** I check `claim.is_deidentified`, **Then** it returns `True`. **And** the type system (mypy/pyright) distinguishes `DeidentifiedClaim` from `ClaimData`.

4. **Given** any code path that calls an LLM, **When** I trace the data flow, **Then** `BaseLLMClient.send_messages()` accepts only `DeidentifiedClaim` at the type level. **And** a runtime assertion `assert claim.is_deidentified` provides belt-and-suspenders protection.

5. **Given** a claim with edge cases (PHI in unexpected fields, mixed PHI/clinical data), **When** the de-identifier processes it, **Then** it errs on the side of stripping — false positive removal is acceptable, false negative (PHI leakage) is not.

6. **Given** a `DeidentifiedClaim`, **When** I inspect `patient_age`, **Then** ages 90+ are capped to `90` per HIPAA Safe Harbor rules.

7. **Given** a `DeidentifiedClaim`, **When** I inspect `service_year`, **Then** only the year portion of service dates is retained (not month/day).

8. **Given** any `DeidentifiedClaim`, **When** I inspect all fields, **Then** no raw dates (full YYYY-MM-DD) appear anywhere — only year values.

9. **Given** `ClaimDeidentifier`, **When** I call `deidentify()` multiple times with the same input, **Then** the output is deterministic (identical each time). **And** the deidentifier is stateless.

10. **Given** a `DeidentifiedClaim`, **When** I inspect the `lines` property, **Then** each line retains `procedure_code`, `modifiers`, `diagnosis_pointers`, `charge_amount`, `units`, `place_of_service`, and `service_year` (derived from `service_date_from`). **And** `rendering_provider_npi` is retained (NPI is not PHI). **And** no full dates appear.

11. **Given** the `DeidentifiedClaim` model, **When** I check `from claim_validator.models import DeidentifiedClaim`, **Then** it is importable from the models subpackage and from the top-level `claim_validator` package.

## Tasks / Subtasks

- [x] Task 1: Implement `DeidentifiedClaim` and `DeidentifiedLineData` in `src/claim_validator/models/deidentified.py` (AC: #3, #6, #7, #8, #10)
  - [x] `DeidentifiedClaim` frozen Pydantic model with non-PHI fields only
  - [x] `is_deidentified` property returning `Literal[True]`
  - [x] `DeidentifiedLineData` for de-identified line items (service_year instead of dates)
  - [x] `patient_age: int | None` (capped at 90 per Safe Harbor)
  - [x] `service_year: int | None` (year only, no month/day)
  - [x] All NPI fields retained (NPI is not PHI per HHS)
  - [x] Clinical data retained: codes, charges, modifiers, diagnosis_pointers, units
- [x] Task 2: Implement `ClaimDeidentifier` in `src/claim_validator/deidentifier/deidentifier.py` (AC: #1, #2, #5, #6, #7, #9)
  - [x] `deidentify(claim: ClaimData) -> DeidentifiedClaim` classmethod
  - [x] Strip all patient/subscriber names
  - [x] Convert DOB to age (capped at 90)
  - [x] Strip subscriber_id (health plan beneficiary number)
  - [x] Convert full dates to year only
  - [x] Retain NPI, payer_id, codes, charges, gender, place_of_service
  - [x] Process all claim lines → `DeidentifiedLineData`
  - [x] Stateless, deterministic, no side effects
- [x] Task 3: Write tests in `tests/test_deidentifier/test_deidentifier.py` (AC: #1-#11)
  - [x] Test all 18 HIPAA identifier categories stripped
  - [x] Test patient names removed
  - [x] Test subscriber names removed
  - [x] Test DOB → age conversion
  - [x] Test age 90+ capped to 90 (Safe Harbor)
  - [x] Test subscriber_id stripped
  - [x] Test dates → year only
  - [x] Test NPI retained (not PHI)
  - [x] Test payer_id retained
  - [x] Test clinical codes retained
  - [x] Test charges retained
  - [x] Test gender retained
  - [x] Test is_deidentified property
  - [x] Test DeidentifiedClaim distinct from ClaimData (type check)
  - [x] Test line-level de-identification
  - [x] Test edge cases: empty claim, None fields, missing DOB
  - [x] Test determinism (same input → same output)
  - [x] Test statelessness (multiple calls)
  - [x] Test no full dates in any field
- [x] Task 4: Write tests in `tests/test_models/test_deidentified.py` (AC: #3, #6, #8, #10)
  - [x] Test DeidentifiedClaim model creation
  - [x] Test frozen immutability
  - [x] Test is_deidentified returns True
  - [x] Test DeidentifiedLineData model
  - [x] Test age capping at 90
  - [x] Test service_year is int
- [x] Task 5: Update `deidentifier/__init__.py` re-exports
  - [x] Add `ClaimDeidentifier` re-export
- [x] Task 6: Update `models/__init__.py` re-exports
  - [x] Add `DeidentifiedClaim`, `DeidentifiedLineData` re-exports
- [x] Task 7: Update top-level `__init__.py` re-exports
  - [x] Add `ClaimDeidentifier` import from `deidentifier`
  - [x] Add `DeidentifiedClaim` import from `models`
  - [x] Add both to `__all__`
- [x] Task 8: Verify tooling
  - [x] `uv run ruff check .` — zero warnings
  - [x] `uv run mypy src/` — zero errors (37 source files)
  - [x] `uv run pytest` — 521 tests pass (453 existing + 68 new)

## Dev Notes

### Project Location

`/home/lnv-20/Documents/claude/claim-validator/`

### Previous Story Intelligence (Story 2.8)

- ValidationPipeline completed with two-phase execution, builder pattern, from_settings()
- Pipeline already has AI phase gate logic (`skip_ai_on_rule_failure`)
- 453 tests passing, ruff/mypy clean (36 source files)
- uv PATH: `export PATH="$HOME/snap/code/225/.local/bin:$PATH"`
- Line-length limit is 100 characters — wrap long strings with implicit concatenation
- Test pattern: `_valid_claim_dict()` helper, class-based tests with `setup_method`
- ruff catches unused imports (F401), unsorted imports (I001), CamelCase aliases (N817)
- `head` and `tail` commands unavailable in sandbox — don't pipe to them

### Current State of Key Files

| File | Status | Notes |
|---|---|---|
| `models/deidentified.py` | **STUB** — only docstring | Needs `DeidentifiedClaim`, `DeidentifiedLineData` |
| `deidentifier/__init__.py` | **EMPTY** (0 bytes) | Needs `ClaimDeidentifier` re-export |
| `deidentifier/deidentifier.py` | **DOES NOT EXIST** | Needs full implementation |
| `models/claim.py` | Complete | `ClaimData`, `ClaimLineData`, `DiagnosisCode` (frozen Pydantic) |
| `models/__init__.py` | Complete | Re-exports 7 models, needs `DeidentifiedClaim` added |
| `__init__.py` | Complete | Re-exports 19 symbols, needs `ClaimDeidentifier`, `DeidentifiedClaim` |
| `exceptions.py` | Complete | `ClaimValidatorError`, `ValidationError`, `ConfigurationError`, `LLMError`, `CodeTableError` |
| `constants.py` | Complete | `Severity`, `ClaimType` enums |
| `validators/pipeline.py` | Complete | Two-phase pipeline, AI phase gate |

### HIPAA Safe Harbor De-identification — 18 Identifier Categories

Per 45 CFR § 164.514(b)(2), the following 18 types of identifiers must be removed:

| # | Identifier | ClaimData Fields Affected | De-identification Strategy |
|---|---|---|---|
| 1 | Names | `patient_first_name`, `patient_last_name`, `subscriber_first_name`, `subscriber_last_name` | Strip entirely |
| 2 | Geographic data (below state) | None currently in model | N/A (model has no address fields) |
| 3 | Dates (except year) for ages < 90 | `patient_dob`, `subscriber_dob`, `filing_date`, `service_date_from`, `service_date_to` | Convert to year only or age |
| 4 | Phone numbers | None currently in model | N/A |
| 5 | Fax numbers | None currently in model | N/A |
| 6 | Email addresses | None currently in model | N/A |
| 7 | SSN | None currently in model | N/A |
| 8 | Medical record numbers | None currently in model | N/A |
| 9 | Health plan beneficiary numbers | `subscriber_id` | Strip entirely |
| 10 | Account numbers | None currently in model | N/A |
| 11 | Certificate/license numbers | None currently in model | N/A |
| 12 | Vehicle identifiers | None currently in model | N/A |
| 13 | Device identifiers | None currently in model | N/A |
| 14 | Web URLs | None currently in model | N/A |
| 15 | IP addresses | None currently in model | N/A |
| 16 | Biometric identifiers | None currently in model | N/A |
| 17 | Full-face photos | None currently in model | N/A |
| 18 | Any other unique identifying number | None currently in model | N/A |

**Key insight:** The `ClaimData` model is domain-constrained — it only contains CMS-1500 claim fields, not arbitrary patient records. Most HIPAA identifiers (phone, email, SSN, address, etc.) are not present in the model. The PHI-carrying fields are: **names** (4 fields), **dates** (5 fields), and **subscriber_id** (1 field).

**NPI is NOT PHI:** Per HHS guidance, NPIs are public provider identifiers, not patient identifiers. They are retained in `DeidentifiedClaim`.

**Payer ID is NOT PHI:** Payer identifiers are organization identifiers, not patient identifiers. Retained.

### Implementation Spec

```python
# src/claim_validator/models/deidentified.py
"""De-identified claim model — DeidentifiedClaim."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


class DeidentifiedLineData(BaseModel):
    """De-identified service line — dates replaced with year only."""

    model_config = ConfigDict(frozen=True, strict=False)

    procedure_code: str
    modifiers: list[str] = []
    diagnosis_pointers: list[int] = []
    charge_amount: float
    units: float = 1.0
    place_of_service: str | None = None
    rendering_provider_npi: str | None = None
    service_year: int | None = None


class DeidentifiedClaim(BaseModel):
    """HIPAA Safe Harbor de-identified claim.

    Contains only clinically relevant, non-PHI data
    suitable for LLM consumption. Created exclusively
    by ``ClaimDeidentifier.deidentify()``.
    """

    model_config = ConfigDict(frozen=True, strict=False)

    # Provider (NPI is public, not PHI)
    billing_provider_npi: str | None = None
    billing_provider_taxonomy: str | None = None
    rendering_provider_npi: str | None = None

    # Demographics (de-identified)
    patient_age: int | None = None  # Capped at 90 per Safe Harbor
    patient_gender: str | None = None

    # Payer (organization identifier, not PHI)
    payer_id: str | None = None
    payer_name: str | None = None

    # Claim metadata
    claim_type: str = "professional"
    place_of_service: str | None = None
    total_charge: float | None = None

    # Clinical data (codes are not PHI)
    diagnosis_codes: list[dict[str, str | int]] = []
    lines: list[DeidentifiedLineData] = []

    @property
    def is_deidentified(self) -> Literal[True]:
        """Type-level marker that this claim is de-identified."""
        return True
```

```python
# src/claim_validator/deidentifier/deidentifier.py
"""ClaimDeidentifier — HIPAA Safe Harbor de-identification."""

from __future__ import annotations

import datetime

from claim_validator.models.claim import ClaimData
from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)

# Safe Harbor age cap: ages 90+ reported as 90
_SAFE_HARBOR_AGE_CAP = 90


class ClaimDeidentifier:
    """Strips all 18 HIPAA identifiers from a ClaimData instance.

    Stateless — safe for concurrent use, deterministic output.
    """

    @classmethod
    def deidentify(cls, claim: ClaimData) -> DeidentifiedClaim:
        """De-identify a claim for LLM consumption.

        Strips: names, dates (except year), subscriber ID.
        Retains: NPI, codes, charges, gender, payer ID, age.
        Ages 90+ capped to 90 per HIPAA Safe Harbor.
        """
        patient_age = cls._compute_age(claim.patient_dob)

        lines = [
            cls._deidentify_line(line)
            for line in claim.lines
        ]

        diagnosis_codes = [
            {"code": dx.code, "pointer": dx.pointer}
            for dx in claim.diagnosis_codes
        ]

        return DeidentifiedClaim(
            billing_provider_npi=claim.billing_provider_npi,
            billing_provider_taxonomy=(
                claim.billing_provider_taxonomy
            ),
            rendering_provider_npi=(
                claim.rendering_provider_npi
            ),
            patient_age=patient_age,
            patient_gender=claim.patient_gender,
            payer_id=claim.payer_id,
            payer_name=claim.payer_name,
            claim_type=claim.claim_type,
            place_of_service=claim.place_of_service,
            total_charge=claim.total_charge,
            diagnosis_codes=diagnosis_codes,
            lines=lines,
        )

    @classmethod
    def _deidentify_line(
        cls, line: ClaimLineData,
    ) -> DeidentifiedLineData:
        """Strip PHI from a single claim line."""
        service_year = cls._extract_year(
            line.service_date_from,
        )
        return DeidentifiedLineData(
            procedure_code=line.procedure_code,
            modifiers=list(line.modifiers),
            diagnosis_pointers=list(
                line.diagnosis_pointers
            ),
            charge_amount=line.charge_amount,
            units=line.units,
            place_of_service=line.place_of_service,
            rendering_provider_npi=(
                line.rendering_provider_npi
            ),
            service_year=service_year,
        )

    @staticmethod
    def _compute_age(
        dob_str: str | None,
    ) -> int | None:
        """Convert DOB string to age, capped at 90."""
        if not dob_str:
            return None
        try:
            dob = datetime.date.fromisoformat(dob_str)
        except (ValueError, TypeError):
            return None
        today = datetime.date.today()
        age = (
            today.year - dob.year
            - (
                (today.month, today.day)
                < (dob.month, dob.day)
            )
        )
        return min(age, _SAFE_HARBOR_AGE_CAP)

    @staticmethod
    def _extract_year(
        date_str: str | None,
    ) -> int | None:
        """Extract year from a date string."""
        if not date_str:
            return None
        try:
            return datetime.date.fromisoformat(
                date_str
            ).year
        except (ValueError, TypeError):
            return None
```

Note: `_deidentify_line` references `ClaimLineData` — add the import:
```python
from claim_validator.models.claim import ClaimData, ClaimLineData
```

### Key Design Decisions

- **`DeidentifiedClaim` is a separate model**, NOT a subclass of `ClaimData` — type system enforces the distinction
- **`is_deidentified` returns `Literal[True]`** — enables mypy to distinguish at the type level
- **`diagnosis_codes` uses `list[dict]`** not `list[DiagnosisCode]` — avoids carrying the `DiagnosisCode` model (which could theoretically be extended with PHI in future); plain dict with `code` and `pointer` keys is sufficient for LLM context
- **Age capping at 90** — HIPAA Safe Harbor requires ages 90+ to be aggregated into a single category
- **`_compute_age` uses `datetime.date.today()`** — deterministic for same-day calls; tests should mock `datetime.date.today()` for reproducibility
- **`ClaimDeidentifier` is a classmethod-based class** (no `__init__`, no state) — stateless by design, safe for concurrent use
- **NPI retained** — HHS explicitly states NPI is a public provider identifier, not patient PHI
- **Payer ID retained** — organization identifier, not patient PHI
- **`service_year`** replaces `service_date_from`/`service_date_to` — only year retained per Safe Harbor
- **De-identifier is in core** (no optional dependencies) — available without `[ai]` extra

### Anti-Patterns to Avoid

- **DO NOT** make `DeidentifiedClaim` a subclass of `ClaimData` — they must be distinct types
- **DO NOT** retain full dates (YYYY-MM-DD) anywhere in `DeidentifiedClaim` — only year values
- **DO NOT** retain patient/subscriber names, DOBs, or subscriber IDs
- **DO NOT** use `datetime.datetime` when `datetime.date` suffices for DOB/service date parsing
- **DO NOT** add logging that could leak PHI — no log statements in the de-identifier
- **DO NOT** store state in `ClaimDeidentifier` — it must be stateless (classmethod pattern)
- **DO NOT** raise exceptions for missing PHI fields — return `None` for missing data gracefully
- **DO NOT** include `filing_date` in `DeidentifiedClaim` — it's a full date, not needed for clinical assessment

### Architecture Decisions

| Decision | Requirement |
|---|---|
| **D5** | De-identification pipeline-integrated, automatic before any AI validator |
| **D6** | PHI boundary — Type-driven `DeidentifiedClaim` + runtime assertion (belt-and-suspenders) |
| **FR21** | Auto de-identify claims before sending to any LLM (18 HIPAA identifiers) |
| **FR22** | Send only non-PHI clinically relevant data to LLMs |
| **NFR8** | Zero PHI transmission (rule-based) — no network calls ever |
| **NFR9** | PHI de-identification (AI) — all 18 HIPAA identifiers stripped before LLM |
| **NFR10** | No PHI in outputs — no PHI in logs, exceptions, or findings |
| **NFR15** | Stateless validation — no state between calls |
| **NFR17** | Deterministic results — identical output per input |

### Future Integration Points

The `DeidentifiedClaim` model will be consumed by:
- **Story 3.2** (`BaseLLMClient`) — `send_messages()` will accept only `DeidentifiedClaim` at the type level
- **Story 3.3** (`AI Validation Pipeline Integration`) — Pipeline will call `ClaimDeidentifier.deidentify()` before passing to AI validators
- **Story 3.4** (`AI Clinical Validators`) — Each AI validator receives `DeidentifiedClaim`, not `ClaimData`

### References

- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.1] — Full acceptance criteria
- [Source: _bmad-output/planning-artifacts/architecture.md#Security Architecture (HIPAA) — D5, D6]
- [Source: _bmad-output/planning-artifacts/architecture.md#Process Patterns — Validator implementation contract]
- [Source: _bmad-output/planning-artifacts/prd.md#FR21] — Auto de-identify claims before LLM
- [Source: _bmad-output/planning-artifacts/prd.md#FR22] — Send only non-PHI data to LLMs
- [Source: _bmad-output/planning-artifacts/prd.md#NFR8-NFR10] — Security requirements
- [Source: 45 CFR § 164.514(b)(2)] — HIPAA Safe Harbor De-identification standard

## Dev Agent Record

### Agent Model Used
Claude Opus 4.6

### Debug Log References
- RED phase: Tests fail with ImportError (deidentified.py stub, deidentifier.py nonexistent)
- GREEN phase: All 521 tests pass after implementation
- Ruff: 4 issues fixed (3x N817 CamelCase alias, 1x I001 unsorted imports in tests)
- Mypy: 0 errors in 37 source files

### Completion Notes List
- DeidentifiedClaim and DeidentifiedLineData implemented as frozen Pydantic models
- ClaimDeidentifier implemented with classmethod pattern — stateless, deterministic
- Age capping at 90 per HIPAA Safe Harbor (45 CFR § 164.514(b)(2))
- Dates reduced to year only — no full YYYY-MM-DD in output
- NPI retained (public provider identifier, not PHI per HHS)
- 68 new tests: 18 model tests + 40 deidentifier tests + 10 import/edge case tests
- All re-exports updated: deidentifier/__init__.py, models/__init__.py, top-level __init__.py

### File List
- `src/claim_validator/models/deidentified.py` — DeidentifiedClaim, DeidentifiedLineData (new)
- `src/claim_validator/deidentifier/deidentifier.py` — ClaimDeidentifier (new)
- `src/claim_validator/deidentifier/__init__.py` — re-export (updated from empty)
- `src/claim_validator/models/__init__.py` — added DeidentifiedClaim, DeidentifiedLineData (modified)
- `src/claim_validator/__init__.py` — added ClaimDeidentifier, DeidentifiedClaim, DeidentifiedLineData (modified)
- `tests/test_models/test_deidentified.py` — 18 model tests (new)
- `tests/test_deidentifier/test_deidentifier.py` — ~50 deidentifier tests (new)

### Change Log
| Change | Date | Reason |
|---|---|---|
| Initial creation | 2026-02-18 | Sprint planning workflow |
| Implementation complete | 2026-02-18 | All tasks done, 521 tests pass, ruff/mypy clean |
