"""Tests for ClaimData, ClaimLineData, DiagnosisCode models."""

from __future__ import annotations

from typing import Any

import pydantic
import pytest

from claim_validator import ClaimData, ClaimLineData, DiagnosisCode


class TestDiagnosisCode:
    def test_create_with_required_fields(self) -> None:
        dx = DiagnosisCode(code="J06.9", pointer=1)
        assert dx.code == "J06.9"
        assert dx.pointer == 1
        assert dx.type == "principal"

    def test_create_from_dict(self) -> None:
        dx = DiagnosisCode.model_validate({"code": "E11.9", "pointer": 2, "type": "other"})
        assert dx.code == "E11.9"
        assert dx.pointer == 2
        assert dx.type == "other"

    def test_frozen_raises_on_modification(self) -> None:
        dx = DiagnosisCode(code="J06.9", pointer=1)
        with pytest.raises(pydantic.ValidationError):
            dx.code = "Z00.00"  # type: ignore[misc]

    def test_string_coercion_for_pointer(self) -> None:
        """strict=False allows string-to-int coercion."""
        dx = DiagnosisCode(code="J06.9", pointer="1")  # type: ignore[arg-type]
        assert dx.pointer == 1


class TestClaimLineData:
    def test_create_with_required_fields(self) -> None:
        line = ClaimLineData(
            procedure_code="99213",
            charge_amount=150.00,
        )
        assert line.procedure_code == "99213"
        assert line.charge_amount == 150.00
        assert line.modifiers == []
        assert line.diagnosis_pointers == []
        assert line.units == 1.0

    def test_create_from_dict(self) -> None:
        line = ClaimLineData.model_validate(
            {
                "procedure_code": "99213",
                "modifiers": ["25"],
                "diagnosis_pointers": [1, 2],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
                "place_of_service": "11",
            }
        )
        assert line.procedure_code == "99213"
        assert line.modifiers == ["25"]
        assert line.diagnosis_pointers == [1, 2]
        assert line.service_date_from == "2026-01-15"

    def test_string_to_float_coercion(self) -> None:
        """strict=False allows '150.00' -> 150.0."""
        line = ClaimLineData(
            procedure_code="99213",
            charge_amount="150.00",  # type: ignore[arg-type]
        )
        assert line.charge_amount == 150.0
        assert isinstance(line.charge_amount, float)

    def test_frozen_raises_on_modification(self) -> None:
        line = ClaimLineData(procedure_code="99213", charge_amount=150.00)
        with pytest.raises(pydantic.ValidationError):
            line.procedure_code = "99214"  # type: ignore[misc]

    def test_optional_fields_default_none(self) -> None:
        line = ClaimLineData(procedure_code="99213", charge_amount=100.0)
        assert line.service_date_from is None
        assert line.service_date_to is None
        assert line.place_of_service is None
        assert line.rendering_provider_npi is None


class TestClaimData:
    def test_create_from_dict(self, valid_claim_dict: dict[str, Any]) -> None:
        claim = ClaimData.model_validate(valid_claim_dict)
        assert claim.billing_provider_npi == "1234567893"
        assert claim.subscriber_id == "XYZ123456"
        assert len(claim.diagnosis_codes) == 1
        assert len(claim.lines) == 1

    def test_create_with_kwargs(self) -> None:
        claim = ClaimData(
            billing_provider_npi="1234567893",
            subscriber_id="XYZ123456",
            diagnosis_codes=[DiagnosisCode(code="J06.9", pointer=1)],
            lines=[ClaimLineData(procedure_code="99213", charge_amount=150.0)],
        )
        assert claim.billing_provider_npi == "1234567893"

    def test_nested_models_are_typed(self, valid_claim_dict: dict[str, Any]) -> None:
        claim = ClaimData.model_validate(valid_claim_dict)
        assert isinstance(claim.diagnosis_codes[0], DiagnosisCode)
        assert isinstance(claim.lines[0], ClaimLineData)
        assert claim.diagnosis_codes[0].code == "J06.9"
        assert claim.lines[0].procedure_code == "99213"

    def test_frozen_raises_on_modification(self, valid_claim_dict: dict[str, Any]) -> None:
        claim = ClaimData.model_validate(valid_claim_dict)
        with pytest.raises(pydantic.ValidationError):
            claim.billing_provider_npi = "9999999999"  # type: ignore[misc]

    def test_default_claim_type(self) -> None:
        claim = ClaimData()
        assert claim.claim_type == "professional"

    def test_optional_fields_default_none(self) -> None:
        claim = ClaimData()
        assert claim.billing_provider_npi is None
        assert claim.subscriber_id is None
        assert claim.patient_dob is None
        assert claim.payer_id is None
        assert claim.total_charge is None

    def test_empty_claim_is_valid(self) -> None:
        """ClaimData allows partial claims — validators check completeness."""
        claim = ClaimData()
        assert claim.diagnosis_codes == []
        assert claim.lines == []

    def test_total_charge_string_coercion(self) -> None:
        claim = ClaimData(total_charge="500.00")  # type: ignore[arg-type]
        assert claim.total_charge == 500.0

    def test_multiple_lines(self) -> None:
        claim = ClaimData(
            lines=[
                ClaimLineData(procedure_code="99213", charge_amount=150.0),
                ClaimLineData(procedure_code="20610", charge_amount=200.0),
            ],
        )
        assert len(claim.lines) == 2
        assert claim.lines[0].procedure_code == "99213"
        assert claim.lines[1].procedure_code == "20610"

    def test_multiple_diagnosis_codes(self) -> None:
        claim = ClaimData(
            diagnosis_codes=[
                DiagnosisCode(code="J06.9", pointer=1),
                DiagnosisCode(code="E11.9", pointer=2, type="other"),
            ],
        )
        assert len(claim.diagnosis_codes) == 2
        assert claim.diagnosis_codes[1].type == "other"
