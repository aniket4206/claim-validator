"""Tests for validate() function with ai_config parameter."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from claim_validator._api import validate
from claim_validator.conf import ClaimValidatorSettings
from claim_validator.models.results import PipelineResult


def _claim_dict() -> dict:
    """Minimal claim dict for testing."""
    return {
        "billing_provider_npi": "1234567893",
        "patient_first_name": "Test",
        "patient_last_name": "Patient",
        "patient_dob": "1980-01-01",
        "patient_gender": "M",
        "subscriber_id": "SUB123",
        "payer_id": "BCBS01",
        "payer_name": "BCBS",
        "total_charge": 150.0,
        "lines": [],
        "diagnosis_codes": [],
    }


class TestValidateWithAIConfig:
    """Test validate() with ai_config parameter."""

    @patch(
        "claim_validator._api.ValidationPipeline.from_settings",
    )
    def test_ai_config_creates_settings(
        self, mock_from_settings: MagicMock,
    ) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = PipelineResult()
        mock_from_settings.return_value = mock_pipeline

        ai_config = {
            "provider": "anthropic",
            "api_key": "sk-test",
            "model": "claude-sonnet-4-5-20241022",
        }
        validate(_claim_dict(), ai_config=ai_config)

        call_args = mock_from_settings.call_args
        settings = call_args[0][0]
        assert isinstance(settings, ClaimValidatorSettings)
        assert settings.ai_config == ai_config

    @patch(
        "claim_validator._api.ValidationPipeline.from_settings",
    )
    def test_no_ai_config_uses_defaults(
        self, mock_from_settings: MagicMock,
    ) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = PipelineResult()
        mock_from_settings.return_value = mock_pipeline

        validate(_claim_dict())

        call_args = mock_from_settings.call_args
        settings = call_args[0][0]
        assert settings is None

    @patch(
        "claim_validator._api.ValidationPipeline.from_settings",
    )
    def test_ai_config_with_settings_merges(
        self, mock_from_settings: MagicMock,
    ) -> None:
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = PipelineResult()
        mock_from_settings.return_value = mock_pipeline

        original_settings = ClaimValidatorSettings(
            rule_validators=[],
            skip_ai_on_rule_failure=False,
        )
        ai_config = {
            "provider": "openai",
            "api_key": "sk-test",
            "model": "gpt-4o",
        }
        validate(
            _claim_dict(),
            settings=original_settings,
            ai_config=ai_config,
        )

        call_args = mock_from_settings.call_args
        settings = call_args[0][0]
        assert settings.ai_config == ai_config
        assert settings.skip_ai_on_rule_failure is False
        assert settings.rule_validators == []

    @patch(
        "claim_validator._api.ValidationPipeline.from_settings",
    )
    def test_returns_pipeline_result(
        self, mock_from_settings: MagicMock,
    ) -> None:
        expected = PipelineResult()
        mock_pipeline = MagicMock()
        mock_pipeline.run.return_value = expected
        mock_from_settings.return_value = mock_pipeline

        result = validate(_claim_dict(), ai_config={
            "provider": "anthropic",
            "api_key": "sk-test",
            "model": "m",
        })
        assert result is expected

    def test_without_ai_config_runs_rule_only(self) -> None:
        """Regression: validate() without ai_config still works."""
        result = validate(_claim_dict())
        assert isinstance(result, PipelineResult)
