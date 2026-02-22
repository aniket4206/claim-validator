"""Tests for BaseValidator abstract base class contract."""

from __future__ import annotations

import pytest

from claim_validator.constants import Severity
from claim_validator.models.claim import ClaimData
from claim_validator.models.results import Finding, ValidatorOutput
from claim_validator.validators.base import BaseValidator


class ConcreteValidator(BaseValidator):
    """Minimal concrete validator for testing."""

    name = "ConcreteValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        return self._make_output([])


class FindingValidator(BaseValidator):
    """Validator that always produces a finding."""

    name = "FindingValidator"

    def validate(self, claim: ClaimData) -> ValidatorOutput:
        findings = [
            self._make_finding(
                code="TEST_ERROR",
                message="Test error message",
                severity=Severity.ERROR,
                field_name="billing_provider_npi",
                suggestion="Fix the NPI",
            ),
        ]
        return self._make_output(findings)


class TestBaseValidatorContract:
    """BaseValidator ABC cannot be instantiated directly."""

    def test_cannot_instantiate_directly(self) -> None:
        with pytest.raises(TypeError, match="abstract method"):
            BaseValidator()  # type: ignore[abstract]

    def test_subclass_without_validate_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="abstract method"):

            class IncompleteValidator(BaseValidator):
                name = "Incomplete"

            IncompleteValidator()  # type: ignore[abstract]

    def test_concrete_subclass_can_be_instantiated(self) -> None:
        validator = ConcreteValidator()
        assert isinstance(validator, BaseValidator)

    def test_name_attribute_required(self) -> None:
        validator = ConcreteValidator()
        assert validator.name == "ConcreteValidator"


class TestMakeOutput:
    """Tests for _make_output() helper."""

    def test_empty_findings(self) -> None:
        validator = ConcreteValidator()
        output = validator._make_output([])
        assert isinstance(output, ValidatorOutput)
        assert output.validator_name == "ConcreteValidator"
        assert output.findings == []

    def test_with_findings(self) -> None:
        validator = ConcreteValidator()
        finding = Finding(
            code="TEST",
            message="Test",
            severity=Severity.ERROR,
            field_name="test_field",
        )
        output = validator._make_output([finding])
        assert len(output.findings) == 1
        assert output.findings[0].code == "TEST"

    def test_validator_name_from_class(self) -> None:
        validator = FindingValidator()
        output = validator.validate(ClaimData())
        assert output.validator_name == "FindingValidator"


class TestMakeFinding:
    """Tests for _make_finding() convenience method."""

    def test_creates_finding_with_required_fields(self) -> None:
        validator = ConcreteValidator()
        finding = validator._make_finding(
            code="INVALID_NPI",
            message="NPI fails Luhn check",
            severity=Severity.ERROR,
            field_name="billing_provider_npi",
        )
        assert isinstance(finding, Finding)
        assert finding.code == "INVALID_NPI"
        assert finding.message == "NPI fails Luhn check"
        assert finding.severity == Severity.ERROR
        assert finding.field_name == "billing_provider_npi"

    def test_creates_finding_with_all_fields(self) -> None:
        validator = ConcreteValidator()
        finding = validator._make_finding(
            code="INVALID_NPI",
            message="NPI fails Luhn check",
            severity=Severity.ERROR,
            field_name="billing_provider_npi",
            line_number=3,
            suggestion="Verify NPI at npiregistry.cms.hhs.gov",
            context={"expected_check_digit": 3},
        )
        assert finding.line_number == 3
        assert finding.suggestion == "Verify NPI at npiregistry.cms.hhs.gov"
        assert finding.context == {"expected_check_digit": 3}

    def test_defaults_for_optional_fields(self) -> None:
        validator = ConcreteValidator()
        finding = validator._make_finding(
            code="TEST",
            message="Test",
            severity=Severity.WARNING,
            field_name="test",
        )
        assert finding.line_number is None
        assert finding.suggestion == ""
        assert finding.context is None

    def test_keyword_only_arguments(self) -> None:
        """_make_finding() uses keyword-only args to prevent positional mistakes."""
        validator = ConcreteValidator()
        with pytest.raises(TypeError):
            validator._make_finding(  # type: ignore[misc]
                "INVALID_NPI",
                "NPI fails",
                Severity.ERROR,
                "billing_provider_npi",
            )


class TestValidatorStatelessness:
    """Validators must be stateless between calls."""

    def test_validate_returns_validator_output(self) -> None:
        validator = ConcreteValidator()
        result = validator.validate(ClaimData())
        assert isinstance(result, ValidatorOutput)

    def test_multiple_calls_independent(self) -> None:
        validator = FindingValidator()
        result1 = validator.validate(ClaimData())
        result2 = validator.validate(ClaimData())
        assert len(result1.findings) == 1
        assert len(result2.findings) == 1
        assert result1.findings[0].code == result2.findings[0].code

    def test_claim_not_modified(self) -> None:
        """Frozen ClaimData ensures validators cannot modify the claim."""
        claim = ClaimData(billing_provider_npi="1234567893")
        validator = ConcreteValidator()
        validator.validate(claim)
        assert claim.billing_provider_npi == "1234567893"
