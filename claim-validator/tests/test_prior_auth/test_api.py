"""Tests for submit_prior_auth() convenience function."""

from __future__ import annotations

from datetime import date, timedelta

import pydantic
import pytest

from claim_validator.prior_auth._api import submit_prior_auth
from claim_validator.prior_auth.models.request import PriorAuthRequest


def _valid_dict() -> dict:
    return {
        "requester_npi": "1234567893",
        "subscriber": {
            "member_id": "MEM001",
            "first_name": "Jane",
            "last_name": "Doe",
            "dob": date(1985, 3, 15),
        },
        "diagnosis_codes": ["J06.9"],
        "service_lines": [
            {
                "cpt_code": "99213",
                "from_date": date.today() + timedelta(days=10),
            },
        ],
    }


def _valid_request() -> PriorAuthRequest:
    return PriorAuthRequest(**_valid_dict())


class TestSubmitPriorAuthDictInput:
    """AC6, AC8: Accepts dict input, returns PriorAuthResult."""

    def test_valid_dict_passes(self) -> None:
        result = submit_prior_auth(_valid_dict())
        assert result.passed is True
        assert len(result.findings) == 0
        assert result.approved is None

    def test_valid_dict_returns_prior_auth_result(self) -> None:
        from claim_validator.prior_auth.models.result import PriorAuthResult

        result = submit_prior_auth(_valid_dict())
        assert isinstance(result, PriorAuthResult)


class TestSubmitPriorAuthModelInput:
    """AC8: Accepts PriorAuthRequest model input."""

    def test_valid_model_passes(self) -> None:
        result = submit_prior_auth(_valid_request())
        assert result.passed is True
        assert len(result.findings) == 0

    def test_model_input_same_result_as_dict(self) -> None:
        dict_result = submit_prior_auth(_valid_dict())
        model_result = submit_prior_auth(_valid_request())
        assert dict_result.passed == model_result.passed
        assert len(dict_result.findings) == len(model_result.findings)


class TestSubmitPriorAuthInvalidInput:
    """AC11: ValueError for wrong type, ValidationError for malformed dict."""

    def test_wrong_type_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="must be a dict or PriorAuthRequest"):
            submit_prior_auth("not a request")  # type: ignore[arg-type]

    def test_wrong_type_integer_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="must be a dict or PriorAuthRequest"):
            submit_prior_auth(42)  # type: ignore[arg-type]

    def test_wrong_type_list_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="must be a dict or PriorAuthRequest"):
            submit_prior_auth([1, 2, 3])  # type: ignore[arg-type]

    def test_malformed_dict_raises_validation_error(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            submit_prior_auth({"bad_field": "value"})

    def test_missing_required_fields_raises_validation_error(self) -> None:
        with pytest.raises(pydantic.ValidationError):
            submit_prior_auth({"requester_npi": "1234567893"})


class TestSubmitPriorAuthSettings:
    """AC10: Custom settings support."""

    def test_custom_settings(self) -> None:
        from claim_validator.conf import ClaimValidatorSettings

        settings = ClaimValidatorSettings(
            pa_rule_validators=[
                "claim_validator.prior_auth.validators.rule_based.npi.PANPIValidator",
            ]
        )
        result = submit_prior_auth(_valid_request(), settings=settings)
        assert result.passed is True

    def test_none_settings_uses_defaults(self) -> None:
        result = submit_prior_auth(_valid_request(), settings=None)
        assert result.passed is True


class TestSubmitPriorAuthImport:
    """AC13: Import from top level."""

    def test_import_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import submit_prior_auth as fn

        assert callable(fn)

    def test_import_from_top_level(self) -> None:
        from claim_validator import submit_prior_auth as fn

        assert callable(fn)
