"""Tests for PA code table loader mechanics and thread safety."""

from __future__ import annotations

import concurrent.futures
import time
from typing import Any

import pytest

from claim_validator.exceptions import CodeTableError
from claim_validator.prior_auth.code_tables.loader import load_pa_json


class TestLoadPaJson:
    """Tests for the lazy singleton loader."""

    def test_load_hcr_action_codes(self) -> None:
        table = load_pa_json("hcr_action_codes.json")
        assert isinstance(table, dict)
        assert len(table) > 0

    def test_load_aaa_reject_codes(self) -> None:
        table = load_pa_json("aaa_reject_codes.json")
        assert isinstance(table, dict)
        assert len(table) > 0

    def test_load_service_types(self) -> None:
        table = load_pa_json("service_types.json")
        assert isinstance(table, dict)
        assert len(table) > 0

    def test_cached_returns_same_object(self) -> None:
        """Subsequent calls return the same dict object (identity check)."""
        first = load_pa_json("hcr_action_codes.json")
        second = load_pa_json("hcr_action_codes.json")
        assert first is second

    def test_different_tables_return_different_objects(self) -> None:
        hcr = load_pa_json("hcr_action_codes.json")
        aaa = load_pa_json("aaa_reject_codes.json")
        assert hcr is not aaa

    def test_nonexistent_file_raises_code_table_error(self) -> None:
        with pytest.raises(CodeTableError, match="Failed to load PA code table"):
            load_pa_json("nonexistent.json")

    def test_load_manifest(self) -> None:
        manifest = load_pa_json("manifest.json")
        assert isinstance(manifest, dict)
        assert "hcr_action_codes" in manifest
        assert "aaa_reject_codes" in manifest
        assert "service_types" in manifest


class TestManifestValidation:
    """Validate manifest code counts match actual table sizes."""

    def test_hcr_action_codes_count_matches(self) -> None:
        manifest = load_pa_json("manifest.json")
        table = load_pa_json("hcr_action_codes.json")
        assert len(table) == manifest["hcr_action_codes"]["code_count"]

    def test_aaa_reject_codes_count_matches(self) -> None:
        manifest = load_pa_json("manifest.json")
        table = load_pa_json("aaa_reject_codes.json")
        assert len(table) == manifest["aaa_reject_codes"]["code_count"]

    def test_service_types_count_matches(self) -> None:
        manifest = load_pa_json("manifest.json")
        table = load_pa_json("service_types.json")
        assert len(table) == manifest["service_types"]["code_count"]


class TestThreadSafety:
    """Verify thread-safe loading under concurrent access."""

    def test_concurrent_first_load_same_table(self) -> None:
        """Multiple threads loading simultaneously — data loaded once."""
        results: list[Any] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(load_pa_json, "hcr_action_codes.json")
                for _ in range(8)
            ]
            results = [f.result() for f in futures]
        assert all(r is results[0] for r in results)

    def test_concurrent_different_tables(self) -> None:
        """Multiple threads loading different tables concurrently."""
        filenames = [
            "hcr_action_codes.json",
            "aaa_reject_codes.json",
            "service_types.json",
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
            futures = [pool.submit(load_pa_json, f) for f in filenames]
            results = [f.result() for f in futures]
        assert all(isinstance(r, dict) for r in results)
        assert all(len(r) > 0 for r in results)


class TestPerformance:
    """AC8: First load < 500ms, subsequent lookups < 1ms."""

    def test_first_load_under_500ms(self) -> None:
        start = time.perf_counter()
        load_pa_json("hcr_action_codes.json")
        load_pa_json("aaa_reject_codes.json")
        load_pa_json("service_types.json")
        elapsed_ms = (time.perf_counter() - start) * 1000
        assert elapsed_ms < 500, f"First load took {elapsed_ms:.1f}ms (limit: 500ms)"

    def test_cached_lookup_under_1ms(self) -> None:
        # Prime the cache.
        load_pa_json("hcr_action_codes.json")
        # Measure cached lookup.
        start = time.perf_counter()
        for _ in range(100):
            load_pa_json("hcr_action_codes.json")
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100
        assert elapsed_ms < 1, f"Cached lookup took {elapsed_ms:.3f}ms (limit: 1ms)"


class TestPackageReExports:
    """Verify code_tables/__init__.py re-exports all public functions."""

    def test_import_get_hcr_action_code(self) -> None:
        from claim_validator.prior_auth.code_tables import get_hcr_action_code

        assert callable(get_hcr_action_code)

    def test_import_get_aaa_reject_code(self) -> None:
        from claim_validator.prior_auth.code_tables import get_aaa_reject_code

        assert callable(get_aaa_reject_code)

    def test_import_get_pa_service_type(self) -> None:
        from claim_validator.prior_auth.code_tables import get_pa_service_type

        assert callable(get_pa_service_type)

    def test_all_exports_listed(self) -> None:
        import claim_validator.prior_auth.code_tables as ct

        assert set(ct.__all__) == {
            "get_aaa_reject_code",
            "get_hcr_action_code",
            "get_pa_service_type",
        }
