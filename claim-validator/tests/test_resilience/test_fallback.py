"""Tests for fallback routing when circuit breaker is open."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.clearinghouse.models import SubmissionResult
from claim_validator.clearinghouse.pool import ClearinghouseClientPool
from claim_validator.exceptions import ConfigurationError
from claim_validator.resilience.circuit_breaker import CircuitOpenError
from claim_validator.routing.models import PayerRoute
from claim_validator.routing.router import PayerRouter


def _make_mock_client(name: str) -> MagicMock:
    client = MagicMock(spec=BaseClearinghouseClient)
    client.provider_name = name
    return client


class TestFallbackRouting:
    """Tests for ClearinghouseClientPool fallback when circuits open."""

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_falls_back_on_circuit_open(self, mock_factory: MagicMock) -> None:
        """When primary circuit is open, uses fallback provider."""
        primary = _make_mock_client("stedi")
        primary.submit_claim.side_effect = CircuitOpenError("stedi circuit open")
        fallback = _make_mock_client("claimmd")
        expected = MagicMock(spec=SubmissionResult)
        fallback.submit_claim.return_value = expected
        mock_factory.side_effect = [primary, fallback]

        custom = {
            "TESTPAYER": [
                PayerRoute("stedi", "TP1", 1, frozenset({"837P"})),
                PayerRoute("claimmd", "TP2", 2, frozenset({"837P"})),
            ],
        }
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k1"}, "claimmd": {"account_key": "k2"}},
            router=router,
        )

        result = pool.submit_claim({"npi": "1234567893"}, "TESTPAYER")
        assert result is expected
        fallback.submit_claim.assert_called_once()

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_all_circuits_open_raises(self, mock_factory: MagicMock) -> None:
        """When all circuits open, raises ConfigurationError."""
        c1 = _make_mock_client("stedi")
        c1.submit_claim.side_effect = CircuitOpenError("open")
        c2 = _make_mock_client("claimmd")
        c2.submit_claim.side_effect = CircuitOpenError("open")
        mock_factory.side_effect = [c1, c2]

        custom = {
            "ALLDOWN": [
                PayerRoute("stedi", "A1", 1, frozenset({"837P"})),
                PayerRoute("claimmd", "A2", 2, frozenset({"837P"})),
            ],
        }
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k1"}, "claimmd": {"account_key": "k2"}},
            router=router,
        )

        with pytest.raises(ConfigurationError, match="unavailable"):
            pool.submit_claim({"npi": "1234567893"}, "ALLDOWN")

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_status_no_fallback(self, mock_factory: MagicMock) -> None:
        """Claim status always goes to primary — no fallback."""
        primary = _make_mock_client("stedi")
        primary.check_claim_status.return_value = MagicMock()
        mock_factory.return_value = primary

        custom = {
            "STATUSTEST": [
                PayerRoute("stedi", "S1", 1, frozenset({"837P"})),
                PayerRoute("claimmd", "S2", 2, frozenset({"837P"})),
            ],
        }
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k1"}, "claimmd": {"account_key": "k2"}},
            router=router,
        )

        pool.check_claim_status("REF-1", "STATUSTEST")
        primary.check_claim_status.assert_called_once_with("REF-1")

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_non_circuit_error_propagates(self, mock_factory: MagicMock) -> None:
        """Non-CircuitOpenError exceptions propagate, no fallback."""
        primary = _make_mock_client("stedi")
        primary.submit_claim.side_effect = RuntimeError("real error")
        mock_factory.return_value = primary

        custom = {
            "ERRT": [
                PayerRoute("stedi", "E1", 1, frozenset({"837P"})),
                PayerRoute("claimmd", "E2", 2, frozenset({"837P"})),
            ],
        }
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k1"}, "claimmd": {"account_key": "k2"}},
            router=router,
        )

        with pytest.raises(RuntimeError, match="real error"):
            pool.submit_claim({"npi": "1234567893"}, "ERRT")
