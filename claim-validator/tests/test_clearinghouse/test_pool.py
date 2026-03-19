"""Tests for ClearinghouseClientPool."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from claim_validator.clearinghouse.base import BaseClearinghouseClient
from claim_validator.clearinghouse.models import (
    ClearinghouseEligibilityResponse,
    SubmissionResult,
)
from claim_validator.clearinghouse.pool import ClearinghouseClientPool
from claim_validator.exceptions import ConfigurationError
from claim_validator.routing.models import PayerRoute
from claim_validator.routing.router import PayerRouter


def _make_mock_client(name: str) -> MagicMock:
    """Create a mock clearinghouse client."""
    client = MagicMock(spec=BaseClearinghouseClient)
    client.provider_name = name
    client.submit_claim.return_value = MagicMock(spec=SubmissionResult)
    client.check_eligibility.return_value = MagicMock(spec=ClearinghouseEligibilityResponse)
    return client


class TestGetClient:
    """Tests for ClearinghouseClientPool.get_client()."""

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_lazy_instantiation(self, mock_factory: MagicMock) -> None:
        """Client should not be created at pool construction."""
        configs: dict[str, dict[str, Any]] = {
            "stedi": {"api_key": "test-key"},
        }
        _pool = ClearinghouseClientPool(configs=configs)
        mock_factory.assert_not_called()

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_creates_client_on_first_call(self, mock_factory: MagicMock) -> None:
        mock_client = _make_mock_client("stedi")
        mock_factory.return_value = mock_client

        pool = ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}})
        client = pool.get_client("stedi")

        mock_factory.assert_called_once_with("stedi", api_key="k")
        assert client is mock_client

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_caches_client(self, mock_factory: MagicMock) -> None:
        """Second call returns same object, factory called only once."""
        mock_client = _make_mock_client("stedi")
        mock_factory.return_value = mock_client

        pool = ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}})
        c1 = pool.get_client("stedi")
        c2 = pool.get_client("stedi")

        assert c1 is c2
        assert mock_factory.call_count == 1

    def test_unknown_provider_raises(self) -> None:
        pool = ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}})
        with pytest.raises(ConfigurationError, match="not configured"):
            pool.get_client("unknown_provider")

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_case_insensitive_provider(self, mock_factory: MagicMock) -> None:
        mock_factory.return_value = _make_mock_client("stedi")
        pool = ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}})
        client = pool.get_client("STEDI")
        assert client is not None


class TestSubmitClaim:
    """Tests for ClearinghouseClientPool.submit_claim()."""

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_routes_to_correct_provider(self, mock_factory: MagicMock) -> None:
        mock_client = _make_mock_client("stedi")
        mock_factory.return_value = mock_client

        custom = {"TESTPAYER": [PayerRoute("stedi", "TP", 1, frozenset({"837P"}))]}
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k"}},
            router=router,
        )

        claim = {"npi": "1234567893"}
        pool.submit_claim(claim, "TESTPAYER")

        mock_client.submit_claim.assert_called_once_with(claim)

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_returns_submission_result(self, mock_factory: MagicMock) -> None:
        mock_client = _make_mock_client("stedi")
        expected = MagicMock(spec=SubmissionResult)
        mock_client.submit_claim.return_value = expected
        mock_factory.return_value = mock_client

        custom = {"TP": [PayerRoute("stedi", "TP", 1, frozenset({"837P"}))]}
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}}, router=router)

        result = pool.submit_claim({"npi": "1234567893"}, "TP")
        assert result is expected


class TestCheckEligibility:
    """Tests for ClearinghouseClientPool.check_eligibility()."""

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_routes_to_correct_provider(self, mock_factory: MagicMock) -> None:
        mock_client = _make_mock_client("stedi")
        mock_factory.return_value = mock_client

        custom = {"EP": [PayerRoute("stedi", "EP", 1, frozenset({"270/271"}))]}
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k"}},
            router=router,
        )

        req = {"payer_id": "EP"}
        pool.check_eligibility(req, "EP")

        mock_client.check_eligibility.assert_called_once_with(req)


class TestPoolRoutingMismatch:
    """Tests for when router resolves to an unconfigured provider."""

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_submit_claim_unconfigured_provider_raises(
        self, mock_factory: MagicMock
    ) -> None:
        """Router resolves to 'change' but pool only has 'stedi'."""
        custom = {"MISMATCH": [PayerRoute("change", "M1", 1, frozenset({"837P"}))]}
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k"}},
            router=router,
        )
        with pytest.raises(ConfigurationError, match="not configured"):
            pool.submit_claim({"npi": "1234567893"}, "MISMATCH")

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_check_eligibility_unconfigured_provider_raises(
        self, mock_factory: MagicMock
    ) -> None:
        custom = {"MISMATCH": [PayerRoute("availity", "M1", 1, frozenset({"270/271"}))]}
        router = PayerRouter(custom_mappings=custom)
        pool = ClearinghouseClientPool(
            configs={"stedi": {"api_key": "k"}},
            router=router,
        )
        with pytest.raises(ConfigurationError, match="not configured"):
            pool.check_eligibility({"payer_id": "X"}, "MISMATCH")


class TestPoolThreadSafety:
    """Tests for concurrent get_client() calls."""

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_concurrent_get_client(self, mock_factory: MagicMock) -> None:
        """8 threads calling get_client() should all get the same cached instance."""
        import threading as _threading

        mock_client = _make_mock_client("stedi")
        mock_factory.return_value = mock_client

        pool = ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}})
        results: list[BaseClearinghouseClient] = []
        errors: list[Exception] = []
        mu = _threading.Lock()

        def fetch() -> None:
            try:
                c = pool.get_client("stedi")
                with mu:
                    results.append(c)
            except Exception as exc:
                with mu:
                    errors.append(exc)

        threads = [_threading.Thread(target=fetch) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(results) == 8
        assert all(r is results[0] for r in results)


class TestPoolLifecycle:
    """Tests for pool cleanup."""

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_close_cleans_up_clients(self, mock_factory: MagicMock) -> None:
        mock_c1 = _make_mock_client("stedi")
        mock_c2 = _make_mock_client("claimmd")
        mock_factory.side_effect = [mock_c1, mock_c2]

        pool = ClearinghouseClientPool(configs={
            "stedi": {"api_key": "k1"},
            "claimmd": {"account_key": "k2"},
        })
        pool.get_client("stedi")
        pool.get_client("claimmd")
        pool.close()

        mock_c1.close.assert_called_once()
        mock_c2.close.assert_called_once()

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_context_manager(self, mock_factory: MagicMock) -> None:
        mock_client = _make_mock_client("stedi")
        mock_factory.return_value = mock_client

        with ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}}) as pool:
            pool.get_client("stedi")

        mock_client.close.assert_called_once()

    @patch("claim_validator.clearinghouse.pool.get_clearinghouse_client")
    def test_close_without_clients(self, mock_factory: MagicMock) -> None:
        """Close on a pool with no instantiated clients should not error."""
        pool = ClearinghouseClientPool(configs={"stedi": {"api_key": "k"}})
        pool.close()  # Should not raise
