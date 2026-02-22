"""Tests for ClaimDeidentifier — HIPAA Safe Harbor de-identification."""

from __future__ import annotations

import datetime
from unittest.mock import patch

from claim_validator.deidentifier.deidentifier import ClaimDeidentifier
from claim_validator.models.claim import ClaimData
from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)


def _full_phi_claim_dict() -> dict:
    """Claim dict with all PHI fields populated."""
    return {
        "billing_provider_npi": "1234567893",
        "billing_provider_taxonomy": "207Q00000X",
        "rendering_provider_npi": "1306849450",
        "subscriber_id": "XYZ123456",
        "subscriber_first_name": "John",
        "subscriber_last_name": "Smith",
        "subscriber_dob": "1965-03-20",
        "subscriber_gender": "M",
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
        "patient_gender": "F",
        "patient_relationship": "spouse",
        "payer_id": "BCBS001",
        "payer_name": "Blue Cross Blue Shield",
        "claim_type": "professional",
        "place_of_service": "11",
        "total_charge": 300.00,
        "filing_date": "2026-02-15",
        "diagnosis_codes": [
            {"code": "J06.9", "pointer": 1},
            {"code": "R05.9", "pointer": 2},
        ],
        "lines": [
            {
                "procedure_code": "99213",
                "modifiers": ["25"],
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "units": 1.0,
                "service_date_from": "2026-01-15",
                "service_date_to": "2026-01-15",
                "place_of_service": "11",
                "rendering_provider_npi": "1306849450",
            },
            {
                "procedure_code": "20610",
                "diagnosis_pointers": [1, 2],
                "charge_amount": 150.00,
                "units": 1.0,
                "service_date_from": "2026-01-20",
            },
        ],
    }


# --- Core de-identification tests ---


class TestDeidentifyBasic:
    """Test basic de-identification behavior."""

    def setup_method(self) -> None:
        self.claim = ClaimData(**_full_phi_claim_dict())

    def test_returns_deidentified_claim(self) -> None:
        result = ClaimDeidentifier.deidentify(self.claim)
        assert isinstance(result, DeidentifiedClaim)

    def test_is_deidentified_true(self) -> None:
        result = ClaimDeidentifier.deidentify(self.claim)
        assert result.is_deidentified is True

    def test_deterministic(self) -> None:
        r1 = ClaimDeidentifier.deidentify(self.claim)
        r2 = ClaimDeidentifier.deidentify(self.claim)
        assert r1 == r2

    def test_stateless(self) -> None:
        r1 = ClaimDeidentifier.deidentify(self.claim)
        r2 = ClaimDeidentifier.deidentify(self.claim)
        assert r1.patient_age == r2.patient_age
        assert len(r1.lines) == len(r2.lines)


# --- HIPAA identifier stripping tests ---


class TestStripNames:
    """Test patient and subscriber name removal."""

    def setup_method(self) -> None:
        self.claim = ClaimData(**_full_phi_claim_dict())
        self.result = ClaimDeidentifier.deidentify(self.claim)

    def test_patient_first_name_stripped(self) -> None:
        assert not hasattr(self.result, "patient_first_name")

    def test_patient_last_name_stripped(self) -> None:
        assert not hasattr(self.result, "patient_last_name")

    def test_subscriber_first_name_stripped(self) -> None:
        assert not hasattr(self.result, "subscriber_first_name")

    def test_subscriber_last_name_stripped(self) -> None:
        assert not hasattr(self.result, "subscriber_last_name")

    def test_no_name_in_any_field(self) -> None:
        result_str = str(self.result.model_dump())
        assert "Jane" not in result_str
        assert "Doe" not in result_str
        assert "John" not in result_str
        assert "Smith" not in result_str


class TestStripDates:
    """Test date de-identification — only year retained."""

    def setup_method(self) -> None:
        self.claim = ClaimData(**_full_phi_claim_dict())
        self.result = ClaimDeidentifier.deidentify(self.claim)

    def test_patient_dob_stripped(self) -> None:
        assert not hasattr(self.result, "patient_dob")

    def test_subscriber_dob_stripped(self) -> None:
        assert not hasattr(self.result, "subscriber_dob")

    def test_filing_date_stripped(self) -> None:
        assert not hasattr(self.result, "filing_date")

    def test_no_full_dates_in_output(self) -> None:
        result_str = str(self.result.model_dump())
        assert "1990-01-15" not in result_str
        assert "1965-03-20" not in result_str
        assert "2026-02-15" not in result_str
        assert "2026-01-15" not in result_str
        assert "2026-01-20" not in result_str


class TestStripSubscriberID:
    """Test health plan beneficiary number removal."""

    def setup_method(self) -> None:
        self.claim = ClaimData(**_full_phi_claim_dict())
        self.result = ClaimDeidentifier.deidentify(self.claim)

    def test_subscriber_id_stripped(self) -> None:
        assert not hasattr(self.result, "subscriber_id")

    def test_subscriber_id_not_in_output(self) -> None:
        result_str = str(self.result.model_dump())
        assert "XYZ123456" not in result_str


# --- Age computation tests ---


class TestAgeComputation:
    """Test DOB → age conversion with Safe Harbor cap."""

    @patch("claim_validator.deidentifier.deidentifier.datetime")
    def test_age_computed_from_dob(self, mock_dt: object) -> None:
        mock_date = type("MockDate", (), {
            "today": staticmethod(
                lambda: datetime.date(2026, 2, 18)
            ),
            "fromisoformat": datetime.date.fromisoformat,
        })()
        mock_dt.date = mock_date  # type: ignore[attr-defined]
        claim = ClaimData(**_full_phi_claim_dict())
        result = ClaimDeidentifier.deidentify(claim)
        # DOB is 1990-01-15, today is 2026-02-18 → age 36
        assert result.patient_age == 36

    @patch("claim_validator.deidentifier.deidentifier.datetime")
    def test_age_capped_at_90(self, mock_dt: object) -> None:
        mock_date = type("MockDate", (), {
            "today": staticmethod(
                lambda: datetime.date(2026, 2, 18)
            ),
            "fromisoformat": datetime.date.fromisoformat,
        })()
        mock_dt.date = mock_date  # type: ignore[attr-defined]
        d = _full_phi_claim_dict()
        d["patient_dob"] = "1920-01-01"  # age 106 → capped to 90
        claim = ClaimData(**d)
        result = ClaimDeidentifier.deidentify(claim)
        assert result.patient_age == 90

    def test_missing_dob_returns_none(self) -> None:
        d = _full_phi_claim_dict()
        d["patient_dob"] = None
        claim = ClaimData(**d)
        result = ClaimDeidentifier.deidentify(claim)
        assert result.patient_age is None

    def test_empty_dob_returns_none(self) -> None:
        d = _full_phi_claim_dict()
        d["patient_dob"] = ""
        claim = ClaimData(**d)
        result = ClaimDeidentifier.deidentify(claim)
        assert result.patient_age is None

    def test_invalid_dob_returns_none(self) -> None:
        d = _full_phi_claim_dict()
        d["patient_dob"] = "not-a-date"
        claim = ClaimData(**d)
        result = ClaimDeidentifier.deidentify(claim)
        assert result.patient_age is None


# --- Retained data tests ---


class TestRetainedData:
    """Test non-PHI clinical data is retained."""

    def setup_method(self) -> None:
        self.claim = ClaimData(**_full_phi_claim_dict())
        self.result = ClaimDeidentifier.deidentify(self.claim)

    def test_billing_npi_retained(self) -> None:
        assert self.result.billing_provider_npi == "1234567893"

    def test_rendering_npi_retained(self) -> None:
        assert self.result.rendering_provider_npi == "1306849450"

    def test_taxonomy_retained(self) -> None:
        assert (
            self.result.billing_provider_taxonomy == "207Q00000X"
        )

    def test_payer_id_retained(self) -> None:
        assert self.result.payer_id == "BCBS001"

    def test_payer_name_retained(self) -> None:
        assert self.result.payer_name == "Blue Cross Blue Shield"

    def test_gender_retained(self) -> None:
        assert self.result.patient_gender == "F"

    def test_claim_type_retained(self) -> None:
        assert self.result.claim_type == "professional"

    def test_place_of_service_retained(self) -> None:
        assert self.result.place_of_service == "11"

    def test_total_charge_retained(self) -> None:
        assert self.result.total_charge == 300.00

    def test_diagnosis_codes_retained(self) -> None:
        assert len(self.result.diagnosis_codes) == 2
        assert self.result.diagnosis_codes[0]["code"] == "J06.9"
        assert self.result.diagnosis_codes[1]["code"] == "R05.9"


# --- Line de-identification tests ---


class TestLineDeidentification:
    """Test claim line de-identification."""

    def setup_method(self) -> None:
        self.claim = ClaimData(**_full_phi_claim_dict())
        self.result = ClaimDeidentifier.deidentify(self.claim)

    def test_lines_count_preserved(self) -> None:
        assert len(self.result.lines) == 2

    def test_line_is_deidentified_type(self) -> None:
        assert isinstance(
            self.result.lines[0], DeidentifiedLineData
        )

    def test_procedure_code_retained(self) -> None:
        assert self.result.lines[0].procedure_code == "99213"
        assert self.result.lines[1].procedure_code == "20610"

    def test_modifiers_retained(self) -> None:
        assert self.result.lines[0].modifiers == ["25"]

    def test_diagnosis_pointers_retained(self) -> None:
        assert self.result.lines[0].diagnosis_pointers == [1]
        assert self.result.lines[1].diagnosis_pointers == [1, 2]

    def test_charge_amount_retained(self) -> None:
        assert self.result.lines[0].charge_amount == 150.00

    def test_units_retained(self) -> None:
        assert self.result.lines[0].units == 1.0

    def test_line_rendering_npi_retained(self) -> None:
        assert (
            self.result.lines[0].rendering_provider_npi
            == "1306849450"
        )

    def test_service_year_extracted(self) -> None:
        assert self.result.lines[0].service_year == 2026
        assert self.result.lines[1].service_year == 2026

    def test_no_full_dates_in_lines(self) -> None:
        for line in self.result.lines:
            line_str = str(line.model_dump())
            assert "2026-01-15" not in line_str
            assert "2026-01-20" not in line_str

    def test_line_place_of_service_retained(self) -> None:
        assert self.result.lines[0].place_of_service == "11"


# --- Edge case tests ---


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_claim(self) -> None:
        claim = ClaimData()
        result = ClaimDeidentifier.deidentify(claim)
        assert isinstance(result, DeidentifiedClaim)
        assert result.patient_age is None
        assert result.lines == []

    def test_none_fields(self) -> None:
        claim = ClaimData(
            patient_first_name=None,
            patient_dob=None,
            subscriber_id=None,
        )
        result = ClaimDeidentifier.deidentify(claim)
        assert result.patient_age is None

    def test_line_with_no_service_date(self) -> None:
        claim = ClaimData(
            lines=[
                {
                    "procedure_code": "99213",
                    "charge_amount": 150.00,
                },
            ],
        )
        result = ClaimDeidentifier.deidentify(claim)
        assert result.lines[0].service_year is None

    def test_patient_relationship_stripped(self) -> None:
        claim = ClaimData(patient_relationship="spouse")
        result = ClaimDeidentifier.deidentify(claim)
        assert not hasattr(result, "patient_relationship")


# --- Import tests ---


class TestImports:
    """Test module imports work correctly."""

    def test_import_from_models(self) -> None:
        from claim_validator.models import DeidentifiedClaim
        assert DeidentifiedClaim is not None

    def test_import_from_top_level(self) -> None:
        from claim_validator import ClaimDeidentifier
        assert ClaimDeidentifier is not None

    def test_import_from_top_level_model(self) -> None:
        from claim_validator import DeidentifiedClaim
        assert DeidentifiedClaim is not None
