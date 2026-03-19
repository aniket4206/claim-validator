"""Tests for payer routing models."""

from __future__ import annotations

import dataclasses

import pytest

from claim_validator.routing.models import PayerRoute


class TestPayerRoute:
    """Tests for the PayerRoute frozen dataclass."""

    def test_create_basic(self) -> None:
        route = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="AETNA",
            priority=1,
            supports=frozenset({"837P", "270/271"}),
        )
        assert route.clearinghouse == "stedi"
        assert route.payer_id_at_clearinghouse == "AETNA"
        assert route.priority == 1
        assert route.supports == frozenset({"837P", "270/271"})

    def test_frozen_immutable(self) -> None:
        route = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="AETNA",
            priority=1,
            supports=frozenset({"837P"}),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            route.clearinghouse = "other"  # type: ignore[misc]

    def test_frozen_priority_immutable(self) -> None:
        route = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="AETNA",
            priority=1,
            supports=frozenset(),
        )
        with pytest.raises(dataclasses.FrozenInstanceError):
            route.priority = 99  # type: ignore[misc]

    def test_hashable(self) -> None:
        route = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="AETNA",
            priority=1,
            supports=frozenset({"837P"}),
        )
        # Must be hashable (usable in sets and as dict keys)
        route_set = {route}
        assert route in route_set

    def test_equality_same_fields(self) -> None:
        r1 = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="X",
            priority=1,
            supports=frozenset(),
        )
        r2 = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="X",
            priority=1,
            supports=frozenset(),
        )
        assert r1 == r2

    def test_inequality_different_fields(self) -> None:
        r1 = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="X",
            priority=1,
            supports=frozenset(),
        )
        r2 = PayerRoute(
            clearinghouse="claimmd",
            payer_id_at_clearinghouse="X",
            priority=1,
            supports=frozenset(),
        )
        assert r1 != r2

    def test_supports_frozenset_type(self) -> None:
        route = PayerRoute(
            clearinghouse="change",
            payer_id_at_clearinghouse="00882",
            priority=1,
            supports=frozenset({"837P", "837I", "270/271", "276/277"}),
        )
        assert isinstance(route.supports, frozenset)
        assert "837P" in route.supports
        assert "837I" in route.supports

    def test_repr(self) -> None:
        route = PayerRoute(
            clearinghouse="stedi",
            payer_id_at_clearinghouse="AETNA",
            priority=1,
            supports=frozenset({"837P"}),
        )
        r = repr(route)
        assert "PayerRoute" in r
        assert "stedi" in r
