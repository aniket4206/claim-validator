"""Tests for eligibility code tables manifest."""

from __future__ import annotations

import json
from importlib.resources import files


class TestManifest:
    """Tests for eligibility data manifest.json."""

    def _load_manifest(self) -> dict[str, dict[str, object]]:
        data_pkg = files("claim_validator.eligibility.data")
        return json.loads(data_pkg.joinpath("manifest.json").read_text(encoding="utf-8"))

    def test_manifest_loads_successfully(self) -> None:
        manifest = self._load_manifest()
        assert isinstance(manifest, dict)

    def test_manifest_has_payer_directory_entry(self) -> None:
        manifest = self._load_manifest()
        assert "payer_directory" in manifest

    def test_manifest_has_service_types_entry(self) -> None:
        manifest = self._load_manifest()
        assert "service_types" in manifest

    def test_payer_directory_code_count_matches(self) -> None:
        """Manifest code_count must match actual JSON entry count."""
        manifest = self._load_manifest()
        data_pkg = files("claim_validator.eligibility.data")
        actual = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        assert manifest["payer_directory"]["code_count"] == len(actual)

    def test_service_types_code_count_matches(self) -> None:
        """Manifest code_count must match actual JSON entry count."""
        manifest = self._load_manifest()
        data_pkg = files("claim_validator.eligibility.data")
        actual = json.loads(
            data_pkg.joinpath("service_types.json").read_text(encoding="utf-8")
        )
        assert manifest["service_types"]["code_count"] == len(actual)

    def test_all_entries_have_required_fields(self) -> None:
        """Each manifest entry must have code_count, effective_date, source, version."""
        manifest = self._load_manifest()
        required = {"code_count", "effective_date", "source", "version"}
        for table_name, entry in manifest.items():
            for field in required:
                assert field in entry, (
                    f"Missing '{field}' in manifest entry '{table_name}'"
                )
