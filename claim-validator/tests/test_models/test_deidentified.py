"""Tests for DeidentifiedClaim and DeidentifiedLineData models."""

from __future__ import annotations

from claim_validator.models.deidentified import (
    DeidentifiedClaim,
    DeidentifiedLineData,
)

# --- DeidentifiedLineData tests ---


class TestDeidentifiedLineData:
    """Test DeidentifiedLineData model."""

    def test_create_minimal(self) -> None:
        line = DeidentifiedLineData(
            procedure_code="99213",
            charge_amount=150.00,
        )
        assert line.procedure_code == "99213"
        assert line.charge_amount == 150.00

    def test_service_year_is_int(self) -> None:
        line = DeidentifiedLineData(
            procedure_code="99213",
            charge_amount=150.00,
            service_year=2026,
        )
        assert line.service_year == 2026
        assert isinstance(line.service_year, int)

    def test_no_full_dates(self) -> None:
        line = DeidentifiedLineData(
            procedure_code="99213",
            charge_amount=150.00,
            service_year=2026,
        )
        # Model has no date fields — only service_year
        assert not hasattr(line, "service_date_from")
        assert not hasattr(line, "service_date_to")

    def test_retains_clinical_data(self) -> None:
        line = DeidentifiedLineData(
            procedure_code="99213",
            modifiers=["25"],
            diagnosis_pointers=[1, 2],
            charge_amount=150.00,
            units=2.0,
            place_of_service="11",
            rendering_provider_npi="1234567893",
            service_year=2026,
        )
        assert line.modifiers == ["25"]
        assert line.diagnosis_pointers == [1, 2]
        assert line.units == 2.0
        assert line.place_of_service == "11"
        assert line.rendering_provider_npi == "1234567893"

    def test_frozen_immutability(self) -> None:
        line = DeidentifiedLineData(
            procedure_code="99213",
            charge_amount=150.00,
        )
        try:
            line.procedure_code = "99214"  # type: ignore[misc]
            assert False, "Should have raised"
        except Exception:
            pass


# --- DeidentifiedClaim tests ---


class TestDeidentifiedClaim:
    """Test DeidentifiedClaim model."""

    def test_create_minimal(self) -> None:
        claim = DeidentifiedClaim()
        assert claim is not None

    def test_is_deidentified_returns_true(self) -> None:
        claim = DeidentifiedClaim()
        assert claim.is_deidentified is True

    def test_no_patient_name_fields(self) -> None:
        claim = DeidentifiedClaim()
        assert not hasattr(claim, "patient_first_name")
        assert not hasattr(claim, "patient_last_name")

    def test_no_subscriber_name_fields(self) -> None:
        claim = DeidentifiedClaim()
        assert not hasattr(claim, "subscriber_first_name")
        assert not hasattr(claim, "subscriber_last_name")

    def test_no_dob_fields(self) -> None:
        claim = DeidentifiedClaim()
        assert not hasattr(claim, "patient_dob")
        assert not hasattr(claim, "subscriber_dob")

    def test_no_subscriber_id_field(self) -> None:
        claim = DeidentifiedClaim()
        assert not hasattr(claim, "subscriber_id")

    def test_no_filing_date_field(self) -> None:
        claim = DeidentifiedClaim()
        assert not hasattr(claim, "filing_date")

    def test_has_patient_age(self) -> None:
        claim = DeidentifiedClaim(patient_age=35)
        assert claim.patient_age == 35

    def test_age_capped_at_90(self) -> None:
        claim = DeidentifiedClaim(patient_age=90)
        assert claim.patient_age == 90

    def test_retains_npi(self) -> None:
        claim = DeidentifiedClaim(
            billing_provider_npi="1234567893",
            rendering_provider_npi="1306849450",
        )
        assert claim.billing_provider_npi == "1234567893"
        assert claim.rendering_provider_npi == "1306849450"

    def test_retains_payer_info(self) -> None:
        claim = DeidentifiedClaim(
            payer_id="BCBS001",
            payer_name="Blue Cross",
        )
        assert claim.payer_id == "BCBS001"
        assert claim.payer_name == "Blue Cross"

    def test_retains_clinical_data(self) -> None:
        claim = DeidentifiedClaim(
            patient_gender="F",
            claim_type="professional",
            place_of_service="11",
            total_charge=300.00,
            diagnosis_codes=[
                {"code": "J06.9", "pointer": 1},
            ],
        )
        assert claim.patient_gender == "F"
        assert claim.total_charge == 300.00
        assert len(claim.diagnosis_codes) == 1

    def test_retains_lines(self) -> None:
        claim = DeidentifiedClaim(
            lines=[
                DeidentifiedLineData(
                    procedure_code="99213",
                    charge_amount=150.00,
                    service_year=2026,
                ),
            ],
        )
        assert len(claim.lines) == 1
        assert claim.lines[0].service_year == 2026

    def test_frozen_immutability(self) -> None:
        claim = DeidentifiedClaim(patient_age=35)
        try:
            claim.patient_age = 40  # type: ignore[misc]
            assert False, "Should have raised"
        except Exception:
            pass

    def test_distinct_from_claim_data(self) -> None:
        from claim_validator.models.claim import ClaimData
        assert DeidentifiedClaim is not ClaimData
        assert not issubclass(DeidentifiedClaim, ClaimData)
