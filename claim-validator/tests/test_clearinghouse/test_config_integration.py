"""Tests for clearinghouse configuration integration with ClaimValidatorSettings."""

from __future__ import annotations

from claim_validator.conf import ClaimValidatorSettings


class TestClearinghouseConfig:
    """Verify clearinghouse_config field in settings."""

    def test_default_is_none(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.clearinghouse_config is None

    def test_set_via_constructor(self) -> None:
        config = {
            "provider": "stedi",
            "api_key": "test-key",
        }
        settings = ClaimValidatorSettings(clearinghouse_config=config)
        assert settings.clearinghouse_config is not None
        assert settings.clearinghouse_config["provider"] == "stedi"
        assert settings.clearinghouse_config["api_key"] == "test-key"

    def test_existing_settings_unchanged(self) -> None:
        """Adding clearinghouse_config must not break existing settings."""
        settings = ClaimValidatorSettings(
            ai_config={"provider": "openai", "api_key": "sk-test", "model": "gpt-4o"},
            clearinghouse_config={"provider": "stedi", "api_key": "test"},
        )
        assert settings.ai_config is not None
        assert settings.ai_config["provider"] == "openai"
        assert settings.clearinghouse_config is not None
        assert settings.clearinghouse_config["provider"] == "stedi"

    def test_settings_frozen(self) -> None:
        """Settings remain frozen with new field."""
        settings = ClaimValidatorSettings()
        assert settings.model_config.get("frozen") is True
