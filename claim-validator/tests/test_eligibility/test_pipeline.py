"""Tests for EligibilityPipeline and check_eligibility() API."""

from __future__ import annotations

import datetime
import time
from typing import Any
from unittest.mock import MagicMock

import pytest

from claim_validator.conf import ClaimValidatorSettings
from claim_validator.constants import Severity
from claim_validator.eligibility._api import check_eligibility
from claim_validator.eligibility.models.request import EligibilityRequest
from claim_validator.eligibility.models.result import EligibilityResult
from claim_validator.eligibility.pipeline import EligibilityPipeline
from claim_validator.validators.base import BaseValidator

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def fully_valid_dict() -> dict[str, Any]:
    """Fully valid eligibility request dict — zero findings expected."""
    return {
        "provider_npi": "1234567893",
        "payer_id": "60054",
        "subscriber_id": "XYZ123456",
        "subscriber_first_name": "Jane",
        "subscriber_last_name": "Doe",
        "subscriber_dob": "1985-03-15",
        "date_of_service": datetime.date.today(),
        "service_type_code": "30",
    }


@pytest.fixture
def fully_valid_request(fully_valid_dict: dict[str, Any]) -> EligibilityRequest:
    """Fully valid EligibilityRequest model — zero findings expected."""
    return EligibilityRequest(**fully_valid_dict)


@pytest.fixture
def invalid_request_dict() -> dict[str, Any]:
    """Request dict with multiple validation issues."""
    return {
        "provider_npi": "1234567890",  # invalid Luhn
        "payer_id": "NONEXISTENT_PAYER",
        "subscriber_id": "---",  # no alphanumeric chars
        "subscriber_first_name": "",
        "subscriber_last_name": "",
        "subscriber_dob": "1985-03-15",
        "date_of_service": None,
        "service_type_code": "ZZZZ",
    }


# ---------------------------------------------------------------------------
# Task 5.1: Valid request → passed=True, zero findings, eligible=None
# ---------------------------------------------------------------------------

class TestValidRequest:
    def test_check_eligibility_valid_dict(
        self, fully_valid_dict: dict[str, Any],
    ) -> None:
        result = check_eligibility(fully_valid_dict)
        assert isinstance(result, EligibilityResult)
        assert result.passed is True
        assert result.findings == []
        assert result.eligible is None

    def test_check_eligibility_valid_model(
        self, fully_valid_request: EligibilityRequest,
    ) -> None:
        result = check_eligibility(fully_valid_request)
        assert isinstance(result, EligibilityResult)
        assert result.passed is True
        assert result.findings == []
        assert result.eligible is None

    def test_zero_config_required(
        self, fully_valid_dict: dict[str, Any],
    ) -> None:
        """AC #1: zero configuration, zero API keys, zero network calls."""
        result = check_eligibility(fully_valid_dict)
        assert result.passed is True


# ---------------------------------------------------------------------------
# Task 5.2 & 5.3: Dict and Pydantic model input accepted
# ---------------------------------------------------------------------------

class TestInputTypes:
    def test_dict_input(self, fully_valid_dict: dict[str, Any]) -> None:
        result = check_eligibility(fully_valid_dict)
        assert isinstance(result, EligibilityResult)

    def test_model_input(
        self, fully_valid_request: EligibilityRequest,
    ) -> None:
        result = check_eligibility(fully_valid_request)
        assert isinstance(result, EligibilityResult)

    def test_invalid_input_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="request must be a dict"):
            check_eligibility("not a dict or model")  # type: ignore[arg-type]

    def test_invalid_input_list_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="request must be a dict"):
            check_eligibility([1, 2, 3])  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Task 5.5: Multiple validation errors — all 6 validators run
# ---------------------------------------------------------------------------

class TestAllValidatorsRun:
    def test_multiple_findings_aggregated(
        self, invalid_request_dict: dict[str, Any],
    ) -> None:
        result = check_eligibility(invalid_request_dict)
        assert result.passed is False
        assert len(result.findings) > 0

        codes = {f.code for f in result.findings}
        # NPI validator
        assert any("NPI" in c for c in codes), f"NPI finding missing: {codes}"
        # Payer ID validator
        assert any("PAYER" in c for c in codes), f"Payer finding missing: {codes}"
        # Demographics validator (emits ELIG_MISSING_FIELD)
        assert any(
            "MISSING_FIELD" in c for c in codes
        ), f"Demographics finding missing: {codes}"
        # Service type validator
        assert any(
            "SERVICE_TYPE" in c for c in codes
        ), f"Service type finding missing: {codes}"
        # Date validator
        assert any(
            "DATE" in c for c in codes
        ), f"Date finding missing: {codes}"
        # Member ID validator
        assert any(
            "MEMBER_ID" in c for c in codes
        ), f"Member ID finding missing: {codes}"

    def test_findings_from_all_six_validators(
        self, invalid_request_dict: dict[str, Any],
    ) -> None:
        """AC #2: all 6 rule-based validators run."""
        result = check_eligibility(invalid_request_dict)
        # At least 6 findings (one per validator minimum)
        assert len(result.findings) >= 6

    def test_findings_ordered_by_severity(
        self, invalid_request_dict: dict[str, Any],
    ) -> None:
        """AC #2: findings ordered by severity (ERROR before WARNING)."""
        result = check_eligibility(invalid_request_dict)
        severities = [f.severity for f in result.findings]
        error_indices = [
            i for i, s in enumerate(severities) if s == Severity.ERROR
        ]
        warning_indices = [
            i for i, s in enumerate(severities) if s == Severity.WARNING
        ]
        if error_indices and warning_indices:
            assert max(error_indices) < min(warning_indices), (
                "ERROR findings must come before WARNING findings"
            )


# ---------------------------------------------------------------------------
# Task 5.6 & 5.7: Custom settings
# ---------------------------------------------------------------------------

class TestCustomSettings:
    def test_subset_of_validators(
        self, fully_valid_dict: dict[str, Any],
    ) -> None:
        """AC #5: only configured validators execute."""
        settings = ClaimValidatorSettings(
            eligibility_rule_validators=[
                "claim_validator.eligibility.validators.rule_based.npi.EligibilityNPIValidator",
            ],
        )
        result = check_eligibility(fully_valid_dict, settings=settings)
        assert isinstance(result, EligibilityResult)
        assert result.passed is True

    def test_empty_validators_list(
        self, fully_valid_dict: dict[str, Any],
    ) -> None:
        settings = ClaimValidatorSettings(
            eligibility_rule_validators=[],
        )
        result = check_eligibility(fully_valid_dict, settings=settings)
        assert result.passed is True
        assert result.findings == []

    def test_custom_settings_fewer_findings(
        self, invalid_request_dict: dict[str, Any],
    ) -> None:
        """With only NPI validator, only NPI findings should appear."""
        settings = ClaimValidatorSettings(
            eligibility_rule_validators=[
                "claim_validator.eligibility.validators.rule_based.npi.EligibilityNPIValidator",
            ],
        )
        result = check_eligibility(
            invalid_request_dict, settings=settings,
        )
        codes = {f.code for f in result.findings}
        assert all("NPI" in c for c in codes)


# ---------------------------------------------------------------------------
# Task 5.8: execution_time > 0
# ---------------------------------------------------------------------------

class TestExecutionTime:
    def test_execution_time_positive(
        self, fully_valid_dict: dict[str, Any],
    ) -> None:
        result = check_eligibility(fully_valid_dict)
        assert result.execution_time > 0

    def test_performance_under_100ms(
        self, fully_valid_dict: dict[str, Any],
    ) -> None:
        """AC #7: completes in under 100ms."""
        start = time.perf_counter()
        result = check_eligibility(fully_valid_dict)
        elapsed = time.perf_counter() - start
        assert elapsed < 0.1, f"Took {elapsed:.4f}s, expected < 0.1s"
        assert result.execution_time < 0.1


# ---------------------------------------------------------------------------
# Task 5.10: Validator exception → VALIDATOR_ERROR finding
# ---------------------------------------------------------------------------

class TestValidatorException:
    def test_validator_error_on_exception(
        self, fully_valid_request: EligibilityRequest,
    ) -> None:
        """AC #8 edge case: broken validator doesn't crash pipeline."""
        broken = MagicMock(spec=BaseValidator)
        broken.validate.side_effect = RuntimeError("boom")

        pipeline = EligibilityPipeline(rule_validators=[broken])
        result = pipeline.run(fully_valid_request)

        assert result.passed is False
        assert len(result.findings) == 1
        assert result.findings[0].code == "VALIDATOR_ERROR"
        assert result.findings[0].severity == Severity.ERROR
        assert "boom" in result.findings[0].context["error"]
        assert result.findings[0].context["validator"] == "MagicMock"


# ---------------------------------------------------------------------------
# Task 5.11 & 5.12: Import tests
# ---------------------------------------------------------------------------

class TestImports:
    def test_top_level_check_eligibility_import(self) -> None:
        """AC #6: from claim_validator import check_eligibility."""
        from claim_validator import check_eligibility as ce
        assert callable(ce)

    def test_top_level_eligibility_pipeline_import(self) -> None:
        from claim_validator import EligibilityPipeline
        assert EligibilityPipeline is not None

    def test_eligibility_module_check_eligibility(self) -> None:
        from claim_validator.eligibility import check_eligibility as ce
        assert callable(ce)

    def test_eligibility_module_pipeline(self) -> None:
        from claim_validator.eligibility import EligibilityPipeline
        assert EligibilityPipeline is not None

    def test_top_level_models_importable(self) -> None:
        """AC #6: EligibilityRequest/Response/Result importable."""
        from claim_validator import (
            EligibilityRequest,
            EligibilityResponse,
            EligibilityResult,
        )
        assert EligibilityRequest is not None
        assert EligibilityResponse is not None
        assert EligibilityResult is not None


# ---------------------------------------------------------------------------
# Pipeline direct usage
# ---------------------------------------------------------------------------

class TestPipelineDirect:
    def test_from_settings_default(self) -> None:
        pipeline = EligibilityPipeline.from_settings()
        assert len(pipeline._rule_validators) == 6

    def test_from_settings_custom(self) -> None:
        settings = ClaimValidatorSettings(
            eligibility_rule_validators=[
                "claim_validator.eligibility.validators.rule_based.npi.EligibilityNPIValidator",
            ],
        )
        pipeline = EligibilityPipeline.from_settings(settings)
        assert len(pipeline._rule_validators) == 1

    def test_from_settings_empty(self) -> None:
        settings = ClaimValidatorSettings(
            eligibility_rule_validators=[],
        )
        pipeline = EligibilityPipeline.from_settings(settings)
        assert len(pipeline._rule_validators) == 0
