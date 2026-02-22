"""Tests for timely filing deadline lookups."""

from __future__ import annotations

from claim_validator.code_tables.timely_filing import get_filing_deadline


class TestGetFilingDeadline:
    def test_medicare_365_days(self) -> None:
        assert get_filing_deadline("MEDICARE") == 365

    def test_aetna_90_days(self) -> None:
        assert get_filing_deadline("AETNA") == 90

    def test_bcbs_180_days(self) -> None:
        assert get_filing_deadline("BCBS") == 180

    def test_case_insensitive(self) -> None:
        assert get_filing_deadline("medicare") == 365
        assert get_filing_deadline("Medicare") == 365

    def test_with_whitespace(self) -> None:
        assert get_filing_deadline("  MEDICARE  ") == 365

    def test_unknown_payer_returns_default(self) -> None:
        result = get_filing_deadline("UNKNOWN_PAYER_XYZ")
        assert result == 365  # _default

    def test_common_payers_have_deadlines(self) -> None:
        payers = ["MEDICARE", "MEDICAID", "BCBS", "UNITED", "AETNA", "CIGNA"]
        for payer in payers:
            result = get_filing_deadline(payer)
            assert result is not None, f"Expected deadline for {payer}"
            assert result > 0
