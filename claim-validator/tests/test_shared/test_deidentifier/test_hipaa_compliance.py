"""HIPAA compliance verification tests for all 3 domains.

Verifies the shared BaseDeidentifier strips all applicable HIPAA Safe Harbor
identifiers for claims, eligibility, and prior auth domains.  No source files
are created or modified — this module exercises existing Story 2.1 code.

Covers:
- Per-domain PHI verification (AC-1, AC-2, AC-3)
- Cross-domain PHI leak scanning (AC-4)
- HIPAA Safe Harbor age cap at 90 (AC-5)
- Date reduction to year-only int (AC-6)
"""

from __future__ import annotations

import datetime
from typing import Any

import pytest

from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.shared.deidentifier.config import (
    CLAIM_DEID_CONFIG,
    ELIGIBILITY_DEID_CONFIG,
    PA_DEID_CONFIG,
    DeidentificationConfig,
)

# ---------------------------------------------------------------------------
# Sample PHI data per domain
# ---------------------------------------------------------------------------

CLAIM_SAMPLE: dict[str, Any] = {
    "patient_first_name": "Robert",
    "patient_last_name": "Johnson",
    "service_date_from": "2024-03-15",
    "service_date_to": "2024-03-20",
    "subscriber_id": "SUB-987654321",
    "patient_address": "742 Evergreen Terrace",
    "patient_city": "Springfield",
    "patient_state": "IL",
    "patient_zip": "62701",
    "patient_dob": "1985-06-15",
    # Non-PHI fields
    "diagnosis_code": "J06.9",
    "procedure_code": "99213",
    "npi": "1234567890",
    "charge_amount": 250.00,
}

ELIG_SAMPLE: dict[str, Any] = {
    "subscriber_name": "Maria Garcia",
    "effective_date": "2024-01-01",
    "termination_date": "2024-12-31",
    "member_id": "MEM-123456",
    "group_number": "GRP-789",
    # Non-PHI fields
    "plan_name": "Gold PPO",
    "payer_id": "BCBS-IL",
    "coverage_active": True,
}

PA_SAMPLE: dict[str, Any] = {
    "patient_name": "James Williams",
    "effective_date": "2024-02-01",
    "expiration_date": "2024-08-01",
    "authorization_number": "AUTH-2024-00123",
    "member_id": "MEM-555777",
    "patient_address": "1600 Pennsylvania Ave NW, Washington DC 20500",
    "patient_dob": "1990-11-20",
    # Non-PHI fields
    "diagnosis_code": "M54.5",
    "procedure_code": "97110",
    "status": "approved",
}

# ---------------------------------------------------------------------------
# Shared test constants
# ---------------------------------------------------------------------------

_AGE_BOUNDARY_CASES = [
    (89, 89),
    (90, 90),
    (91, 90),
    (95, 90),
    (100, 90),
]
_AGE_BOUNDARY_IDS = ["age-89", "age-90", "age-91", "age-95", "age-100"]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _phi_field_names(config: DeidentificationConfig) -> set[str]:
    """Return all PHI field names declared in a config."""
    fields: set[str] = set()
    fields.update(config.name_fields)
    fields.update(config.date_fields)
    fields.update(config.id_fields)
    fields.update(config.address_fields)
    if config.age_field:
        fields.add(config.age_field)
    return fields


def _assert_no_phi_leak(
    input_data: dict[str, Any],
    output_data: dict[str, Any],
    config: DeidentificationConfig,
) -> None:
    """Assert no raw PHI value from input appears in output values.

    Only checks values of fields that the config declares as PHI.
    Non-PHI fields are expected to pass through unchanged and are excluded.

    Note: if a PHI field value coincidentally equals a non-PHI field value,
    this scan will flag it — conservative by design (FR40).
    Error messages reference field names only, never PHI values (AC-4).
    """
    phi_fields = _phi_field_names(config)
    output_values: set[Any] = set()
    for v in output_data.values():
        if v is not None:
            output_values.add(v)

    for key in phi_fields:
        if key not in input_data:
            continue
        value = input_data[key]
        if isinstance(value, str) and value:
            assert value not in output_values, (
                f"PHI leak detected: field '{key}' value was not stripped from output"
            )


# ---------------------------------------------------------------------------
# Claims domain HIPAA compliance (AC-1, AC-4, AC-5, AC-6)
# ---------------------------------------------------------------------------


class TestClaimHipaaCompliance:
    """Verify HIPAA compliance for the claims domain."""

    def setup_method(self) -> None:
        self.deid = BaseDeidentifier(CLAIM_DEID_CONFIG)
        self.sample: dict[str, Any] = {**CLAIM_SAMPLE}

    # Task 2.1 — name fields stripped
    def test_patient_first_name_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_first_name"] is None

    def test_patient_last_name_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_last_name"] is None

    # Task 2.2 — date fields reduced to year-only int
    def test_service_date_from_reduced_to_year(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["service_date_from"] == 2024

    def test_service_date_to_reduced_to_year(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["service_date_to"] == 2024

    # Task 2.3 — subscriber_id stripped
    def test_subscriber_id_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["subscriber_id"] is None

    # Task 2.4 — address fields stripped
    def test_patient_address_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_address"] is None

    def test_patient_city_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_city"] is None

    def test_patient_state_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_state"] is None

    def test_patient_zip_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_zip"] is None

    # Task 2.5 — DOB age cap at 90
    def test_dob_replaced_with_age_int(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert isinstance(result["patient_dob"], int)
        assert 0 < result["patient_dob"] < 90

    def test_dob_over_90_capped(self) -> None:
        data = {**self.sample, "patient_dob": "1920-01-01"}
        result = self.deid.deidentify(data)
        assert result["patient_dob"] == 90

    # Task 2.6 — comprehensive PHI leak scan
    def test_phi_leak_scan(self) -> None:
        result = self.deid.deidentify(self.sample)
        _assert_no_phi_leak(self.sample, result, CLAIM_DEID_CONFIG)

    # Task 2.7 — non-PHI fields preserved
    def test_diagnosis_code_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["diagnosis_code"] == "J06.9"

    def test_procedure_code_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["procedure_code"] == "99213"

    def test_npi_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["npi"] == "1234567890"

    def test_charge_amount_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["charge_amount"] == 250.00


# ---------------------------------------------------------------------------
# Eligibility domain HIPAA compliance (AC-2, AC-4, AC-6)
# ---------------------------------------------------------------------------


class TestEligibilityHipaaCompliance:
    """Verify HIPAA compliance for the eligibility domain."""

    def setup_method(self) -> None:
        self.deid = BaseDeidentifier(ELIGIBILITY_DEID_CONFIG)
        self.sample: dict[str, Any] = {**ELIG_SAMPLE}

    # Task 3.1 — subscriber_name stripped
    def test_subscriber_name_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["subscriber_name"] is None

    # Task 3.2 — date fields reduced to year-only int
    def test_effective_date_reduced_to_year(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["effective_date"] == 2024

    def test_termination_date_reduced_to_year(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["termination_date"] == 2024

    # Task 3.3 — member_id and group_number stripped
    def test_member_id_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["member_id"] is None

    def test_group_number_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["group_number"] is None

    # Task 3.4 — no age processing
    def test_no_age_processing_dob_passes_through(self) -> None:
        """Eligibility has no DOB field — age processing is skipped."""
        data = {**self.sample, "patient_dob": "1990-01-01"}
        result = self.deid.deidentify(data)
        assert result["patient_dob"] == "1990-01-01"

    # Task 3.5 — PHI leak scan
    def test_phi_leak_scan(self) -> None:
        result = self.deid.deidentify(self.sample)
        _assert_no_phi_leak(self.sample, result, ELIGIBILITY_DEID_CONFIG)

    # Task 3.6 — non-PHI fields preserved
    def test_plan_name_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["plan_name"] == "Gold PPO"

    def test_payer_id_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["payer_id"] == "BCBS-IL"

    def test_coverage_active_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["coverage_active"] is True


# ---------------------------------------------------------------------------
# Prior auth domain HIPAA compliance (AC-3, AC-4, AC-5, AC-6)
# ---------------------------------------------------------------------------


class TestPaHipaaCompliance:
    """Verify HIPAA compliance for the prior authorization domain."""

    def setup_method(self) -> None:
        self.deid = BaseDeidentifier(PA_DEID_CONFIG)
        self.sample: dict[str, Any] = {**PA_SAMPLE}

    # Task 4.1 — patient_name stripped
    def test_patient_name_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_name"] is None

    # Task 4.2 — date fields reduced to year-only int
    def test_effective_date_reduced_to_year(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["effective_date"] == 2024

    def test_expiration_date_reduced_to_year(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["expiration_date"] == 2024

    # Task 4.3 — authorization_number and member_id stripped
    def test_authorization_number_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["authorization_number"] is None

    def test_member_id_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["member_id"] is None

    # Task 4.4 — patient_address stripped
    def test_patient_address_stripped(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["patient_address"] is None

    # Task 4.5 — DOB age cap at 90
    def test_dob_replaced_with_age_int(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert isinstance(result["patient_dob"], int)
        assert 0 < result["patient_dob"] < 90

    def test_dob_over_90_capped(self) -> None:
        data = {**self.sample, "patient_dob": "1920-01-01"}
        result = self.deid.deidentify(data)
        assert result["patient_dob"] == 90

    # Task 4.6 — PHI leak scan
    def test_phi_leak_scan(self) -> None:
        result = self.deid.deidentify(self.sample)
        _assert_no_phi_leak(self.sample, result, PA_DEID_CONFIG)

    # Task 4.7 — non-PHI fields preserved
    def test_diagnosis_code_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["diagnosis_code"] == "M54.5"

    def test_procedure_code_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["procedure_code"] == "97110"

    def test_status_preserved(self) -> None:
        result = self.deid.deidentify(self.sample)
        assert result["status"] == "approved"


# ---------------------------------------------------------------------------
# HIPAA Safe Harbor edge cases (AC-5, AC-6)
# ---------------------------------------------------------------------------


class TestHipaaSafeHarborEdgeCases:
    """HIPAA Safe Harbor age cap and date reduction boundary tests."""

    # Task 5.1 — age boundary cases for claims
    @pytest.mark.parametrize(
        ("age", "expected"),
        _AGE_BOUNDARY_CASES,
        ids=_AGE_BOUNDARY_IDS,
    )
    def test_claim_age_boundaries(self, age: int, expected: int) -> None:
        """Age <= 90 passes through; age > 90 capped to 90."""
        today = datetime.date.today()
        dob = datetime.date(today.year - age, 1, 1)
        data = {**CLAIM_SAMPLE, "patient_dob": dob.isoformat()}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["patient_dob"] == expected

    # Task 5.1 — age boundary cases for prior auth
    @pytest.mark.parametrize(
        ("age", "expected"),
        _AGE_BOUNDARY_CASES,
        ids=_AGE_BOUNDARY_IDS,
    )
    def test_pa_age_boundaries(self, age: int, expected: int) -> None:
        """Age <= 90 passes through; age > 90 capped to 90."""
        today = datetime.date.today()
        dob = datetime.date(today.year - age, 1, 1)
        data = {**PA_SAMPLE, "patient_dob": dob.isoformat()}
        result = BaseDeidentifier(PA_DEID_CONFIG).deidentify(data)
        assert result["patient_dob"] == expected

    # Task 5.2 — date edge cases
    def test_date_iso_string(self) -> None:
        data = {**CLAIM_SAMPLE, "service_date_from": "2024-06-15"}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["service_date_from"] == 2024

    def test_date_none(self) -> None:
        data = {**CLAIM_SAMPLE, "service_date_from": None}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["service_date_from"] is None

    def test_date_empty_string(self) -> None:
        data = {**CLAIM_SAMPLE, "service_date_from": ""}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["service_date_from"] is None

    def test_date_invalid_string(self) -> None:
        data = {**CLAIM_SAMPLE, "service_date_from": "not-a-date"}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["service_date_from"] is None

    def test_date_datetime_date_object(self) -> None:
        data = {**CLAIM_SAMPLE, "service_date_from": datetime.date(2023, 12, 25)}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["service_date_from"] == 2023

    # Task 5.3 — future DOB returns None
    def test_future_dob_returns_none_claim(self) -> None:
        data = {**CLAIM_SAMPLE, "patient_dob": "2030-01-01"}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["patient_dob"] is None

    def test_future_dob_returns_none_pa(self) -> None:
        data = {**PA_SAMPLE, "patient_dob": "2030-01-01"}
        result = BaseDeidentifier(PA_DEID_CONFIG).deidentify(data)
        assert result["patient_dob"] is None

    # Task 5.3 — datetime.date DOB returns None (compute_age accepts str only)
    def test_datetime_date_dob_returns_none_claim(self) -> None:
        """compute_age() only accepts str|None — datetime.date triggers TypeError → None."""
        data = {**CLAIM_SAMPLE, "patient_dob": datetime.date(1985, 6, 15)}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["patient_dob"] is None

    # Task 5.4 — None DOB returns None
    def test_none_dob_returns_none_claim(self) -> None:
        data = {**CLAIM_SAMPLE, "patient_dob": None}
        result = BaseDeidentifier(CLAIM_DEID_CONFIG).deidentify(data)
        assert result["patient_dob"] is None

    def test_none_dob_returns_none_pa(self) -> None:
        data = {**PA_SAMPLE, "patient_dob": None}
        result = BaseDeidentifier(PA_DEID_CONFIG).deidentify(data)
        assert result["patient_dob"] is None


# ---------------------------------------------------------------------------
# Cross-domain PHI leak scanning (AC-4)
# ---------------------------------------------------------------------------


class TestCrossDomainPhiLeakScan:
    """Cross-domain parametrized PHI leak scanning."""

    # Task 6.1 — parametrized across all 3 domains
    @pytest.mark.parametrize(
        ("config", "sample_data"),
        [
            (CLAIM_DEID_CONFIG, CLAIM_SAMPLE),
            (ELIGIBILITY_DEID_CONFIG, ELIG_SAMPLE),
            (PA_DEID_CONFIG, PA_SAMPLE),
        ],
        ids=["claim", "eligibility", "prior_auth"],
    )
    def test_no_phi_leak(
        self,
        config: DeidentificationConfig,
        sample_data: dict[str, Any],
    ) -> None:
        """No input PHI value appears in any output value."""
        deid = BaseDeidentifier(config)
        result = deid.deidentify(sample_data)
        _assert_no_phi_leak(sample_data, result, config)

    # Task 6.2 — realistic PHI data
    @pytest.mark.parametrize(
        ("config", "sample_data"),
        [
            (
                CLAIM_DEID_CONFIG,
                {
                    "patient_first_name": "Elizabeth",
                    "patient_last_name": "Hernandez-Rodriguez",
                    "service_date_from": "2024-11-23",
                    "service_date_to": "2024-11-25",
                    "subscriber_id": "SSN-555-12-9876",
                    "patient_address": "4521 Oak Boulevard, Apt 12B",
                    "patient_city": "San Francisco",
                    "patient_state": "CA",
                    "patient_zip": "94102-3345",
                    "patient_dob": "1978-09-03",
                    "diagnosis_code": "E11.65",
                    "procedure_code": "36415",
                    "npi": "9876543210",
                    "charge_amount": 1250.75,
                },
            ),
            (
                ELIGIBILITY_DEID_CONFIG,
                {
                    "subscriber_name": "Dr. Patricia Anne O'Sullivan-Yamamoto",
                    "effective_date": "2023-07-01",
                    "termination_date": "2025-06-30",
                    "member_id": "MBR-2024-AZ-00987654",
                    "group_number": "GRPN-CORP-5599",
                    "plan_name": "Platinum HMO Plus",
                    "payer_id": "UHC-WEST",
                    "coverage_active": True,
                },
            ),
            (
                PA_DEID_CONFIG,
                {
                    "patient_name": "Mohammed Al-Rashid bin Abdullah",
                    "effective_date": "2024-04-15",
                    "expiration_date": "2024-10-15",
                    "authorization_number": "PA-2024-FL-00456789",
                    "member_id": "MBR-FL-334455",
                    "patient_address": "789 Cherry Lane, Suite 300, Miami FL 33101",
                    "patient_dob": "1965-02-28",
                    "diagnosis_code": "G43.909",
                    "procedure_code": "64615",
                    "status": "pending_review",
                },
            ),
        ],
        ids=["claim-realistic", "eligibility-realistic", "prior_auth-realistic"],
    )
    def test_realistic_phi_no_leak(
        self,
        config: DeidentificationConfig,
        sample_data: dict[str, Any],
    ) -> None:
        """Realistic PHI data with diverse names and addresses — no leak."""
        deid = BaseDeidentifier(config)
        result = deid.deidentify(sample_data)
        _assert_no_phi_leak(sample_data, result, config)

    # Task 6.3 — output dict keys are preserved
    @pytest.mark.parametrize(
        ("config", "sample_data"),
        [
            (CLAIM_DEID_CONFIG, CLAIM_SAMPLE),
            (ELIGIBILITY_DEID_CONFIG, ELIG_SAMPLE),
            (PA_DEID_CONFIG, PA_SAMPLE),
        ],
        ids=["claim", "eligibility", "prior_auth"],
    )
    def test_output_keys_preserved(
        self,
        config: DeidentificationConfig,
        sample_data: dict[str, Any],
    ) -> None:
        """De-identification changes values only — all keys are preserved."""
        deid = BaseDeidentifier(config)
        result = deid.deidentify(sample_data)
        assert set(result.keys()) == set(sample_data.keys())
