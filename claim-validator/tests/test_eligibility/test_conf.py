"""Tests for eligibility settings extension — AC 7."""

from __future__ import annotations

import pytest

from claim_validator.conf import ClaimValidatorSettings


class TestEligibilitySettings:
    """AC 7: new eligibility fields with sensible defaults."""

    def test_stedi_api_key_default_none(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.stedi_api_key is None

    def test_stedi_environment_default_sandbox(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.stedi_environment == "sandbox"

    def test_eligibility_rule_validators_default_empty(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.eligibility_rule_validators == []

    def test_eligibility_ai_validators_default_empty(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.eligibility_ai_validators == []

    def test_skip_clearinghouse_on_eligibility_failure_default_true(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.skip_clearinghouse_on_eligibility_failure is True

    def test_eligibility_skip_ai_default_false(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.eligibility_skip_ai is False

    def test_env_prefix(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """All eligibility settings use CLAIM_VALIDATOR_ prefix."""
        monkeypatch.setenv("CLAIM_VALIDATOR_STEDI_API_KEY", "test-key-123")
        monkeypatch.setenv("CLAIM_VALIDATOR_STEDI_ENVIRONMENT", "production")
        settings = ClaimValidatorSettings()
        assert settings.stedi_api_key == "test-key-123"
        assert settings.stedi_environment == "production"

    def test_existing_pa_settings_unchanged(self) -> None:
        """PA settings still work after eligibility extension."""
        settings = ClaimValidatorSettings()
        assert settings.skip_clearinghouse_on_pa_failure is True
        assert settings.pa_skip_ai is False
        assert len(settings.pa_rule_validators) == 7
