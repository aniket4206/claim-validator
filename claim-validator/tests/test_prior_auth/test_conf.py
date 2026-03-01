"""Tests for prior authorization settings in ClaimValidatorSettings."""

from __future__ import annotations

import pydantic
import pytest

from claim_validator import ClaimValidatorSettings
from claim_validator.conf import DEFAULT_PA_RULE_VALIDATORS


class TestPASettingsDefaults:
    def test_default_pa_rule_validators(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.pa_rule_validators == DEFAULT_PA_RULE_VALIDATORS
        assert len(settings.pa_rule_validators) == 7

    def test_default_pa_ai_validators_empty(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.pa_ai_validators == []

    def test_default_skip_clearinghouse_on_pa_failure(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.skip_clearinghouse_on_pa_failure is True

    def test_default_pa_skip_ai(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.pa_skip_ai is False


class TestPASettingsEnvVars:
    def test_env_override_skip_clearinghouse(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAIM_VALIDATOR_SKIP_CLEARINGHOUSE_ON_PA_FAILURE", "false")
        settings = ClaimValidatorSettings()
        assert settings.skip_clearinghouse_on_pa_failure is False

    def test_env_override_pa_skip_ai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAIM_VALIDATOR_PA_SKIP_AI", "true")
        settings = ClaimValidatorSettings()
        assert settings.pa_skip_ai is True

    def test_env_override_pa_rule_validators_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAIM_VALIDATOR_PA_RULE_VALIDATORS",
            '["my.app.PAValidator"]',
        )
        settings = ClaimValidatorSettings()
        assert settings.pa_rule_validators == ["my.app.PAValidator"]

    def test_env_override_pa_ai_validators_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAIM_VALIDATOR_PA_AI_VALIDATORS",
            '["my.app.PAAIValidator"]',
        )
        settings = ClaimValidatorSettings()
        assert settings.pa_ai_validators == ["my.app.PAAIValidator"]


class TestPASettingsExplicit:
    def test_explicit_pa_rule_validators(self) -> None:
        settings = ClaimValidatorSettings(pa_rule_validators=["my.PAValidator"])
        assert settings.pa_rule_validators == ["my.PAValidator"]

    def test_explicit_pa_ai_validators(self) -> None:
        settings = ClaimValidatorSettings(pa_ai_validators=["my.PAAIValidator"])
        assert settings.pa_ai_validators == ["my.PAAIValidator"]

    def test_explicit_skip_clearinghouse_false(self) -> None:
        settings = ClaimValidatorSettings(skip_clearinghouse_on_pa_failure=False)
        assert settings.skip_clearinghouse_on_pa_failure is False

    def test_explicit_pa_skip_ai_true(self) -> None:
        settings = ClaimValidatorSettings(pa_skip_ai=True)
        assert settings.pa_skip_ai is True


class TestPASettingsFrozen:
    def test_frozen_pa_skip_ai(self) -> None:
        settings = ClaimValidatorSettings()
        with pytest.raises(pydantic.ValidationError):
            settings.pa_skip_ai = True  # type: ignore[misc]

    def test_frozen_skip_clearinghouse(self) -> None:
        settings = ClaimValidatorSettings()
        with pytest.raises(pydantic.ValidationError):
            settings.skip_clearinghouse_on_pa_failure = False  # type: ignore[misc]
