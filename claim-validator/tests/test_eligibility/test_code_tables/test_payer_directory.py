"""Tests for payer directory lookups."""

from __future__ import annotations

import json
from importlib.resources import files

from claim_validator.eligibility.code_tables.payer_directory import get_payer_directory


class TestGetPayerDirectory:
    """Tests for get_payer_directory() lookup."""

    def test_valid_payer_returns_dict(self) -> None:
        """A known payer ID returns a dict with name and type."""
        result = get_payer_directory("60054")
        assert result is not None
        assert isinstance(result, dict)
        assert "name" in result
        assert "type" in result

    def test_aetna_payer(self) -> None:
        result = get_payer_directory("60054")
        assert result is not None
        assert result["name"] == "Aetna"

    def test_medicare_part_a(self) -> None:
        result = get_payer_directory("00882")
        assert result is not None
        assert "Medicare" in result["name"]
        assert result["type"] == "government"

    def test_medicare_part_b(self) -> None:
        result = get_payer_directory("00883")
        assert result is not None
        assert "Medicare" in result["name"]
        assert result["type"] == "government"

    def test_case_insensitive_alpha_id(self) -> None:
        """Payer IDs with letters should be case-insensitive."""
        result_upper = get_payer_directory("SB580")
        result_lower = get_payer_directory("sb580")
        assert result_upper is not None
        assert result_upper == result_lower

    def test_whitespace_handling(self) -> None:
        result = get_payer_directory("  60054  ")
        assert result is not None
        assert result["name"] == "Aetna"

    def test_unknown_payer_returns_none(self) -> None:
        assert get_payer_directory("ZZZZZ") is None

    def test_empty_string_returns_none(self) -> None:
        assert get_payer_directory("") is None

    def test_all_entries_have_required_fields(self) -> None:
        """Every payer entry must have 'name' and 'type' keys."""
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        for payer_id, info in raw.items():
            assert "name" in info, f"Missing 'name' for payer {payer_id}"
            assert "type" in info, f"Missing 'type' for payer {payer_id}"

    def test_no_empty_keys_in_data(self) -> None:
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        for payer_id in raw:
            assert len(payer_id.strip()) > 0, "Empty payer ID found"

    def test_no_empty_names_in_data(self) -> None:
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        for payer_id, info in raw.items():
            assert len(info["name"].strip()) > 0, f"Empty name for payer {payer_id}"

    def test_payer_ids_are_strings(self) -> None:
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        for payer_id in raw:
            assert isinstance(payer_id, str), f"Payer ID {payer_id} is not a string"

    def test_payer_ids_are_uppercase(self) -> None:
        """All payer IDs in JSON should be stored uppercase."""
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        for payer_id in raw:
            assert payer_id == payer_id.upper(), f"Payer ID {payer_id} not uppercase"

    def test_common_payers_exist(self) -> None:
        """Major US payers should be in the directory."""
        major_payers = [
            "60054",  # Aetna
            "00882",  # Medicare Part A
            "00883",  # Medicare Part B
            "SB580",  # Anthem BCBS
            "87726",  # UnitedHealthcare
            "62308",  # Cigna
            "61101",  # Humana
        ]
        for pid in major_payers:
            result = get_payer_directory(pid)
            assert result is not None, f"Major payer {pid} not found"

    def test_valid_payer_types(self) -> None:
        """All payer types should be from the known set."""
        valid_types = {
            "commercial", "government", "workers_comp", "auto",
            "dental", "vision", "pharmacy", "behavioral_health",
            "managed_care",
        }
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        for payer_id, info in raw.items():
            assert info["type"] in valid_types, (
                f"Invalid type '{info['type']}' for payer {payer_id}"
            )

    def test_minimum_entry_count(self) -> None:
        """Directory should have substantial coverage (~3,400 entries)."""
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        assert len(raw) >= 3000, f"Only {len(raw)} entries, expected ~3,400"

    def test_returns_dict_with_string_values(self) -> None:
        result = get_payer_directory("60054")
        assert result is not None
        for key, val in result.items():
            assert isinstance(val, str), f"Value for '{key}' is not a string"

    def test_all_known_payers_round_trip(self) -> None:
        """Every payer in the JSON can be looked up successfully."""
        data_pkg = files("claim_validator.eligibility.data")
        raw = json.loads(
            data_pkg.joinpath("payer_directory.json").read_text(encoding="utf-8")
        )
        for payer_id, expected in raw.items():
            result = get_payer_directory(payer_id)
            assert result == expected, f"Round-trip failed for payer {payer_id}"
