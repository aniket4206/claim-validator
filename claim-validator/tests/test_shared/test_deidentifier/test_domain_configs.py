"""Tests for domain-specific de-identification configs — claim, eligibility, prior auth."""

from __future__ import annotations

import pytest

from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.shared.deidentifier.config import (
    CLAIM_DEID_CONFIG,
    ELIGIBILITY_DEID_CONFIG,
    PA_DEID_CONFIG,
)

# ---------------------------------------------------------------------------
# Claims domain
# ---------------------------------------------------------------------------


class TestClaimDeidConfig:
    """CLAIM_DEID_CONFIG strips correct fields for the claims domain."""

    @pytest.fixture()
    def deid(self) -> BaseDeidentifier:
        return BaseDeidentifier(CLAIM_DEID_CONFIG)

    @pytest.fixture()
    def sample_claim(self) -> dict[str, object]:
        return {
            "patient_first_name": "John",
            "patient_last_name": "Doe",
            "service_date_from": "2024-03-15",
            "service_date_to": "2024-03-15",
            "subscriber_id": "SUB123456",
            "patient_address": "123 Main St",
            "patient_city": "Springfield",
            "patient_state": "IL",
            "patient_zip": "62701",
            "patient_dob": "1985-06-15",
            "diagnosis_code": "J06.9",
            "procedure_code": "99213",
            "npi": "1234567893",
            "charge_amount": 150.00,
        }

    def test_names_stripped(self, deid: BaseDeidentifier, sample_claim: dict[str, object]) -> None:
        result = deid.deidentify(sample_claim)
        assert result["patient_first_name"] is None
        assert result["patient_last_name"] is None

    def test_dates_reduced(self, deid: BaseDeidentifier, sample_claim: dict[str, object]) -> None:
        result = deid.deidentify(sample_claim)
        assert result["service_date_from"] == 2024
        assert result["service_date_to"] == 2024

    def test_subscriber_id_stripped(
        self, deid: BaseDeidentifier, sample_claim: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_claim)
        assert result["subscriber_id"] is None

    def test_addresses_stripped(
        self, deid: BaseDeidentifier, sample_claim: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_claim)
        assert result["patient_address"] is None
        assert result["patient_city"] is None
        assert result["patient_state"] is None
        assert result["patient_zip"] is None

    def test_age_computed_and_capped(
        self, deid: BaseDeidentifier, sample_claim: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_claim)
        # Age from 1985 DOB should be around 40-41, not capped
        assert isinstance(result["patient_dob"], int)
        assert result["patient_dob"] < 90

    def test_age_over_90_capped(self, deid: BaseDeidentifier) -> None:
        data = {"patient_dob": "1920-01-01"}
        result = deid.deidentify(data)
        assert result["patient_dob"] == 90

    def test_non_phi_preserved(
        self, deid: BaseDeidentifier, sample_claim: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_claim)
        assert result["diagnosis_code"] == "J06.9"
        assert result["procedure_code"] == "99213"
        assert result["npi"] == "1234567893"
        assert result["charge_amount"] == 150.00

    def test_phi_values_not_in_output(
        self, deid: BaseDeidentifier, sample_claim: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_claim)
        values = list(result.values())
        assert "John" not in values
        assert "Doe" not in values
        assert "SUB123456" not in values
        assert "123 Main St" not in values
        assert "Springfield" not in values


# ---------------------------------------------------------------------------
# Eligibility domain
# ---------------------------------------------------------------------------


class TestEligibilityDeidConfig:
    """ELIGIBILITY_DEID_CONFIG strips correct fields for the eligibility domain."""

    @pytest.fixture()
    def deid(self) -> BaseDeidentifier:
        return BaseDeidentifier(ELIGIBILITY_DEID_CONFIG)

    @pytest.fixture()
    def sample_elig(self) -> dict[str, object]:
        return {
            "subscriber_name": "Jane Smith",
            "effective_date": "2024-01-01",
            "termination_date": "2024-12-31",
            "member_id": "MEM789",
            "group_number": "GRP456",
            "plan_name": "Gold PPO",
            "payer_id": "PAYER001",
            "coverage_active": True,
        }

    def test_subscriber_name_stripped(
        self, deid: BaseDeidentifier, sample_elig: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_elig)
        assert result["subscriber_name"] is None

    def test_dates_reduced(self, deid: BaseDeidentifier, sample_elig: dict[str, object]) -> None:
        result = deid.deidentify(sample_elig)
        assert result["effective_date"] == 2024
        assert result["termination_date"] == 2024

    def test_ids_stripped(self, deid: BaseDeidentifier, sample_elig: dict[str, object]) -> None:
        result = deid.deidentify(sample_elig)
        assert result["member_id"] is None
        assert result["group_number"] is None

    def test_no_age_processing(
        self, deid: BaseDeidentifier, sample_elig: dict[str, object]
    ) -> None:
        """Eligibility has no age_field — DOB-like fields are untouched."""
        sample_elig["dob"] = "1990-01-01"
        result = deid.deidentify(sample_elig)
        assert result["dob"] == "1990-01-01"

    def test_no_address_stripping(self, deid: BaseDeidentifier) -> None:
        """Eligibility has no address fields configured."""
        data = {"address": "742 Evergreen", "subscriber_name": "Homer"}
        result = deid.deidentify(data)
        assert result["address"] == "742 Evergreen"
        assert result["subscriber_name"] is None

    def test_non_phi_preserved(
        self, deid: BaseDeidentifier, sample_elig: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_elig)
        assert result["plan_name"] == "Gold PPO"
        assert result["payer_id"] == "PAYER001"
        assert result["coverage_active"] is True

    def test_phi_values_not_in_output(
        self, deid: BaseDeidentifier, sample_elig: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_elig)
        values = list(result.values())
        assert "Jane Smith" not in values
        assert "MEM789" not in values
        assert "GRP456" not in values


# ---------------------------------------------------------------------------
# Prior Auth domain
# ---------------------------------------------------------------------------


class TestPaDeidConfig:
    """PA_DEID_CONFIG strips correct fields for the prior auth domain."""

    @pytest.fixture()
    def deid(self) -> BaseDeidentifier:
        return BaseDeidentifier(PA_DEID_CONFIG)

    @pytest.fixture()
    def sample_pa(self) -> dict[str, object]:
        return {
            "patient_name": "Bob Johnson",
            "effective_date": "2024-04-01",
            "expiration_date": "2025-03-31",
            "authorization_number": "AUTH789012",
            "member_id": "MEM456",
            "patient_address": "789 Elm St",
            "patient_dob": "1960-08-20",
            "diagnosis_code": "M54.5",
            "procedure_code": "27447",
            "status": "approved",
        }

    def test_patient_name_stripped(
        self, deid: BaseDeidentifier, sample_pa: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_pa)
        assert result["patient_name"] is None

    def test_dates_reduced(self, deid: BaseDeidentifier, sample_pa: dict[str, object]) -> None:
        result = deid.deidentify(sample_pa)
        assert result["effective_date"] == 2024
        assert result["expiration_date"] == 2025

    def test_ids_stripped(self, deid: BaseDeidentifier, sample_pa: dict[str, object]) -> None:
        result = deid.deidentify(sample_pa)
        assert result["authorization_number"] is None
        assert result["member_id"] is None

    def test_address_stripped(self, deid: BaseDeidentifier, sample_pa: dict[str, object]) -> None:
        result = deid.deidentify(sample_pa)
        assert result["patient_address"] is None

    def test_age_computed(self, deid: BaseDeidentifier, sample_pa: dict[str, object]) -> None:
        result = deid.deidentify(sample_pa)
        assert isinstance(result["patient_dob"], int)
        assert result["patient_dob"] < 90  # 1960 DOB → ~65

    def test_age_over_90_capped(self, deid: BaseDeidentifier) -> None:
        data = {"patient_dob": "1920-01-01"}
        result = deid.deidentify(data)
        assert result["patient_dob"] == 90

    def test_non_phi_preserved(
        self, deid: BaseDeidentifier, sample_pa: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_pa)
        assert result["diagnosis_code"] == "M54.5"
        assert result["procedure_code"] == "27447"
        assert result["status"] == "approved"

    def test_phi_values_not_in_output(
        self, deid: BaseDeidentifier, sample_pa: dict[str, object]
    ) -> None:
        result = deid.deidentify(sample_pa)
        values = list(result.values())
        assert "Bob Johnson" not in values
        assert "AUTH789012" not in values
        assert "MEM456" not in values
        assert "789 Elm St" not in values


# ---------------------------------------------------------------------------
# Cross-domain: HIPAA 18 identifier coverage
# ---------------------------------------------------------------------------


class TestHipaa18IdentifierCoverage:
    """All 3 domain configs together cover the relevant HIPAA identifiers."""

    def test_names_covered(self) -> None:
        """At least one config strips name fields."""
        all_name_fields = (
            CLAIM_DEID_CONFIG.name_fields
            + ELIGIBILITY_DEID_CONFIG.name_fields
            + PA_DEID_CONFIG.name_fields
        )
        assert len(all_name_fields) > 0

    def test_dates_covered(self) -> None:
        """All 3 configs handle date fields."""
        assert len(CLAIM_DEID_CONFIG.date_fields) > 0
        assert len(ELIGIBILITY_DEID_CONFIG.date_fields) > 0
        assert len(PA_DEID_CONFIG.date_fields) > 0

    def test_identifiers_covered(self) -> None:
        """All 3 configs handle identifier fields."""
        assert len(CLAIM_DEID_CONFIG.id_fields) > 0
        assert len(ELIGIBILITY_DEID_CONFIG.id_fields) > 0
        assert len(PA_DEID_CONFIG.id_fields) > 0

    def test_age_cap_where_applicable(self) -> None:
        """Domains with DOB have age_field set."""
        assert CLAIM_DEID_CONFIG.age_field is not None
        assert PA_DEID_CONFIG.age_field is not None

    def test_addresses_where_applicable(self) -> None:
        """Claims and PA have address fields."""
        assert len(CLAIM_DEID_CONFIG.address_fields) > 0
        assert len(PA_DEID_CONFIG.address_fields) > 0


# ---------------------------------------------------------------------------
# Cross-domain: Input immutability
# ---------------------------------------------------------------------------


class TestDomainConfigInputImmutability:
    """deidentify() never mutates input for any domain config."""

    @pytest.mark.parametrize(
        "config",
        [CLAIM_DEID_CONFIG, ELIGIBILITY_DEID_CONFIG, PA_DEID_CONFIG],
        ids=["claim", "eligibility", "prior_auth"],
    )
    def test_input_not_mutated(self, config: object) -> None:
        deid = BaseDeidentifier(config)  # type: ignore[arg-type]
        data = {
            "patient_first_name": "Test",
            "patient_last_name": "User",
            "subscriber_name": "Test User",
            "patient_name": "Test User",
            "service_date_from": "2024-01-01",
            "service_date_to": "2024-01-01",
            "effective_date": "2024-01-01",
            "termination_date": "2024-12-31",
            "expiration_date": "2025-01-01",
            "subscriber_id": "SUB1",
            "member_id": "MEM1",
            "group_number": "GRP1",
            "authorization_number": "AUTH1",
            "patient_address": "1 Test St",
            "patient_city": "Test City",
            "patient_state": "TS",
            "patient_zip": "00000",
            "patient_dob": "1990-01-01",
        }
        original = {**data}
        deid.deidentify(data)
        assert data == original
