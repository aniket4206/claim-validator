"""Tests for BaseClearinghouseClient ABC."""

from __future__ import annotations

from typing import Any

import pytest

from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)


class ConcreteClient(BaseClearinghouseClient):
    """Minimal concrete implementation for testing."""

    @property
    def provider_name(self) -> str:
        return "test"

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        return SubmissionResult(status="ok", accepted=True)

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        return ClearinghouseEligibilityResponse(status="active", eligible=True)

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        return ClaimStatusResponse(status="found", claim_status="paid")


class TestBaseClearinghouseClientABC:
    """Verify ABC behaviour."""

    def test_cannot_instantiate_abc(self) -> None:
        with pytest.raises(TypeError, match="abstract"):
            BaseClearinghouseClient(api_key="k")  # type: ignore[abstract]

    def test_concrete_subclass_instantiation(self) -> None:
        client = ConcreteClient(api_key="test-key", base_url="https://test.com")
        assert client.provider_name == "test"

    def test_submit_claim(self) -> None:
        client = ConcreteClient(api_key="k", base_url="https://test.com")
        result = client.submit_claim({"npi": "123"})
        assert isinstance(result, SubmissionResult)
        assert result.accepted is True

    def test_check_eligibility(self) -> None:
        client = ConcreteClient(api_key="k", base_url="https://test.com")
        result = client.check_eligibility({"payer_id": "00520"})
        assert isinstance(result, ClearinghouseEligibilityResponse)
        assert result.eligible is True

    def test_check_claim_status(self) -> None:
        client = ConcreteClient(api_key="k", base_url="https://test.com")
        result = client.check_claim_status("REF-123")
        assert isinstance(result, ClaimStatusResponse)
        assert result.claim_status == "paid"

    def test_close(self) -> None:
        client = ConcreteClient(api_key="k", base_url="https://test.com")
        client.close()  # Should not raise

    def test_has_httpx_client(self) -> None:
        import httpx

        client = ConcreteClient(api_key="k", base_url="https://test.com")
        assert isinstance(client._client, httpx.Client)
        client.close()

    def test_context_manager(self) -> None:
        with ConcreteClient(api_key="k", base_url="https://test.com") as client:
            assert client.provider_name == "test"
        # After exiting, the httpx client should be closed
        assert client._client.is_closed


class TestPartialImplementation:
    """Verify ABC rejects incomplete implementations."""

    def test_missing_provider_name(self) -> None:
        class NoProvider(BaseClearinghouseClient):
            def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
                return SubmissionResult(status="ok", accepted=True)

            def check_eligibility(
                self, request: dict[str, Any]
            ) -> ClearinghouseEligibilityResponse:
                return ClearinghouseEligibilityResponse(status="ok")

            def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
                return ClaimStatusResponse(status="ok")

        with pytest.raises(TypeError):
            NoProvider(api_key="k")  # type: ignore[abstract]

    def test_missing_submit_claim(self) -> None:
        class NoSubmit(BaseClearinghouseClient):
            @property
            def provider_name(self) -> str:
                return "test"

            def check_eligibility(
                self, request: dict[str, Any]
            ) -> ClearinghouseEligibilityResponse:
                return ClearinghouseEligibilityResponse(status="ok")

            def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
                return ClaimStatusResponse(status="ok")

        with pytest.raises(TypeError):
            NoSubmit(api_key="k")  # type: ignore[abstract]


class TestImports:
    """Verify ABC importable from clearinghouse package."""

    def test_import_from_clearinghouse(self) -> None:
        from claim_validator.clearinghouse import BaseClearinghouseClient

        assert BaseClearinghouseClient is not None
