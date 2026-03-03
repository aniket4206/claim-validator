"""Tests for code table accessor functions — verify non-empty dicts with correct types."""

from __future__ import annotations

from claim_validator.shared.code_tables import (
    get_aaa_reject_codes_table,
    get_hcpcs_table,
    get_hcr_action_codes_table,
    get_icd10_table,
    get_payer_directory_table,
    get_pos_table,
    get_service_types_table,
    get_taxonomy_table,
    get_timely_filing_table,
)


class TestCompressedTableAccessors:
    """Compressed .json.gz table accessors."""

    def test_icd10_table_non_empty(self) -> None:
        table = get_icd10_table()
        assert isinstance(table, dict)
        assert len(table) >= 100

    def test_hcpcs_table_non_empty(self) -> None:
        table = get_hcpcs_table()
        assert isinstance(table, dict)
        assert len(table) >= 100

    def test_taxonomy_table_non_empty(self) -> None:
        table = get_taxonomy_table()
        assert isinstance(table, dict)
        assert len(table) >= 50

    def test_pos_table_non_empty(self) -> None:
        table = get_pos_table()
        assert isinstance(table, dict)
        assert len(table) >= 40

    def test_compressed_tables_have_string_values(self) -> None:
        for table in [get_icd10_table(), get_hcpcs_table(), get_taxonomy_table(), get_pos_table()]:
            key = next(iter(table))
            assert isinstance(key, str)
            assert isinstance(table[key], str)


class TestPlainJsonTableAccessors:
    """Plain .json table accessors."""

    def test_payer_directory_non_empty(self) -> None:
        table = get_payer_directory_table()
        assert isinstance(table, dict)
        assert len(table) >= 3000

    def test_service_types_non_empty(self) -> None:
        table = get_service_types_table()
        assert isinstance(table, dict)
        assert len(table) >= 100

    def test_timely_filing_non_empty(self) -> None:
        table = get_timely_filing_table()
        assert isinstance(table, dict)
        assert len(table) >= 5

    def test_hcr_action_codes_non_empty(self) -> None:
        table = get_hcr_action_codes_table()
        assert isinstance(table, dict)
        assert len(table) >= 5

    def test_aaa_reject_codes_non_empty(self) -> None:
        table = get_aaa_reject_codes_table()
        assert isinstance(table, dict)
        assert len(table) >= 20

    def test_payer_directory_entry_has_name_type(self) -> None:
        table = get_payer_directory_table()
        key = next(iter(table))
        entry = table[key]
        assert "name" in entry
        assert "type" in entry

    def test_hcr_action_entry_has_expected_keys(self) -> None:
        table = get_hcr_action_codes_table()
        key = next(iter(table))
        entry = table[key]
        assert "description" in entry
        assert "category" in entry
        assert "suggested_action" in entry

    def test_aaa_reject_entry_has_expected_keys(self) -> None:
        table = get_aaa_reject_codes_table()
        key = next(iter(table))
        entry = table[key]
        assert "meaning" in entry
        assert "description" in entry
        assert "suggested_fix" in entry
