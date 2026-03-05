"""Tests for unified code table loader — caching, thread safety, error handling."""

from __future__ import annotations

import threading

import pytest

from claim_validator.exceptions import CodeTableError
from claim_validator.shared.code_tables.loader import (
    _clear_cache,
    load_compressed_json,
    load_json,
)


class TestLoadCompressedJson:
    """Tests for load_compressed_json() lazy singleton."""

    def setup_method(self) -> None:
        _clear_cache()

    def test_returns_dict(self) -> None:
        table = load_compressed_json("icd10_cm.json.gz")
        assert isinstance(table, dict)
        assert len(table) > 0

    def test_cached_same_object(self) -> None:
        t1 = load_compressed_json("icd10_cm.json.gz")
        t2 = load_compressed_json("icd10_cm.json.gz")
        assert t1 is t2

    def test_different_tables_different_objects(self) -> None:
        t1 = load_compressed_json("icd10_cm.json.gz")
        t2 = load_compressed_json("hcpcs.json.gz")
        assert t1 is not t2

    def test_missing_file_raises_code_table_error(self) -> None:
        with pytest.raises(CodeTableError, match="no_such_file"):
            load_compressed_json("no_such_file.json.gz")

    def test_thread_safe_concurrent_load(self) -> None:
        results: list[dict[str, str]] = []
        errors: list[Exception] = []
        mu = threading.Lock()

        def load() -> None:
            try:
                table = load_compressed_json("taxonomy.json.gz")
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

        assert not errors
        assert len(results) == 8
        # All threads should get the same cached object
        assert all(r is results[0] for r in results)


class TestLoadJson:
    """Tests for load_json() lazy singleton."""

    def setup_method(self) -> None:
        _clear_cache()

    def test_returns_data(self) -> None:
        table = load_json("timely_filing.json")
        assert isinstance(table, dict)
        assert len(table) > 0

    def test_cached_same_object(self) -> None:
        t1 = load_json("payer_directory.json")
        t2 = load_json("payer_directory.json")
        assert t1 is t2

    def test_missing_file_raises_code_table_error(self) -> None:
        with pytest.raises(CodeTableError, match="missing"):
            load_json("missing.json")

    def test_thread_safe_concurrent_load(self) -> None:
        results: list[object] = []
        errors: list[Exception] = []
        mu = threading.Lock()

        def load() -> None:
            try:
                table = load_json("service_types.json")
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

        assert not errors
        assert len(results) == 8
        assert all(r is results[0] for r in results)
