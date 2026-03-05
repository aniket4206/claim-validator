"""Tests for stage configuration, default domain configs, and stage runner."""

from __future__ import annotations

import pytest

from claim_validator.exceptions import ConfigurationError
from claim_validator.shared.validators.date import validate_date
from claim_validator.shared.validators.demographics import validate_demographics
from claim_validator.shared.validators.diagnosis import validate_diagnosis
from claim_validator.shared.validators.member_id import validate_member_id
from claim_validator.shared.validators.npi import validate_npi
from claim_validator.shared.validators.payer_id import validate_payer_id
from claim_validator.shared.validators.procedure import validate_procedure
from claim_validator.shared.validators.stage import (
    DEFAULT_CLAIM_VALIDATORS,
    DEFAULT_ELIGIBILITY_VALIDATORS,
    DEFAULT_PA_VALIDATORS,
    StageValidatorConfig,
    get_default_stage_config,
    run_stage_validators,
)


class TestStageValidatorConfig:
    """StageValidatorConfig creation and immutability."""

    def test_creation(self) -> None:
        cfg = StageValidatorConfig(validators=("npi", "date"))
        assert cfg.validators == ("npi", "date")

    def test_frozen(self) -> None:
        cfg = StageValidatorConfig(validators=("npi",))
        with pytest.raises(AttributeError):
            cfg.validators = ("date",)  # type: ignore[misc]

    def test_empty_config(self) -> None:
        cfg = StageValidatorConfig(validators=())
        assert cfg.validators == ()


class TestResolveValidators:
    """resolve() returns correct functions in configuration order."""

    def test_resolve_returns_correct_functions(self) -> None:
        cfg = StageValidatorConfig(validators=("npi", "diagnosis", "payer_id"))
        funcs = cfg.resolve()
        assert funcs == (validate_npi, validate_diagnosis, validate_payer_id)

    def test_resolve_preserves_order(self) -> None:
        cfg1 = StageValidatorConfig(validators=("date", "npi"))
        cfg2 = StageValidatorConfig(validators=("npi", "date"))
        assert cfg1.resolve() == (validate_date, validate_npi)
        assert cfg2.resolve() == (validate_npi, validate_date)

    def test_resolve_invalid_id_raises_configuration_error(self) -> None:
        cfg = StageValidatorConfig(validators=("npi", "BOGUS"))
        with pytest.raises(ConfigurationError, match="Unknown shared validator"):
            cfg.resolve()

    def test_resolve_empty_config(self) -> None:
        cfg = StageValidatorConfig(validators=())
        assert cfg.resolve() == ()


class TestDefaultStageConfigs:
    """get_default_stage_config returns correct defaults per domain."""

    def test_claim_defaults(self) -> None:
        cfg = get_default_stage_config("claim")
        assert cfg.validators == DEFAULT_CLAIM_VALIDATORS
        assert cfg.validators == ("npi", "member_id", "demographics", "diagnosis", "procedure")

    def test_eligibility_defaults(self) -> None:
        cfg = get_default_stage_config("eligibility")
        assert cfg.validators == DEFAULT_ELIGIBILITY_VALIDATORS
        assert cfg.validators == ("date", "demographics", "member_id", "npi", "payer_id")

    def test_prior_auth_defaults(self) -> None:
        cfg = get_default_stage_config("prior_auth")
        assert cfg.validators == DEFAULT_PA_VALIDATORS
        assert cfg.validators == ("date", "diagnosis", "member_id", "npi", "procedure")

    def test_unknown_domain_raises_configuration_error(self) -> None:
        with pytest.raises(ConfigurationError, match="Unknown domain"):
            get_default_stage_config("UNKNOWN")

    def test_error_lists_available_domains(self) -> None:
        with pytest.raises(ConfigurationError, match="Available:"):
            get_default_stage_config("nonexistent")

    def test_all_defaults_resolvable(self) -> None:
        """All default configs can be resolved without error."""
        for domain in ("claim", "eligibility", "prior_auth"):
            cfg = get_default_stage_config(domain)
            funcs = cfg.resolve()
            assert len(funcs) == len(cfg.validators)

    def test_claim_resolves_to_expected_functions(self) -> None:
        cfg = get_default_stage_config("claim")
        funcs = cfg.resolve()
        assert funcs == (
            validate_npi,
            validate_member_id,
            validate_demographics,
            validate_diagnosis,
            validate_procedure,
        )

    def test_eligibility_resolves_to_expected_functions(self) -> None:
        cfg = get_default_stage_config("eligibility")
        funcs = cfg.resolve()
        assert funcs == (
            validate_date,
            validate_demographics,
            validate_member_id,
            validate_npi,
            validate_payer_id,
        )

    def test_prior_auth_resolves_to_expected_functions(self) -> None:
        cfg = get_default_stage_config("prior_auth")
        funcs = cfg.resolve()
        assert funcs == (
            validate_date,
            validate_diagnosis,
            validate_member_id,
            validate_npi,
            validate_procedure,
        )


class TestRunStageValidators:
    """run_stage_validators invokes validators with correct parameters."""

    def test_code_prefix_passthrough(self) -> None:
        """Validators receive the code_prefix when data_extractor doesn't supply it."""
        cfg = StageValidatorConfig(validators=("npi",))

        def extractor(vid: str) -> dict[str, object]:
            return {"npi": "INVALID"}

        findings = run_stage_validators(cfg, extractor, code_prefix="PA_")
        assert len(findings) >= 1
        assert all(f.code.startswith("PA_") for f in findings)

    def test_data_extractor_code_prefix_overrides(self) -> None:
        """If data_extractor provides code_prefix, that takes precedence."""
        cfg = StageValidatorConfig(validators=("npi",))

        def extractor(vid: str) -> dict[str, object]:
            return {"npi": "INVALID", "code_prefix": "CLM_"}

        findings = run_stage_validators(cfg, extractor, code_prefix="PA_")
        assert len(findings) >= 1
        assert all(f.code.startswith("CLM_") for f in findings)

    def test_aggregates_findings_from_multiple_validators(self) -> None:
        """Findings from multiple validators are aggregated."""
        cfg = StageValidatorConfig(validators=("npi", "member_id"))

        def extractor(vid: str) -> dict[str, object]:
            if vid == "npi":
                return {"npi": "INVALID"}
            return {"member_id": "!"}

        findings = run_stage_validators(cfg, extractor)
        # Both validators should produce findings for invalid input
        assert len(findings) >= 2
        codes = [f.code for f in findings]
        assert any("NPI" in c for c in codes)
        assert any("MEMBER_ID" in c for c in codes)

    def test_empty_config_returns_empty_findings(self) -> None:
        cfg = StageValidatorConfig(validators=())

        def extractor(vid: str) -> dict[str, object]:
            return {}

        assert run_stage_validators(cfg, extractor) == []

    def test_valid_data_returns_empty_findings(self) -> None:
        """Valid inputs produce no findings."""
        cfg = StageValidatorConfig(validators=("npi",))

        def extractor(vid: str) -> dict[str, object]:
            return {"npi": "1234567893"}  # valid NPI (Luhn check passes)

        findings = run_stage_validators(cfg, extractor)
        assert findings == []

    def test_field_name_passthrough(self) -> None:
        """Validators receive field_name from data_extractor."""
        cfg = StageValidatorConfig(validators=("npi",))

        def extractor(vid: str) -> dict[str, object]:
            return {"npi": "INVALID", "field_name": "provider_npi"}

        findings = run_stage_validators(cfg, extractor)
        assert len(findings) >= 1
        assert findings[0].field_name == "provider_npi"

    def test_demographics_via_runner(self) -> None:
        """Demographics validator works through the runner with its unique signature."""
        cfg = StageValidatorConfig(validators=("demographics",))

        def extractor(vid: str) -> dict[str, object]:
            return {
                "name": None,
                "gender": None,
                "dob": None,
                "field_prefix": "patient_",
            }

        findings = run_stage_validators(cfg, extractor, code_prefix="PA_")
        # demographics with all None should produce findings
        assert len(findings) >= 1
        assert all(f.code.startswith("PA_") for f in findings)

    def test_diagnosis_list_via_runner(self) -> None:
        """Diagnosis validator (list-based) works through the runner."""
        cfg = StageValidatorConfig(validators=("diagnosis",))

        def extractor(vid: str) -> dict[str, object]:
            return {"codes": ["INVALID_FORMAT"], "field_name": "dx_codes"}

        findings = run_stage_validators(cfg, extractor)
        assert len(findings) >= 1
        assert findings[0].field_name == "dx_codes"
