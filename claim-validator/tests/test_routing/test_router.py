"""Tests for PayerRouter."""

from __future__ import annotations

import threading

import pytest

from claim_validator.exceptions import PayerRoutingError
from claim_validator.routing.models import PayerRoute
from claim_validator.routing.router import PayerRouter


class TestPayerRouterRoute:
    """Tests for PayerRouter.route()."""

    def test_returns_payer_route(self) -> None:
        router = PayerRouter()
        result = router.route("60054")  # Aetna — should exist in default data
        assert isinstance(result, PayerRoute)

    def test_returns_highest_priority(self) -> None:
        """route() should return priority=1 route."""
        custom = {
            "TEST1": [
                PayerRoute("claimmd", "T1B", 2, frozenset({"837P"})),
                PayerRoute("stedi", "T1A", 1, frozenset({"837P"})),
            ],
        }
        router = PayerRouter(custom_mappings=custom)
        result = router.route("TEST1")
        assert result.clearinghouse == "stedi"
        assert result.priority == 1

    def test_case_insensitive(self) -> None:
        custom = {
            "UPPER": [PayerRoute("stedi", "X", 1, frozenset({"837P"}))],
        }
        router = PayerRouter(custom_mappings=custom)
        result = router.route("upper")
        assert result.clearinghouse == "stedi"

    def test_whitespace_trimmed(self) -> None:
        custom = {
            "TRIM": [PayerRoute("stedi", "X", 1, frozenset({"837P"}))],
        }
        router = PayerRouter(custom_mappings=custom)
        result = router.route("  TRIM  ")
        assert result.clearinghouse == "stedi"

    def test_unknown_payer_raises(self) -> None:
        router = PayerRouter()
        with pytest.raises(PayerRoutingError, match="No routes found"):
            router.route("ZZZZZ_NONEXISTENT")

    def test_empty_string_raises(self) -> None:
        router = PayerRouter()
        with pytest.raises(PayerRoutingError):
            router.route("")


class TestPayerRouterRouteWithFallback:
    """Tests for PayerRouter.route_with_fallback()."""

    def test_returns_list(self) -> None:
        router = PayerRouter()
        result = router.route_with_fallback("60054")
        assert isinstance(result, list)
        assert len(result) >= 1

    def test_returns_sorted_by_priority(self) -> None:
        custom = {
            "MULTI": [
                PayerRoute("waystar", "M3", 3, frozenset({"837P"})),
                PayerRoute("stedi", "M1", 1, frozenset({"837P"})),
                PayerRoute("claimmd", "M2", 2, frozenset({"837P"})),
            ],
        }
        router = PayerRouter(custom_mappings=custom)
        result = router.route_with_fallback("MULTI")
        priorities = [r.priority for r in result]
        assert priorities == sorted(priorities)

    def test_first_element_matches_route(self) -> None:
        """route_with_fallback()[0] should equal route()."""
        custom = {
            "MATCH": [
                PayerRoute("claimmd", "B", 2, frozenset({"837P"})),
                PayerRoute("stedi", "A", 1, frozenset({"837P"})),
            ],
        }
        router = PayerRouter(custom_mappings=custom)
        assert router.route("MATCH") == router.route_with_fallback("MATCH")[0]

    def test_returns_copy_not_original(self) -> None:
        """Returned list should be a copy to prevent mutation."""
        custom = {
            "COPY": [PayerRoute("stedi", "X", 1, frozenset({"837P"}))],
        }
        router = PayerRouter(custom_mappings=custom)
        result1 = router.route_with_fallback("COPY")
        result2 = router.route_with_fallback("COPY")
        assert result1 == result2
        assert result1 is not result2  # Different list objects

    def test_unknown_payer_raises(self) -> None:
        router = PayerRouter()
        with pytest.raises(PayerRoutingError, match="No routes found"):
            router.route_with_fallback("ZZZZZ_NONEXISTENT")


class TestPayerRouterCustomMappings:
    """Tests for custom mapping overrides."""

    def test_custom_overrides_default(self) -> None:
        """Custom mapping for existing payer overrides default."""
        custom_route = PayerRoute("custom_ch", "CUSTOM", 1, frozenset({"837P"}))
        router = PayerRouter(custom_mappings={"60054": [custom_route]})
        result = router.route("60054")
        assert result.clearinghouse == "custom_ch"

    def test_custom_adds_new_payer(self) -> None:
        """Custom mapping can add payers not in defaults."""
        custom_route = PayerRoute("stedi", "NEW", 1, frozenset({"837P"}))
        router = PayerRouter(custom_mappings={"NEWPAYER99": [custom_route]})
        result = router.route("NEWPAYER99")
        assert result.payer_id_at_clearinghouse == "NEW"

    def test_default_payers_still_available(self) -> None:
        """Custom mappings don't remove default payers."""
        custom_route = PayerRoute("stedi", "X", 1, frozenset({"837P"}))
        router = PayerRouter(custom_mappings={"NEWPAYER99": [custom_route]})
        # 60054 (Aetna) should still be routable
        result = router.route("60054")
        assert isinstance(result, PayerRoute)

    def test_none_custom_uses_defaults(self) -> None:
        router = PayerRouter(custom_mappings=None)
        result = router.route("60054")
        assert isinstance(result, PayerRoute)

    def test_custom_keys_normalized_to_uppercase(self) -> None:
        """Custom mappings with lowercase keys should still be found via uppercase lookup."""
        custom_route = PayerRoute("custom_ch", "LOWER", 1, frozenset({"837P"}))
        router = PayerRouter(custom_mappings={"lowercase_payer": [custom_route]})
        result = router.route("LOWERCASE_PAYER")
        assert result.clearinghouse == "custom_ch"

    def test_custom_keys_whitespace_normalized(self) -> None:
        """Custom mappings with whitespace-padded keys should be normalized."""
        custom_route = PayerRoute("stedi", "WS", 1, frozenset({"837P"}))
        router = PayerRouter(custom_mappings={"  PADDED  ": [custom_route]})
        result = router.route("PADDED")
        assert result.payer_id_at_clearinghouse == "WS"


class TestPayerRouterThreadSafety:
    """Tests for thread safety and statelessness."""

    def test_concurrent_route_calls(self) -> None:
        """8 threads routing concurrently should all succeed."""
        router = PayerRouter()
        results: list[PayerRoute] = []
        errors: list[Exception] = []
        mu = threading.Lock()

        def do_route() -> None:
            try:
                r = router.route("60054")
                with mu:
                    results.append(r)
            except Exception as exc:
                with mu:
                    errors.append(exc)

        threads = [threading.Thread(target=do_route) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(results) == 8
        # All should get equal results
        assert all(r == results[0] for r in results)

    def test_stateless_repeated_calls(self) -> None:
        """Repeated calls should return consistent results."""
        router = PayerRouter()
        r1 = router.route("60054")
        r2 = router.route("60054")
        assert r1 == r2
