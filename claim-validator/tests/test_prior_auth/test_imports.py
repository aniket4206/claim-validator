"""Tests for prior authorization module imports and re-exports."""

from __future__ import annotations


class TestPriorAuthModuleImports:
    """Verify all PA symbols are importable from expected paths."""

    def test_import_enums_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import (
            CertificationActionCode,
            CertificationTypeCode,
            RequestCategoryCode,
        )

        assert CertificationActionCode.CERTIFIED_IN_TOTAL == "A1"
        assert RequestCategoryCode.HEALTH_SERVICES_REVIEW == "HS"
        assert CertificationTypeCode.INITIAL == "I"

    def test_import_models_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import (
            PriorAuthPipeline,
            PriorAuthRequest,
            PriorAuthResponse,
            PriorAuthResult,
        )

        # Verify they are importable (not None)
        assert PriorAuthPipeline is not None
        assert PriorAuthRequest is not None
        assert PriorAuthResponse is not None
        assert PriorAuthResult is not None

    def test_import_submit_prior_auth(self) -> None:
        from claim_validator.prior_auth import submit_prior_auth

        assert callable(submit_prior_auth)

    def test_import_parse_278_response(self) -> None:
        from claim_validator.prior_auth import parse_278_response

        assert callable(parse_278_response)

    def test_import_from_top_level(self) -> None:
        from claim_validator import (
            CertificationActionCode,
            PriorAuthPipeline,
            PriorAuthRequest,
            parse_278_response,
            submit_prior_auth,
        )

        assert PriorAuthRequest is not None
        assert PriorAuthPipeline is not None
        assert CertificationActionCode.CERTIFIED_IN_TOTAL == "A1"
        assert callable(submit_prior_auth)
        assert callable(parse_278_response)

    def test_all_pa_symbols_in_top_level_all(self) -> None:
        import claim_validator

        pa_symbols = [
            "CertificationActionCode",
            "CertificationTypeCode",
            "DeidentifiedPriorAuthResponse",
            "PADeterminationResult",
            "parse_278_response",
            "PatientInfo",
            "PriorAuthError",
            "PriorAuthPipeline",
            "PriorAuthRequest",
            "PriorAuthResponse",
            "PriorAuthResult",
            "RequestCategoryCode",
            "ServiceLine",
            "ServiceLineDecision",
            "submit_prior_auth",
            "SubscriberInfo",
        ]
        for sym in pa_symbols:
            assert sym in claim_validator.__all__, f"{sym} not in claim_validator.__all__"

    def test_all_pa_symbols_in_prior_auth_all(self) -> None:
        from claim_validator import prior_auth

        pa_symbols = [
            "CertificationActionCode",
            "CertificationTypeCode",
            "DeidentifiedPriorAuthResponse",
            "determine_pa_required",
            "PADeterminationResult",
            "parse_278_response",
            "PatientInfo",
            "PriorAuthError",
            "PriorAuthPipeline",
            "PriorAuthRequest",
            "PriorAuthResponse",
            "PriorAuthResult",
            "RequestCategoryCode",
            "ServiceLine",
            "ServiceLineDecision",
            "submit_prior_auth",
            "SubscriberInfo",
        ]
        for sym in pa_symbols:
            assert sym in prior_auth.__all__, f"{sym} not in prior_auth.__all__"
