"""Tests for clearinghouse client factory."""

from __future__ import annotations

import sys
import types
from typing import Any
from unittest.mock import patch

import pytest

from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.clearinghouse.factory import get_clearinghouse_client
from claim_validator.clearinghouse.models import (
    ClaimStatusResponse,
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.exceptions import ConfigurationError


# Stub providers for testing factory dispatch
class _StubStediClient(BaseClearinghouseClient):
    @property
    def provider_name(self) -> str:
        return "stedi"

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        return SubmissionResult(status="ok", accepted=True)

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        return ClearinghouseEligibilityResponse(status="ok")

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        return ClaimStatusResponse(status="ok")


class _StubClaimMDClient(BaseClearinghouseClient):
    @property
    def provider_name(self) -> str:
        return "claimmd"

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        return SubmissionResult(status="ok", accepted=True)

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        return ClearinghouseEligibilityResponse(status="ok")

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        return ClaimStatusResponse(status="ok")


class _StubWaystarClient(BaseClearinghouseClient):
    @property
    def provider_name(self) -> str:
        return "waystar"

    def submit_claim(self, claim_data: dict[str, Any]) -> SubmissionResult:
        return SubmissionResult(status="ok", accepted=True)

    def check_eligibility(
        self, request: dict[str, Any]
    ) -> ClearinghouseEligibilityResponse:
        return ClearinghouseEligibilityResponse(status="ok")

    def check_claim_status(self, claim_ref: str) -> ClaimStatusResponse:
        return ClaimStatusResponse(status="ok")


def _inject_fake_provider(module_path: str, class_name: str, stub_cls: type):
    """Inject a fake provider module into sys.modules for lazy import testing."""
    mod = types.ModuleType(module_path)
    setattr(mod, class_name, stub_cls)
    return mod


class TestGetClearinghouseClient:
    """Verify factory dispatches to correct providers."""

    def test_stedi_provider(self) -> None:
        fake_mod = _inject_fake_provider(
            "claim_validator.clearinghouse.providers.stedi",
            "StediClient",
            _StubStediClient,
        )
        with patch.dict(sys.modules, {fake_mod.__name__: fake_mod}):
            client = get_clearinghouse_client("stedi", api_key="test-key")
            assert client.provider_name == "stedi"

    def test_claimmd_provider(self) -> None:
        fake_mod = _inject_fake_provider(
            "claim_validator.clearinghouse.providers.claimmd",
            "ClaimMDClient",
            _StubClaimMDClient,
        )
        with patch.dict(sys.modules, {fake_mod.__name__: fake_mod}):
            client = get_clearinghouse_client("claimmd", api_key="test-key")
            assert client.provider_name == "claimmd"

    def test_waystar_provider(self) -> None:
        fake_mod = _inject_fake_provider(
            "claim_validator.clearinghouse.providers.waystar",
            "WaystarClient",
            _StubWaystarClient,
        )
        with patch.dict(sys.modules, {fake_mod.__name__: fake_mod}):
            client = get_clearinghouse_client("waystar", api_key="test-key", secret="s")
            assert client.provider_name == "waystar"

    def test_unknown_provider_raises(self) -> None:
        with pytest.raises(ConfigurationError, match="Unknown clearinghouse provider"):
            get_clearinghouse_client("unknown_provider", api_key="k")

    def test_case_insensitive(self) -> None:
        """Provider names should be case-insensitive."""
        with pytest.raises(ConfigurationError):
            # "UNKNOWN" should still fail regardless of case handling
            get_clearinghouse_client("UNKNOWN", api_key="k")

    def test_error_message_lists_providers(self) -> None:
        with pytest.raises(ConfigurationError, match="stedi.*claimmd.*waystar"):
            get_clearinghouse_client("invalid", api_key="k")


class TestFactoryImport:
    """Verify factory importable from clearinghouse package."""

    def test_import_from_clearinghouse(self) -> None:
        from claim_validator.clearinghouse import get_clearinghouse_client

        assert get_clearinghouse_client is not None
