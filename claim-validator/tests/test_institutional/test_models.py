"""Tests for institutional claim data models."""

from __future__ import annotations

import pydantic
import pytest

from claim_validator.constants import ClaimType
from claim_validator.models.institutional import (
    InstitutionalClaimData,
    InstitutionalServiceLine,
    OccurrenceCode,
    ValueCode,
)


class TestClaimType:
    def test_professional_value(self) -> None:
        assert ClaimType.PROFESSIONAL == "professional"

    def test_institutional_value(self) -> None:
        assert ClaimType.INSTITUTIONAL == "institutional"

    def test_dental_value(self) -> None:
        assert ClaimType.DENTAL == "dental"


class TestOccurrenceCode:
    def test_create(self) -> None:
        oc = OccurrenceCode(code="01", date="2026-01-15")
        assert oc.code == "01"
        assert oc.date == "2026-01-15"

    def test_frozen(self) -> None:
        oc = OccurrenceCode(code="01")
        with pytest.raises(pydantic.ValidationError):
            oc.code = "02"  # type: ignore[misc]


class TestValueCode:
    def test_create(self) -> None:
        vc = ValueCode(code="01", amount=1500.00)
        assert vc.code == "01"
        assert vc.amount == 1500.00

    def test_frozen(self) -> None:
        vc = ValueCode(code="01", amount=100.0)
        with pytest.raises(pydantic.ValidationError):
            vc.amount = 200.0  # type: ignore[misc]


class TestInstitutionalServiceLine:
    def test_create(self) -> None:
        sl = InstitutionalServiceLine(
            revenue_code="0120",
            hcpcs_code="99213",
            rate=250.00,
            units=1.0,
        )
        assert sl.revenue_code == "0120"
        assert sl.hcpcs_code == "99213"

    def test_defaults(self) -> None:
        sl = InstitutionalServiceLine(revenue_code="0120")
        assert sl.modifiers == []
        assert sl.units == 1.0
        assert sl.hcpcs_code is None


class TestInstitutionalClaimData:
    def test_create_minimal(self) -> None:
        claim = InstitutionalClaimData(
            billing_provider_npi="1234567893",
            bill_type_code="111",
        )
        assert claim.claim_type == "institutional"
        assert claim.bill_type_code == "111"

    def test_frozen(self) -> None:
        claim = InstitutionalClaimData()
        with pytest.raises(pydantic.ValidationError):
            claim.bill_type_code = "222"  # type: ignore[misc]

    def test_full_construction(self) -> None:
        claim = InstitutionalClaimData(
            billing_provider_npi="1234567893",
            attending_physician_npi="9876543210",
            bill_type_code="131",
            admission_date="2026-01-10",
            discharge_date="2026-01-15",
            admission_type_code="1",
            admission_source_code="7",
            patient_status_code="01",
            drg_code="470",
            condition_codes=["01", "02"],
            occurrence_codes=[OccurrenceCode(code="01", date="2026-01-10")],
            value_codes=[ValueCode(code="01", amount=5000.00)],
            service_lines=[
                InstitutionalServiceLine(revenue_code="0120", rate=500.00),
                InstitutionalServiceLine(revenue_code="0250", hcpcs_code="J1234", rate=150.00),
            ],
            subscriber_id="MEM123",
            payer_id="60054",
            total_charge_amount=5650.00,
        )
        assert len(claim.service_lines) == 2
        assert len(claim.condition_codes) == 2
        assert claim.drg_code == "470"

    def test_default_claim_type(self) -> None:
        claim = InstitutionalClaimData()
        assert claim.claim_type == "institutional"
