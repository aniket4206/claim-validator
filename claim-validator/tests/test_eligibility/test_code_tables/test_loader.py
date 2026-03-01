"""Tests for eligibility code table loader."""

from __future__ import annotations

import concurrent.futures

import pytest

from claim_validator.eligibility.code_tables import loader
from claim_validator.exceptions import CodeTableError


class TestLoadEligJson:
    """Tests for load_elig_json() lazy singleton."""

    def test_loads_valid_json_file(self) -> None:
        result = loader.load_elig_json("service_types.json")
        assert isinstance(result, dict)
        assert len(result) > 0

    def test_returns_cached_on_second_call(self) -> None:
        first = loader.load_elig_json("service_types.json")
        second = loader.load_elig_json("service_types.json")
        assert first is second

    def test_different_files_cached_independently(self) -> None:
        st = loader.load_elig_json("service_types.json")
        pd = loader.load_elig_json("payer_directory.json")
        assert st is not pd

    def test_raises_code_table_error_for_missing_file(self) -> None:
        with pytest.raises(CodeTableError, match="Failed to load eligibility code table"):
            loader.load_elig_json("nonexistent.json")

    def test_raises_code_table_error_for_invalid_json(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Invalid JSON content triggers CodeTableError through real except path."""

        class _BadResource:
            def read_text(self, encoding: str = "utf-8") -> str:
                return "{not valid json!!"

        class _FakePkg:
            def joinpath(self, name: str) -> _BadResource:
                return _BadResource()

        monkeypatch.setattr(loader, "files", lambda _pkg: _FakePkg())
        with pytest.raises(CodeTableError, match="Failed to load eligibility code table"):
            loader.load_elig_json("bad_content.json")

    def test_thread_safety_single_load(self) -> None:
        """8 concurrent loads → data loaded once (same object identity)."""
        results: list[object] = []

        def _load() -> dict[str, str]:
            return loader.load_elig_json("service_types.json")

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(_load) for _ in range(8)]
            results = [f.result() for f in futures]

        # All threads get the exact same cached dict
        for r in results:
            assert r is results[0]

    def test_cache_clearing_works(self) -> None:
        first = loader.load_elig_json("service_types.json")
        loader._tables.clear()
        second = loader.load_elig_json("service_types.json")
        # After clearing, a new dict is loaded (not the same object)
        assert first is not second
        assert first == second

    def test_strips_json_suffix_for_cache_key(self) -> None:
        loader.load_elig_json("service_types.json")
        assert "service_types" in loader._tables
        assert "service_types.json" not in loader._tables


class TestGetLock:
    """Tests for _get_lock() helper."""

    def test_returns_lock_for_table(self) -> None:
        lock = loader._get_lock("test_table")
        assert isinstance(lock, type(loader._global_lock))

    def test_same_lock_returned_for_same_table(self) -> None:
        lock1 = loader._get_lock("test_table")
        lock2 = loader._get_lock("test_table")
        assert lock1 is lock2

    def test_different_locks_for_different_tables(self) -> None:
        lock1 = loader._get_lock("table_a")
        lock2 = loader._get_lock("table_b")
        assert lock1 is not lock2
