"""Tests for AAA error parsing in parse_278_response() — Story PA-2.2."""

from __future__ import annotations

import copy
import time
from typing import Any

import pytest

from claim_validator.constants import Severity
from claim_validator.prior_auth.code_tables.aaa_reject_codes import (
    get_aaa_reject_code,
)
from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.response_parser import parse_278_response


def _make_278_with_aaa(
    action_code: str = "A3",
    aaa_errors: list[dict[str, Any]] | None = None,
    **overrides: Any,
) -> dict[str, Any]:
    """Build a raw 278 JSON dict with AAA error segments for testing."""
    base: dict[str, Any] = {
        "action_code": action_code,
        "authorization_number": None,
        "effective_date": None,
        "expiration_date": None,
        "decision_reason_code": None,
        "decision_reason_description": None,
        "service_lines": [],
        "aaa_errors": aaa_errors
        if aaa_errors is not None
        else [{"rejection_code": "57", "follow_up_code": "N"}],
    }
    base.update(overrides)
    return base


class TestAAABasicParsing:
    """AC #1: AAA error segments parsed into PriorAuthError objects."""

    def test_single_aaa_error_in_response_errors(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57", "follow_up_code": "N"}],
        )
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 1
        error = response.errors[0]
        assert error.rejection_code == "57"
        assert error.follow_up_code == "N"
        assert error.message != ""
        assert error.suggested_fix != ""

    def test_aaa_error_fields_populated(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "72", "follow_up_code": "C"}],
        )
        response, _ = parse_278_response(raw)

        error = response.errors[0]
        assert error.rejection_code == "72"
        assert error.follow_up_code == "C"
        assert error.message == "Member ID not found or incorrect format"
        assert "member id" in error.suggested_fix.lower()


class TestAAACodeMapping:
    """AC #2: Known AAA codes mapped to human-readable messages."""

    def test_code_57_message(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57"}],
        )
        response, _ = parse_278_response(raw)

        error = response.errors[0]
        assert error.message == "Patient/subscriber not found or not eligible"
        assert "member id" in error.suggested_fix.lower()

    def test_code_04_message(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "04"}],
        )
        response, _ = parse_278_response(raw)

        error = response.errors[0]
        assert error.message == "Requested service quantity exceeds allowed limits"
        assert "quantity" in error.suggested_fix.lower()

    def test_code_t4_message(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "T4"}],
        )
        response, _ = parse_278_response(raw)

        error = response.errors[0]
        assert error.message == "Required payer identification not provided"
        assert "payer" in error.suggested_fix.lower()


ALL_23_AAA_CODES = [
    "04", "15", "33", "35", "41", "42", "43", "44", "45", "46",
    "47", "48", "49", "51", "56", "57", "58", "60", "71", "72",
    "73", "79", "T4",
]


class TestAAAAllKnownCodes:
    """AC #3: All 23 known AAA codes have messages and suggested fixes."""

    @pytest.mark.parametrize("code", ALL_23_AAA_CODES)
    def test_known_code_has_message_and_fix(self, code: str) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": code}],
        )
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 1
        error = response.errors[0]
        assert error.rejection_code == code
        assert error.message != ""
        assert error.message != "Unknown AAA reject code"
        assert error.suggested_fix != ""
        assert error.suggested_fix != "Contact payer for details"

        # Verify finding is ERROR (not WARNING) for known codes
        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 1
        assert aaa_findings[0].severity == Severity.ERROR

    @pytest.mark.parametrize("code", ALL_23_AAA_CODES)
    def test_known_code_matches_code_table(self, code: str) -> None:
        code_info = get_aaa_reject_code(code)
        assert code_info is not None

        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": code}],
        )
        response, _ = parse_278_response(raw)

        error = response.errors[0]
        assert error.message == code_info["description"]
        assert error.suggested_fix == code_info["suggested_fix"]


class TestAAAUnmappedCode:
    """AC #4: Unmapped AAA codes generate WARNING finding, no exception."""

    def test_unknown_code_warning_finding(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "ZZ"}],
        )
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 1
        error = response.errors[0]
        assert error.rejection_code == "ZZ"
        assert error.message == "Unknown AAA reject code"
        assert error.suggested_fix == "Contact payer for details"

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 1
        assert aaa_findings[0].severity == Severity.WARNING

    def test_unknown_code_no_exception(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "99"}],
        )
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].message == "Unknown AAA reject code"

    def test_unknown_code_context_dict(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "XY", "follow_up_code": "R"}],
        )
        _, findings = parse_278_response(raw)

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 1
        ctx = aaa_findings[0].context
        assert ctx is not None
        assert ctx["rejection_code"] == "XY"
        assert ctx["follow_up_code"] == "R"
        assert ctx["meaning"] == "Unknown"


class TestAAAFindings:
    """AC #5: AAA_PA_REJECTION findings generated with correct context."""

    def test_finding_code_is_aaa_pa_rejection(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57", "follow_up_code": "N"}],
        )
        _, findings = parse_278_response(raw)

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 1
        f = aaa_findings[0]
        assert f.code == "AAA_PA_REJECTION"
        assert f.severity == Severity.ERROR
        assert f.field_name == "aaa_segment"

    def test_finding_context_has_required_keys(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "72", "follow_up_code": "C"}],
        )
        _, findings = parse_278_response(raw)

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        ctx = aaa_findings[0].context
        assert ctx is not None
        assert "rejection_code" in ctx
        assert "follow_up_code" in ctx
        assert "meaning" in ctx
        assert ctx["rejection_code"] == "72"
        assert ctx["follow_up_code"] == "C"
        assert ctx["meaning"] == "Invalid/Missing Subscriber ID"

    def test_finding_suggestion_matches_code_table(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "43"}],
        )
        _, findings = parse_278_response(raw)

        code_info = get_aaa_reject_code("43")
        assert code_info is not None

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert aaa_findings[0].suggestion == code_info["suggested_fix"]
        assert aaa_findings[0].message == code_info["description"]


class TestAAAMultipleErrors:
    """AC #6: Multiple AAA errors all captured."""

    def test_two_errors_both_captured(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[
                {"rejection_code": "57", "follow_up_code": "N"},
                {"rejection_code": "72", "follow_up_code": "C"},
            ],
        )
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 2
        assert response.errors[0].rejection_code == "57"
        assert response.errors[1].rejection_code == "72"

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 2

    def test_three_errors_with_mixed_known_unknown(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[
                {"rejection_code": "57"},
                {"rejection_code": "ZZ"},
                {"rejection_code": "04"},
            ],
        )
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 3
        assert response.errors[0].rejection_code == "57"
        assert response.errors[1].rejection_code == "ZZ"
        assert response.errors[2].rejection_code == "04"

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 3
        assert aaa_findings[0].severity == Severity.ERROR
        assert aaa_findings[1].severity == Severity.WARNING
        assert aaa_findings[2].severity == Severity.ERROR


class TestAAAWithHCRCode:
    """AC #7: Both HCR action code and AAA errors parsed together."""

    def test_a3_with_aaa_errors(self) -> None:
        raw = _make_278_with_aaa(
            action_code="A3",
            aaa_errors=[{"rejection_code": "57"}],
        )
        response, findings = parse_278_response(raw)

        assert response.action_code == CertificationActionCode.NOT_CERTIFIED
        assert response.is_denied is True
        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "57"

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 1

    def test_a1_approved_no_aaa_errors(self) -> None:
        raw = _make_278_with_aaa(
            action_code="A1",
            aaa_errors=[],
        )
        response, findings = parse_278_response(raw)

        assert response.is_approved is True
        assert len(response.errors) == 0
        assert len(findings) == 0

    def test_hcr_and_aaa_findings_coexist(self) -> None:
        raw = _make_278_with_aaa(
            action_code="ZZ",
            aaa_errors=[{"rejection_code": "57"}],
        )
        response, findings = parse_278_response(raw)

        assert response.action_code is None
        assert len(response.errors) == 1

        hcr_findings = [f for f in findings if f.code == "PA_UNKNOWN_ACTION_CODE"]
        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(hcr_findings) == 1
        assert len(aaa_findings) == 1


class TestAAAPerformance:
    """AC #8: parse_278_response with AAA errors completes in < 50ms."""

    def test_under_50ms_with_aaa_errors(self) -> None:
        raw = _make_278_with_aaa(
            action_code="A3",
            aaa_errors=[
                {"rejection_code": code, "follow_up_code": "N"}
                for code in ["04", "57", "72", "43", "T4"]
            ],
        )

        # Warm up code table lazy loading
        parse_278_response(raw)

        start = time.perf_counter()
        parse_278_response(raw)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"parse_278_response took {elapsed_ms:.1f}ms (> 50ms)"


class TestAAAImportUnchanged:
    """AC #9: Existing imports still work — no new public API symbols."""

    def test_import_parse_278_response_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import parse_278_response as fn

        assert callable(fn)

    def test_import_parse_278_response_from_top_level(self) -> None:
        from claim_validator import parse_278_response as fn

        assert callable(fn)


class TestAAAInputNotMutated:
    """AC #10: Raw dict with AAA errors not mutated after parsing."""

    def test_raw_dict_unchanged(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[
                {"rejection_code": "57", "follow_up_code": "N"},
                {"rejection_code": "72"},
            ],
        )
        original = copy.deepcopy(raw)

        parse_278_response(raw)

        assert raw == original

    def test_raw_response_includes_aaa_data(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57"}],
        )
        response, _ = parse_278_response(raw)

        assert response.raw_response is not None
        assert "aaa_errors" in response.raw_response
        assert response.raw_response["aaa_errors"] == [{"rejection_code": "57"}]


class TestAAAEdgeCases:
    """Edge cases for AAA error parsing."""

    def test_no_aaa_errors_key(self) -> None:
        raw = {"action_code": "A1"}
        response, _ = parse_278_response(raw)

        assert response.errors == []

    def test_empty_aaa_errors_list(self) -> None:
        raw = _make_278_with_aaa(aaa_errors=[])
        response, findings = parse_278_response(raw)

        assert response.errors == []
        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 0

    def test_none_aaa_errors(self) -> None:
        raw = {"action_code": "A3", "aaa_errors": None}
        response, _ = parse_278_response(raw)

        assert response.errors == []

    def test_non_list_aaa_errors(self) -> None:
        raw = {"action_code": "A3", "aaa_errors": "not-a-list"}
        response, _ = parse_278_response(raw)

        assert response.errors == []

    def test_non_dict_items_skipped(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=["not-a-dict", 42, None, {"rejection_code": "57"}],
        )
        response, _ = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "57"

    def test_missing_rejection_code_skipped(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[
                {"follow_up_code": "N"},
                {"rejection_code": "57"},
            ],
        )
        response, _ = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "57"

    def test_empty_rejection_code_skipped(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[
                {"rejection_code": ""},
                {"rejection_code": "  "},
                {"rejection_code": "57"},
            ],
        )
        response, _ = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "57"

    def test_follow_up_code_none_when_absent(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57"}],
        )
        response, _ = parse_278_response(raw)

        assert response.errors[0].follow_up_code is None

    def test_follow_up_code_none_for_empty_string(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57", "follow_up_code": ""}],
        )
        response, _ = parse_278_response(raw)

        assert response.errors[0].follow_up_code is None

    def test_case_insensitive_rejection_code(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "t4"}],
        )
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "T4"
        assert response.errors[0].message != "Unknown AAA reject code"

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert aaa_findings[0].severity == Severity.ERROR


class TestAAAKeyConventions:
    """Support alternate key conventions for AAA segments."""

    def test_aaa_segments_fallback_key(self) -> None:
        raw = {
            "action_code": "A3",
            "aaa_segments": [{"rejection_code": "57"}],
        }
        response, findings = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "57"

        aaa_findings = [f for f in findings if f.code == "AAA_PA_REJECTION"]
        assert len(aaa_findings) == 1

    def test_aaa_errors_takes_precedence(self) -> None:
        raw = {
            "action_code": "A3",
            "aaa_errors": [{"rejection_code": "57"}],
            "aaa_segments": [{"rejection_code": "72"}],
        }
        response, _ = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "57"


class TestAAACodeFieldConventions:
    """Support alternate field names within AAA error dicts."""

    def test_aaa03_fallback_for_rejection_code(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"aaa03": "57"}],
        )
        response, _ = parse_278_response(raw)

        assert len(response.errors) == 1
        assert response.errors[0].rejection_code == "57"

    def test_aaa04_fallback_for_follow_up_code(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57", "aaa04": "N"}],
        )
        response, _ = parse_278_response(raw)

        assert response.errors[0].follow_up_code == "N"

    def test_rejection_code_takes_precedence_over_aaa03(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57", "aaa03": "72"}],
        )
        response, _ = parse_278_response(raw)

        assert response.errors[0].rejection_code == "57"

    def test_follow_up_code_takes_precedence_over_aaa04(self) -> None:
        raw = _make_278_with_aaa(
            aaa_errors=[{"rejection_code": "57", "follow_up_code": "N", "aaa04": "C"}],
        )
        response, _ = parse_278_response(raw)

        assert response.errors[0].follow_up_code == "N"


class TestAAANoErrors:
    """Regression guard — responses without AAA segments still work."""

    def test_a1_response_no_aaa_key(self) -> None:
        raw = {
            "action_code": "A1",
            "authorization_number": "AUTH123",
            "service_lines": [],
        }
        response, findings = parse_278_response(raw)

        assert response.is_approved is True
        assert response.errors == []
        assert len(findings) == 0

    def test_a1_response_empty_aaa_list(self) -> None:
        raw = {
            "action_code": "A1",
            "authorization_number": "AUTH123",
            "aaa_errors": [],
        }
        response, findings = parse_278_response(raw)

        assert response.is_approved is True
        assert response.errors == []
        assert len(findings) == 0
