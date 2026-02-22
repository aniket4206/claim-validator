"""Tests for top-level validate() convenience function."""

from __future__ import annotations

import pytest
from pydantic import ValidationError as PydanticValidationError

from claim_validator._api import validate
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import PipelineResult


def _valid_claim_dict() -> dict:
    """Minimal claim dict that passes all validators."""
    return {
        "billing_provider_npi": "1234567893",
        "subscriber_id": "XYZ123456",
        "patient_first_name": "Jane",
        "patient_last_name": "Doe",
        "patient_dob": "1990-01-15",
        "patient_gender": "F",
        "payer_id": "BCBS001",
        "diagnosis_codes": [{"code": "J06.9", "pointer": 1}],
        "lines": [
            {
                "procedure_code": "99213",
                "diagnosis_pointers": [1],
                "charge_amount": 150.00,
                "service_date_from": "2026-01-15",
            },
        ],
    }


def _invalid_claim_dict() -> dict:
    """Claim dict with multiple validation issues."""
    return {
        "billing_provider_npi": "0000000000",
        "subscriber_id": "",
        "patient_first_name": "",
        "patient_last_name": "",
        "patient_dob": "",
        "patient_gender": "",
        "payer_id": "",
        "diagnosis_codes": [],
        "lines": [],
    }


# --- validate() with dict input ---


class TestValidateDict:
    """Test validate() with dict input."""

    def test_valid_dict_returns_pipeline_result(self) -> None:
        result = validate(_valid_claim_dict())
        assert isinstance(result, PipelineResult)

    def test_valid_dict_passed_true(self) -> None:
        result = validate(_valid_claim_dict())
        assert result.passed is True

    def test_invalid_dict_has_findings(self) -> None:
        result = validate(_invalid_claim_dict())
        assert len(result.findings) > 0

    def test_invalid_dict_passed_false(self) -> None:
        result = validate(_invalid_claim_dict())
        assert result.passed is False

    def test_malformed_dict_raises_validation_error(self) -> None:
        with pytest.raises(PydanticValidationError):
            validate({"lines": "not-a-list"})


# --- validate() with ClaimData input ---


class TestValidateClaimData:
    """Test validate() with ClaimData model input."""

    def test_claim_data_returns_pipeline_result(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = validate(claim)
        assert isinstance(result, PipelineResult)

    def test_claim_data_passed_true(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result = validate(claim)
        assert result.passed is True

    def test_claim_data_same_as_dict(self) -> None:
        claim = ClaimData(**_valid_claim_dict())
        result_model = validate(claim)
        result_dict = validate(_valid_claim_dict())
        assert result_model.passed == result_dict.passed
        assert len(result_model.findings) == len(result_dict.findings)


# --- validate() with custom settings ---


class TestValidateCustomSettings:
    """Test validate() with custom ClaimValidatorSettings."""

    def test_custom_settings_single_validator(self) -> None:
        settings = ClaimValidatorSettings(
            rule_validators=[
                "claim_validator.validators.rule_based.npi.NPIValidator",
            ],
        )
        result = validate(_valid_claim_dict(), settings=settings)
        assert result.passed is True
        rule_phase = result.phase_results[0]
        assert len(rule_phase.validator_outputs) == 1

    def test_custom_settings_empty_validators(self) -> None:
        settings = ClaimValidatorSettings(rule_validators=[])
        result = validate(_valid_claim_dict(), settings=settings)
        assert result.passed is True
        assert result.findings == []


# --- validate() default validators ---


class TestValidateDefaultValidators:
    """Test validate() uses all 8 default validators."""

    def test_default_runs_8_validators(self) -> None:
        result = validate(_valid_claim_dict())
        rule_phase = result.phase_results[0]
        assert len(rule_phase.validator_outputs) == 8

    def test_all_8_validators_run_on_bad_claim(self) -> None:
        result = validate(_invalid_claim_dict())
        rule_phase = result.phase_results[0]
        assert len(rule_phase.validator_outputs) == 8
        validators_with_findings = [
            o.validator_name
            for o in rule_phase.validator_outputs
            if o.findings
        ]
        assert len(validators_with_findings) >= 2


# --- validate() top-level import ---


class TestValidateImport:
    """Test validate is importable from top-level package."""

    def test_import_from_claim_validator(self) -> None:
        from claim_validator import validate as v
        assert callable(v)

    def test_import_pipeline_from_claim_validator(self) -> None:
        from claim_validator import ValidationPipeline
        assert ValidationPipeline is not None


# --- No PHI in findings ---


class TestNoPHIInFindings:
    """Test that findings do not contain PHI."""

    def test_no_patient_names_in_findings(self) -> None:
        d = _valid_claim_dict()
        d["billing_provider_npi"] = "0000000000"
        result = validate(d)
        for finding in result.findings:
            assert "Jane" not in finding.message
            assert "Doe" not in finding.message

    def test_no_dob_in_findings(self) -> None:
        d = _valid_claim_dict()
        d["billing_provider_npi"] = "0000000000"
        result = validate(d)
        for finding in result.findings:
            assert "1990-01-15" not in finding.message

    def test_no_subscriber_id_in_findings(self) -> None:
        d = _valid_claim_dict()
        d["billing_provider_npi"] = "0000000000"
        result = validate(d)
        for finding in result.findings:
            assert "XYZ123456" not in finding.message
