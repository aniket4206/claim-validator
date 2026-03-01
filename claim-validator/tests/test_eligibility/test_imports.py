"""Tests for eligibility module re-exports — AC: all."""

from __future__ import annotations


class TestTopLevelImports:
    """All eligibility symbols importable from claim_validator."""

    def test_eligibility_request(self) -> None:
        from claim_validator import EligibilityRequest

        assert EligibilityRequest is not None

    def test_eligibility_response(self) -> None:
        from claim_validator import EligibilityResponse

        assert EligibilityResponse is not None

    def test_eligibility_result(self) -> None:
        from claim_validator import EligibilityResult

        assert EligibilityResult is not None

    def test_coverage_info(self) -> None:
        from claim_validator import CoverageInfo

        assert CoverageInfo is not None

    def test_benefit_info(self) -> None:
        from claim_validator import BenefitInfo

        assert BenefitInfo is not None

    def test_aaa_error(self) -> None:
        from claim_validator import AAAError

        assert AAAError is not None

    def test_coverage_status(self) -> None:
        from claim_validator import CoverageStatus

        assert CoverageStatus is not None

    def test_clearinghouse_error(self) -> None:
        from claim_validator import ClearinghouseError

        assert ClearinghouseError is not None


class TestEligibilityModuleImports:
    """All symbols importable from claim_validator.eligibility."""

    def test_eligibility_request(self) -> None:
        from claim_validator.eligibility import EligibilityRequest

        assert EligibilityRequest is not None

    def test_eligibility_response(self) -> None:
        from claim_validator.eligibility import EligibilityResponse

        assert EligibilityResponse is not None

    def test_eligibility_result(self) -> None:
        from claim_validator.eligibility import EligibilityResult

        assert EligibilityResult is not None

    def test_coverage_info(self) -> None:
        from claim_validator.eligibility import CoverageInfo

        assert CoverageInfo is not None

    def test_benefit_info(self) -> None:
        from claim_validator.eligibility import BenefitInfo

        assert BenefitInfo is not None

    def test_aaa_error(self) -> None:
        from claim_validator.eligibility import AAAError

        assert AAAError is not None

    def test_coverage_status(self) -> None:
        from claim_validator.eligibility import CoverageStatus

        assert CoverageStatus is not None


class TestClearinghouseErrorHierarchy:
    """AC 6: ClearinghouseError is a subclass of ClaimValidatorError."""

    def test_subclass(self) -> None:
        from claim_validator import ClaimValidatorError, ClearinghouseError

        assert issubclass(ClearinghouseError, ClaimValidatorError)

    def test_instantiation(self) -> None:
        from claim_validator import ClearinghouseError

        err = ClearinghouseError("Connection timeout")
        assert str(err) == "Connection timeout"

    def test_catchable_as_base(self) -> None:
        from claim_validator import ClearinghouseError

        with self._raises_clearinghouse():
            raise ClearinghouseError("test")

    @staticmethod
    def _raises_clearinghouse():
        """Context manager that catches ClaimValidatorError."""
        import contextlib

        from claim_validator import ClaimValidatorError

        return contextlib.suppress(ClaimValidatorError)


class TestExistingImportsUnchanged:
    """Verify existing imports still work (zero breaking changes)."""

    def test_validate(self) -> None:
        from claim_validator import validate

        assert callable(validate)

    def test_submit_prior_auth(self) -> None:
        from claim_validator import submit_prior_auth

        assert callable(submit_prior_auth)

    def test_claim_data(self) -> None:
        from claim_validator import ClaimData

        assert ClaimData is not None

    def test_prior_auth_request(self) -> None:
        from claim_validator import PriorAuthRequest

        assert PriorAuthRequest is not None
