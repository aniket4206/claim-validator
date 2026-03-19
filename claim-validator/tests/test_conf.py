"""Tests for ClaimValidatorSettings."""

from __future__ import annotations

import pydantic
import pytest

from claim_validator import ClaimValidatorSettings
from claim_validator.conf import DEFAULT_RULE_VALIDATORS


class TestClaimValidatorSettingsDefaults:
    def test_default_rule_validators(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.rule_validators == DEFAULT_RULE_VALIDATORS
        assert len(settings.rule_validators) == 8

    def test_default_ai_validators_empty(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.ai_validators == []

    def test_default_skip_ai_on_rule_failure(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.skip_ai_on_rule_failure is True

    def test_default_ai_config_none(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.ai_config is None


class TestClaimValidatorSettingsEnvVars:
    def test_env_override_skip_ai(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CLAIM_VALIDATOR_SKIP_AI_ON_RULE_FAILURE", "false")
        settings = ClaimValidatorSettings()
        assert settings.skip_ai_on_rule_failure is False

    def test_env_override_rule_validators_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAIM_VALIDATOR_RULE_VALIDATORS", '["my.app.CustomValidator"]'
        )
        settings = ClaimValidatorSettings()
        assert settings.rule_validators == ["my.app.CustomValidator"]

    def test_env_override_ai_config_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAIM_VALIDATOR_AI_CONFIG",
            '{"provider": "anthropic", "api_key": "sk-test",'
            ' "model": "claude-sonnet-4-5-20241022"}',
        )
        settings = ClaimValidatorSettings()
        assert settings.ai_config is not None
        assert settings.ai_config["provider"] == "anthropic"
        assert settings.ai_config["api_key"] == "sk-test"

    def test_env_override_ai_validators_json(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAIM_VALIDATOR_AI_VALIDATORS", '["my.app.AIValidator"]'
        )
        settings = ClaimValidatorSettings()
        assert settings.ai_validators == ["my.app.AIValidator"]


class TestClaimValidatorSettingsExplicit:
    def test_explicit_rule_validators(self) -> None:
        settings = ClaimValidatorSettings(rule_validators=["my.Validator", "my.Other"])
        assert settings.rule_validators == ["my.Validator", "my.Other"]

    def test_explicit_ai_config(self) -> None:
        ai_cfg = {"provider": "openai", "api_key": "sk-key", "model": "gpt-4o"}
        settings = ClaimValidatorSettings(ai_config=ai_cfg)
        assert settings.ai_config is not None
        assert settings.ai_config["provider"] == "openai"

    def test_explicit_skip_ai_false(self) -> None:
        settings = ClaimValidatorSettings(skip_ai_on_rule_failure=False)
        assert settings.skip_ai_on_rule_failure is False

    def test_explicit_ai_validators(self) -> None:
        settings = ClaimValidatorSettings(
            ai_validators=["claim_validator.validators.ai.code_validation.CodeValidationAI"]
        )
        assert len(settings.ai_validators) == 1

    def test_full_construction(self) -> None:
        settings = ClaimValidatorSettings(
            rule_validators=["my.Validator"],
            ai_validators=["my.AIValidator"],
            skip_ai_on_rule_failure=False,
            ai_config={
                "provider": "anthropic",
                "api_key": "sk-ant",
                "model": "claude-sonnet-4-5-20241022",
            },
        )
        assert len(settings.rule_validators) == 1
        assert len(settings.ai_validators) == 1
        assert settings.skip_ai_on_rule_failure is False
        assert settings.ai_config is not None


class TestClaimValidatorSettingsFrozen:
    def test_frozen_raises_on_field_set(self) -> None:
        settings = ClaimValidatorSettings()
        with pytest.raises(pydantic.ValidationError):
            settings.skip_ai_on_rule_failure = False  # type: ignore[misc]

    def test_frozen_raises_on_list_replace(self) -> None:
        settings = ClaimValidatorSettings()
        with pytest.raises(pydantic.ValidationError):
            settings.rule_validators = []  # type: ignore[misc]


class TestClaimValidatorSettingsValidation:
    def test_invalid_rule_validators_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ClaimValidatorSettings(rule_validators="not-a-list")  # type: ignore[arg-type]

    def test_invalid_skip_ai_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ClaimValidatorSettings(skip_ai_on_rule_failure="not-a-bool")  # type: ignore[arg-type]

    def test_invalid_ai_config_type(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            ClaimValidatorSettings(ai_config="not-a-dict")  # type: ignore[arg-type]


class TestMultiClearinghouseSettings:
    """Tests for multi-clearinghouse routing settings (PE-1.4)."""

    def test_default_clearinghouse_configs_none(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.clearinghouse_configs is None

    def test_default_payer_routing_overrides_none(self) -> None:
        settings = ClaimValidatorSettings()
        assert settings.payer_routing_overrides is None

    def test_existing_clearinghouse_config_still_works(self) -> None:
        """Backward compat — single provider config unchanged."""
        settings = ClaimValidatorSettings(
            clearinghouse_config={"provider": "stedi", "api_key": "test-key"},
        )
        assert settings.clearinghouse_config is not None
        assert settings.clearinghouse_config["provider"] == "stedi"

    def test_clearinghouse_configs_explicit(self) -> None:
        configs = {
            "stedi": {"api_key": "k1"},
            "claimmd": {"account_key": "k2"},
        }
        settings = ClaimValidatorSettings(clearinghouse_configs=configs)
        assert settings.clearinghouse_configs is not None
        assert "stedi" in settings.clearinghouse_configs
        assert "claimmd" in settings.clearinghouse_configs
        assert settings.clearinghouse_configs["stedi"]["api_key"] == "k1"

    def test_payer_routing_overrides_explicit(self) -> None:
        overrides = {
            "60054": [
                {
                    "clearinghouse": "claimmd",
                    "payer_id_at_clearinghouse": "AETNA",
                    "priority": 1,
                    "supports": ["837P"],
                },
            ],
        }
        settings = ClaimValidatorSettings(payer_routing_overrides=overrides)
        assert settings.payer_routing_overrides is not None
        assert "60054" in settings.payer_routing_overrides
        assert len(settings.payer_routing_overrides["60054"]) == 1

    def test_clearinghouse_configs_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAIM_VALIDATOR_CLEARINGHOUSE_CONFIGS",
            '{"stedi": {"api_key": "env-key"}}',
        )
        settings = ClaimValidatorSettings()
        assert settings.clearinghouse_configs is not None
        assert settings.clearinghouse_configs["stedi"]["api_key"] == "env-key"

    def test_payer_routing_overrides_env_var(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            "CLAIM_VALIDATOR_PAYER_ROUTING_OVERRIDES",
            '{"TEST1": [{"clearinghouse": "stedi", "payer_id_at_clearinghouse": "T", "priority": 1, "supports": ["837P"]}]}',
        )
        settings = ClaimValidatorSettings()
        assert settings.payer_routing_overrides is not None
        assert "TEST1" in settings.payer_routing_overrides

    def test_both_single_and_multi_can_coexist(self) -> None:
        """Both clearinghouse_config and clearinghouse_configs can be set."""
        settings = ClaimValidatorSettings(
            clearinghouse_config={"provider": "stedi", "api_key": "single"},
            clearinghouse_configs={"stedi": {"api_key": "pool"}, "claimmd": {"account_key": "pool2"}},
        )
        assert settings.clearinghouse_config is not None
        assert settings.clearinghouse_configs is not None


class TestClaimValidatorSettingsDefaultValidatorPaths:
    """Verify the default validator paths follow naming conventions."""

    def test_all_defaults_are_dotted_paths(self) -> None:
        for path in DEFAULT_RULE_VALIDATORS:
            assert "." in path, f"Expected dotted path, got: {path}"

    def test_all_defaults_end_with_validator(self) -> None:
        for path in DEFAULT_RULE_VALIDATORS:
            class_name = path.rsplit(".", 1)[-1]
            assert class_name.endswith("Validator"), f"Expected *Validator, got: {class_name}"

    def test_defaults_include_expected_validators(self) -> None:
        class_names = [p.rsplit(".", 1)[-1] for p in DEFAULT_RULE_VALIDATORS]
        assert "CompletenessValidator" in class_names
        assert "NPIValidator" in class_names
        assert "CodingValidator" in class_names
        assert "MonetaryValidator" in class_names
        assert "DuplicateValidator" in class_names
        assert "TimelyFilingValidator" in class_names
        assert "SubscriberIDValidator" in class_names
        assert "DemographicsValidator" in class_names
