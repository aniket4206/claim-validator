"""Tests for PipelineConfig creation, immutability, defaults, and field types."""

from __future__ import annotations

from typing import Any

import pytest

from claim_validator.models.results import ValidatorOutput
from claim_validator.shared.deidentifier.base import BaseDeidentifier
from claim_validator.shared.deidentifier.config import DeidentificationConfig
from claim_validator.shared.pipeline.config import PipelineConfig
from claim_validator.validators.base import BaseValidator


class _StubValidator(BaseValidator):
    """Minimal validator for config tests."""

    name = "stub"

    def validate(self, claim: Any) -> ValidatorOutput:
        return ValidatorOutput(validator_name=self.name, findings=[])


class TestPipelineConfigCreation:
    """PipelineConfig can be created with all field categories."""

    def test_all_fields_specified(self) -> None:
        v = _StubValidator()
        deid = BaseDeidentifier(DeidentificationConfig())
        cfg = PipelineConfig(
            domain="claim",
            validators=(v,),
            clearinghouse_client="mock_ch",
            ai_interpreter="mock_ai",
            deidentifier=deid,
            skip_ai_on_rule_failure=False,
            skip_clearinghouse_on_rule_failure=False,
            code_prefix="CLM_",
        )
        assert cfg.domain == "claim"
        assert cfg.validators == (v,)
        assert cfg.clearinghouse_client == "mock_ch"
        assert cfg.ai_interpreter == "mock_ai"
        assert cfg.deidentifier is deid
        assert cfg.skip_ai_on_rule_failure is False
        assert cfg.skip_clearinghouse_on_rule_failure is False
        assert cfg.code_prefix == "CLM_"

    def test_domain_only(self) -> None:
        cfg = PipelineConfig(domain="eligibility")
        assert cfg.domain == "eligibility"

    def test_multiple_validators(self) -> None:
        v1, v2 = _StubValidator(), _StubValidator()
        cfg = PipelineConfig(domain="test", validators=(v1, v2))
        assert len(cfg.validators) == 2


class TestPipelineConfigDefaults:
    """Default values for optional fields match AC-1."""

    def test_validators_default_empty(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.validators == ()

    def test_clearinghouse_client_default_none(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.clearinghouse_client is None

    def test_ai_interpreter_default_none(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.ai_interpreter is None

    def test_deidentifier_default_none(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.deidentifier is None

    def test_skip_ai_on_rule_failure_default_true(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.skip_ai_on_rule_failure is True

    def test_skip_clearinghouse_on_rule_failure_default_true(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.skip_clearinghouse_on_rule_failure is True

    def test_code_prefix_default_empty(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.code_prefix == ""


class TestPipelineConfigImmutability:
    """PipelineConfig is frozen — attributes cannot be reassigned."""

    def test_frozen_domain(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.domain = "other"  # type: ignore[misc]

    def test_frozen_validators(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.validators = ()  # type: ignore[misc]

    def test_frozen_clearinghouse_client(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.clearinghouse_client = "x"  # type: ignore[misc]

    def test_frozen_ai_interpreter(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.ai_interpreter = "x"  # type: ignore[misc]

    def test_frozen_deidentifier(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.deidentifier = None  # type: ignore[misc]

    def test_frozen_skip_ai_on_rule_failure(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.skip_ai_on_rule_failure = False  # type: ignore[misc]

    def test_frozen_skip_clearinghouse_on_rule_failure(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.skip_clearinghouse_on_rule_failure = False  # type: ignore[misc]

    def test_frozen_code_prefix(self) -> None:
        cfg = PipelineConfig(domain="test")
        with pytest.raises(AttributeError):
            cfg.code_prefix = "X_"  # type: ignore[misc]


class TestPipelineConfigFieldTypes:
    """All fields have correct types."""

    def test_domain_is_str(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert isinstance(cfg.domain, str)

    def test_validators_is_tuple(self) -> None:
        cfg = PipelineConfig(domain="test", validators=(_StubValidator(),))
        assert isinstance(cfg.validators, tuple)

    def test_skip_flags_are_bool(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert isinstance(cfg.skip_ai_on_rule_failure, bool)
        assert isinstance(cfg.skip_clearinghouse_on_rule_failure, bool)

    def test_code_prefix_is_str(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert isinstance(cfg.code_prefix, str)


class TestPipelineConfigValidation:
    """PipelineConfig validates constraints at creation time."""

    def test_ai_without_deidentifier_raises(self) -> None:
        with pytest.raises(ValueError, match="deidentifier is required"):
            PipelineConfig(domain="test", ai_interpreter="mock_ai")

    def test_ai_with_deidentifier_ok(self) -> None:
        deid = BaseDeidentifier(DeidentificationConfig())
        cfg = PipelineConfig(
            domain="test", ai_interpreter="mock_ai", deidentifier=deid
        )
        assert cfg.ai_interpreter == "mock_ai"
        assert cfg.deidentifier is deid

    def test_no_ai_no_deidentifier_ok(self) -> None:
        cfg = PipelineConfig(domain="test")
        assert cfg.ai_interpreter is None
        assert cfg.deidentifier is None


class TestPipelineConfigDomainSpecific:
    """Different domain configs can be created independently (AC-6)."""

    def test_three_domain_configs(self) -> None:
        claim_cfg = PipelineConfig(domain="claim", code_prefix="CLM_")
        elig_cfg = PipelineConfig(domain="eligibility", code_prefix="ELIG_")
        pa_cfg = PipelineConfig(domain="prior_auth", code_prefix="PA_")

        assert claim_cfg.domain == "claim"
        assert elig_cfg.domain == "eligibility"
        assert pa_cfg.domain == "prior_auth"
        assert claim_cfg.code_prefix != elig_cfg.code_prefix
