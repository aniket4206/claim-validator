"""Tests for code table loader mechanics."""

from __future__ import annotations

import concurrent.futures

import pytest

from claim_validator.code_tables.loader import load_compressed_json, load_json
from claim_validator.exceptions import CodeTableError


class TestLoadCompressedJson:
    def test_loads_icd10_table(self) -> None:
        table = load_compressed_json("icd10_cm.json.gz")
        assert isinstance(table, dict)
        assert len(table) > 0

    def test_returns_cached_on_second_call(self) -> None:
        table1 = load_compressed_json("icd10_cm.json.gz")
        table2 = load_compressed_json("icd10_cm.json.gz")
        assert table1 is table2

    def test_different_tables_cached_independently(self) -> None:
        icd10 = load_compressed_json("icd10_cm.json.gz")
        hcpcs = load_compressed_json("hcpcs.json.gz")
        assert icd10 is not hcpcs

    def test_nonexistent_file_raises_code_table_error(self) -> None:
        with pytest.raises(CodeTableError, match="Failed to load"):
            load_compressed_json("nonexistent.json.gz")


class TestLoadJson:
    def test_loads_timely_filing(self) -> None:
        data = load_json("timely_filing.json")
        assert isinstance(data, dict)
        assert "MEDICARE" in data

    def test_loads_manifest(self) -> None:
        data = load_json("manifest.json")
        assert "icd10_cm" in data
        assert "hcpcs" in data
        assert "taxonomy" in data
        assert "pos_codes" in data

    def test_nonexistent_file_raises_code_table_error(self) -> None:
        with pytest.raises(CodeTableError, match="Failed to load"):
            load_json("nonexistent.json")


class TestManifest:
    def test_manifest_has_required_fields(self) -> None:
        manifest = load_json("manifest.json")
        for table_name in ["icd10_cm", "hcpcs", "taxonomy", "pos_codes"]:
            entry = manifest[table_name]
            assert "version" in entry
            assert "effective_date" in entry
            assert "code_count" in entry
            assert "source" in entry

    def test_manifest_code_counts_match_tables(self) -> None:
        manifest = load_json("manifest.json")
        tables = {
            "icd10_cm": "icd10_cm.json.gz",
            "hcpcs": "hcpcs.json.gz",
            "taxonomy": "taxonomy.json.gz",
            "pos_codes": "pos_codes.json.gz",
        }
        for name, filename in tables.items():
            table = load_compressed_json(filename)
            assert manifest[name]["code_count"] == len(table), (
                f"{name}: manifest says {manifest[name]['code_count']}, "
                f"table has {len(table)}"
            )


class TestThreadSafety:
    def test_concurrent_first_load(self) -> None:
        """Multiple threads loading simultaneously — table loaded once."""
        results: list[dict[str, str]] = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [
                pool.submit(load_compressed_json, "icd10_cm.json.gz")
                for _ in range(8)
            ]
            results = [f.result() for f in futures]
        assert all(r is results[0] for r in results)

    def test_concurrent_different_tables(self) -> None:
        """Multiple threads loading different tables concurrently."""
        files = [
            "icd10_cm.json.gz",
            "hcpcs.json.gz",
            "taxonomy.json.gz",
            "pos_codes.json.gz",
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
            futures = [pool.submit(load_compressed_json, f) for f in files]
            results = [f.result() for f in futures]
        assert all(isinstance(r, dict) for r in results)
        assert all(len(r) > 0 for r in results)
