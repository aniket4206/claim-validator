"""Tests for payer routing code table accessor and data file."""

from __future__ import annotations

import threading

import pytest

from claim_validator.exceptions import CodeTableError
from claim_validator.routing.models import PayerRoute
from claim_validator.shared.code_tables.loader import _clear_cache
from claim_validator.shared.code_tables.payer_routing import (
    _build_routing_table,
    _clear_routing_cache,
    get_payer_routing_table,
    load_default_mapping,
)


class TestLoadDefaultMapping:
    """Tests for load_default_mapping() lazy singleton."""

    def setup_method(self) -> None:
        _clear_routing_cache()
        _clear_cache()

    def test_returns_dict(self) -> None:
        mapping = load_default_mapping()
        assert isinstance(mapping, dict)

    def test_minimum_entry_count(self) -> None:
        """Mapping should contain ~2,000 payer entries."""
        mapping = load_default_mapping()
        assert len(mapping) >= 2000, f"Only {len(mapping)} entries, expected >= 2000"

    def test_keys_are_strings(self) -> None:
        mapping = load_default_mapping()
        for key in list(mapping.keys())[:10]:
            assert isinstance(key, str)

    def test_values_are_payer_route_lists(self) -> None:
        mapping = load_default_mapping()
        for payer_id, routes in list(mapping.items())[:20]:
            assert isinstance(routes, list), f"Expected list for payer {payer_id}"
            assert len(routes) > 0, f"Empty route list for payer {payer_id}"
            for route in routes:
                assert isinstance(route, PayerRoute), (
                    f"Expected PayerRoute, got {type(route)} for payer {payer_id}"
                )

    def test_routes_sorted_by_priority(self) -> None:
        mapping = load_default_mapping()
        for payer_id, routes in mapping.items():
            priorities = [r.priority for r in routes]
            assert priorities == sorted(priorities), (
                f"Routes not sorted by priority for payer {payer_id}: {priorities}"
            )

    def test_supports_is_frozenset(self) -> None:
        mapping = load_default_mapping()
        for routes in list(mapping.values())[:20]:
            for route in routes:
                assert isinstance(route.supports, frozenset)

    def test_clearinghouse_values_are_known(self) -> None:
        """All clearinghouse names should be from the known set."""
        known = {"stedi", "claimmd", "waystar", "change", "availity"}
        mapping = load_default_mapping()
        all_clearinghouses = set()
        for routes in mapping.values():
            for route in routes:
                all_clearinghouses.add(route.clearinghouse)
        assert all_clearinghouses.issubset(known), (
            f"Unknown clearinghouses: {all_clearinghouses - known}"
        )

    def test_supports_values_are_known_types(self) -> None:
        """All transaction types should be from the known set."""
        known = {"837P", "837I", "837D", "270/271", "276/277", "278"}
        mapping = load_default_mapping()
        all_types: set[str] = set()
        for routes in mapping.values():
            for route in routes:
                all_types.update(route.supports)
        assert all_types.issubset(known), f"Unknown transaction types: {all_types - known}"

    def test_cached_same_object(self) -> None:
        """Verify singleton: same object returned on repeated calls."""
        m1 = load_default_mapping()
        m2 = load_default_mapping()
        assert m1 is m2

    def test_thread_safe_concurrent_load(self) -> None:
        """Verify double-check locking with 8 threads."""
        results: list[dict[str, list[PayerRoute]]] = []
        errors: list[Exception] = []
        mu = threading.Lock()

        def load() -> None:
            try:
                table = load_default_mapping()
                with mu:
                    results.append(table)
            except Exception as exc:
                with mu:
                    errors.append(exc)

        threads = [threading.Thread(target=load) for _ in range(8)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors, f"Thread errors: {errors}"
        assert len(results) == 8
        # All threads should get the same cached object
        assert all(r is results[0] for r in results)


class TestBuildRoutingTableErrors:
    """Tests for corrupt data handling in _build_routing_table."""

    def test_missing_clearinghouse_key_raises(self) -> None:
        raw = {"BAD1": [{"payer_id_at_clearinghouse": "X", "priority": 1, "supports": []}]}
        with pytest.raises(CodeTableError, match="Malformed.*BAD1"):
            _build_routing_table(raw)

    def test_missing_priority_key_raises(self) -> None:
        raw = {"BAD2": [{"clearinghouse": "stedi", "payer_id_at_clearinghouse": "X", "supports": []}]}
        with pytest.raises(CodeTableError, match="Malformed.*BAD2"):
            _build_routing_table(raw)

    def test_non_list_entry_raises(self) -> None:
        raw = {"BAD3": "not_a_list"}
        with pytest.raises(CodeTableError, match="Malformed.*BAD3"):
            _build_routing_table(raw)


class TestGetPayerRoutingTable:
    """Tests for get_payer_routing_table() alias."""

    def setup_method(self) -> None:
        _clear_routing_cache()
        _clear_cache()

    def test_returns_same_as_load_default_mapping(self) -> None:
        """get_payer_routing_table() is an alias for load_default_mapping()."""
        t1 = get_payer_routing_table()
        t2 = load_default_mapping()
        # Same cached object — both functions return the identical dict
        assert t1 is t2

    def test_returns_dict_of_payer_routes(self) -> None:
        table = get_payer_routing_table()
        assert isinstance(table, dict)
        assert len(table) >= 2000
