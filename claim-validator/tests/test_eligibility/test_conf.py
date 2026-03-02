"""Tests for eligibility settings extension."""

from __future__ import annotations

from claim_validator.conf import ClaimValidatorSettings


class TestEligibilitySettings:
    """Eligibility settings with sensible defaults."""

    def test_eligibility_rule_validators_default_six(self) -> None:
        settings = ClaimValidatorSettings()
        assert len(settings.eligibility_rule_validators) == 6

    def test_eligibility_ai_validators_default_one(self) -> None:
        settings = ClaimValidatorSettings()
        assert len(settings.eligibility_ai_validators) == 1
        assert "EligibilityInterpreterAI" in settings.eligibility_ai_validators[0]

    def test_eligibility_skip_ai_default_false(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.eligibility_skip_ai is False

    def test_existing_pa_settings_unchanged(self) -> None:
        """PA settings still work after eligibility extension."""
        settings = ClaimValidatorSettings()
        assert settings.pa_skip_ai is False
        assert len(settings.pa_rule_validators) == 7
