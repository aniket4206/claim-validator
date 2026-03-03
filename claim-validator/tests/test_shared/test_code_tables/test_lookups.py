"""Tests for code table lookup functions — normalization, not-found, spot checks."""

from __future__ import annotations

from claim_validator.shared.code_tables import (
    get_filing_deadline,
    lookup_aaa_reject,
    lookup_hcpcs,
    lookup_hcr_action,
    lookup_icd10,
    lookup_payer,
    lookup_pos,
    lookup_service_type,
    lookup_taxonomy,
)


class TestLookupICD10:
    """ICD-10 lookup with dot-variant normalization."""

    def test_known_code_returns_description(self) -> None:
        result = lookup_icd10("J06.9")
        assert result is not None
        assert isinstance(result, str)

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_icd10("ZZZ99.99") is None

    def test_case_insensitive(self) -> None:
        upper = lookup_icd10("J06.9")
        lower = lookup_icd10("j06.9")
        assert upper == lower

    def test_dotless_variant(self) -> None:
        with_dot = lookup_icd10("J06.9")
        without_dot = lookup_icd10("J069")
        assert with_dot == without_dot

    def test_whitespace_stripped(self) -> None:
        clean = lookup_icd10("J06.9")
        padded = lookup_icd10("  J06.9  ")
        assert clean == padded


class TestLookupHCPCS:
    """HCPCS lookup — case insensitive."""

    def test_known_code_returns_description(self) -> None:
        from claim_validator.shared.code_tables import get_hcpcs_table

        table = get_hcpcs_table()
        first_code = next(iter(table))
        assert lookup_hcpcs(first_code) is not None

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_hcpcs("ZZZZZ") is None

    def test_case_insensitive(self) -> None:
        from claim_validator.shared.code_tables import get_hcpcs_table

        table = get_hcpcs_table()
        first_code = next(iter(table))
        assert lookup_hcpcs(first_code.lower()) == lookup_hcpcs(first_code.upper())


class TestLookupTaxonomy:
    """Taxonomy lookup — case insensitive."""

    def test_known_code_returns_description(self) -> None:
        from claim_validator.shared.code_tables import get_taxonomy_table

        table = get_taxonomy_table()
        first_code = next(iter(table))
        assert lookup_taxonomy(first_code) is not None

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_taxonomy("000000000X") is None


class TestLookupPOS:
    """Place of Service lookup — no case conversion."""

    def test_known_code_returns_description(self) -> None:
        from claim_validator.shared.code_tables import get_pos_table

        table = get_pos_table()
        first_code = next(iter(table))
        assert lookup_pos(first_code) is not None

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_pos("ZZ") is None

    def test_whitespace_stripped(self) -> None:
        from claim_validator.shared.code_tables import get_pos_table

        table = get_pos_table()
        first_code = next(iter(table))
        assert lookup_pos(f"  {first_code}  ") == lookup_pos(first_code)


class TestLookupPayer:
    """Payer directory lookup — returns dict with name, type."""

    def test_known_payer_returns_dict(self) -> None:
        from claim_validator.shared.code_tables import get_payer_directory_table

        table = get_payer_directory_table()
        first_id = next(iter(table))
        result = lookup_payer(first_id)
        assert result is not None
        assert "name" in result
        assert "type" in result

    def test_unknown_payer_returns_none(self) -> None:
        assert lookup_payer("NONEXISTENT_PAYER_99999") is None

    def test_case_insensitive(self) -> None:
        from claim_validator.shared.code_tables import get_payer_directory_table

        table = get_payer_directory_table()
        first_id = next(iter(table))
        assert lookup_payer(first_id.lower()) == lookup_payer(first_id.upper())


class TestLookupServiceType:
    """Service type lookup — case insensitive."""

    def test_known_code_returns_description(self) -> None:
        result = lookup_service_type("1")
        assert result is not None

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_service_type("ZZZZ") is None


class TestLookupHCRAction:
    """HCR action code lookup — returns dict with description, category."""

    def test_known_code_returns_dict(self) -> None:
        from claim_validator.shared.code_tables import get_hcr_action_codes_table

        table = get_hcr_action_codes_table()
        first_code = next(iter(table))
        result = lookup_hcr_action(first_code)
        assert result is not None
        assert "description" in result

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_hcr_action("ZZ") is None


class TestLookupAAAReject:
    """AAA reject code lookup — returns dict with meaning, description."""

    def test_known_code_returns_dict(self) -> None:
        from claim_validator.shared.code_tables import get_aaa_reject_codes_table

        table = get_aaa_reject_codes_table()
        first_code = next(iter(table))
        result = lookup_aaa_reject(first_code)
        assert result is not None
        assert "meaning" in result

    def test_unknown_code_returns_none(self) -> None:
        assert lookup_aaa_reject("ZZ") is None


class TestGetFilingDeadline:
    """Timely filing deadline lookup with _default fallback."""

    def test_known_payer_returns_int(self) -> None:
        from claim_validator.shared.code_tables import get_timely_filing_table

        table = get_timely_filing_table()
        # Find a non-_default key
        payer_id = next(k for k in table if k != "_default")
        result = get_filing_deadline(payer_id)
        assert isinstance(result, int)

    def test_unknown_payer_returns_default(self) -> None:
        result = get_filing_deadline("UNKNOWN_PAYER_XYZ")
        # Should return _default value (365)
        assert result is not None
        assert isinstance(result, int)

    def test_case_insensitive(self) -> None:
        from claim_validator.shared.code_tables import get_timely_filing_table

        table = get_timely_filing_table()
        payer_id = next(k for k in table if k != "_default")
        assert get_filing_deadline(payer_id.lower()) == get_filing_deadline(payer_id.upper())
