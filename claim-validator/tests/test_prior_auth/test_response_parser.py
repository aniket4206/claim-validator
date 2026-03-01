"""Tests for parse_278_response() — 278 response parser."""

from __future__ import annotations

import copy
import time
from typing import Any

import pytest

from claim_validator.constants import Severity
from claim_validator.prior_auth.constants import CertificationActionCode
from claim_validator.prior_auth.response_parser import parse_278_response


def _make_278_response(
    action_code: str = "A1",
    **overrides: Any,
) -> dict[str, Any]:
    """Build a realistic raw 278 JSON dict for testing."""
    base: dict[str, Any] = {
        "action_code": action_code,
        "authorization_number": "AUTH123456",
        "effective_date": "2026-03-01",
        "expiration_date": "2026-06-01",
        "decision_reason_code": None,
        "decision_reason_description": None,
        "service_lines": [
            {
                "cpt_code": "99213",
                "action_code": action_code,
                "authorization_number": "AUTH123456-L1",
                "approved_quantity": 4,
                "denied_reason": None,
            },
        ],
    }
    base.update(overrides)
    return base


class TestParseApproved:
    """AC #1: A1 approved response parsing."""

    def test_a1_returns_is_approved_true(self) -> None:
        raw = _make_278_response(action_code="A1")
        response, findings = parse_278_response(raw)

        assert response.is_approved is True
        assert response.is_denied is False
        assert response.is_pended is False
        assert response.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert len(findings) == 0

    def test_a1_extracts_authorization_number(self) -> None:
        raw = _make_278_response(
            action_code="A1",
            authorization_number="AUTH-99999",
        )
        response, _ = parse_278_response(raw)

        assert response.authorization_number == "AUTH-99999"

    def test_a1_extracts_dates(self) -> None:
        raw = _make_278_response(
            action_code="A1",
            effective_date="2026-03-01",
            expiration_date="2026-06-01",
        )
        response, _ = parse_278_response(raw)

        assert response.effective_date is not None
        assert response.effective_date.isoformat() == "2026-03-01"
        assert response.expiration_date is not None
        assert response.expiration_date.isoformat() == "2026-06-01"


class TestParseDenied:
    """AC #2: A3 denied response parsing."""

    def test_a3_returns_is_denied_true(self) -> None:
        raw = _make_278_response(
            action_code="A3",
            decision_reason_code="01",
            decision_reason_description="Additional clinical info required",
        )
        response, findings = parse_278_response(raw)

        assert response.is_denied is True
        assert response.is_approved is False
        assert response.action_code == CertificationActionCode.NOT_CERTIFIED
        assert len(findings) == 0

    def test_a3_extracts_reason(self) -> None:
        raw = _make_278_response(
            action_code="A3",
            decision_reason_code="01",
            decision_reason_description="Additional clinical info required",
        )
        response, _ = parse_278_response(raw)

        assert response.decision_reason_code == "01"
        assert response.decision_reason_description == "Additional clinical info required"


class TestParsePended:
    """AC #3: A4 pended response parsing."""

    def test_a4_returns_is_pended_true(self) -> None:
        raw = _make_278_response(action_code="A4")
        response, findings = parse_278_response(raw)

        assert response.is_pended is True
        assert response.is_approved is False
        assert response.is_denied is False
        assert response.action_code == CertificationActionCode.PENDED
        assert len(findings) == 0


class TestParsePartial:
    """AC #4: A2 partial approval with mixed service line decisions."""

    def test_a2_with_mixed_service_lines(self) -> None:
        raw = _make_278_response(
            action_code="A2",
            service_lines=[
                {
                    "cpt_code": "99213",
                    "action_code": "A1",
                    "authorization_number": "AUTH-L1",
                    "approved_quantity": 4,
                    "denied_reason": None,
                },
                {
                    "cpt_code": "99214",
                    "action_code": "A3",
                    "authorization_number": None,
                    "approved_quantity": None,
                    "denied_reason": "Not medically necessary",
                },
            ],
        )
        response, findings = parse_278_response(raw)

        assert response.action_code == CertificationActionCode.CERTIFIED_PARTIAL
        assert len(response.service_line_decisions) == 2
        assert len(findings) == 0

        approved_line = response.service_line_decisions[0]
        assert approved_line.cpt_code == "99213"
        assert approved_line.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert approved_line.authorization_number == "AUTH-L1"
        assert approved_line.approved_quantity == 4

        denied_line = response.service_line_decisions[1]
        assert denied_line.cpt_code == "99214"
        assert denied_line.action_code == CertificationActionCode.NOT_CERTIFIED
        assert denied_line.denied_reason == "Not medically necessary"


class TestServiceLineDecisions:
    """AC #5: ServiceLineDecision field extraction."""

    def test_all_fields_populated(self) -> None:
        raw = _make_278_response(
            service_lines=[
                {
                    "cpt_code": "99213",
                    "action_code": "A1",
                    "authorization_number": "AUTH-L1",
                    "approved_quantity": 8,
                    "denied_reason": None,
                },
            ],
        )
        response, _ = parse_278_response(raw)

        assert len(response.service_line_decisions) == 1
        line = response.service_line_decisions[0]
        assert line.cpt_code == "99213"
        assert line.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert line.authorization_number == "AUTH-L1"
        assert line.approved_quantity == 8
        assert line.denied_reason is None

    def test_empty_service_lines(self) -> None:
        raw = _make_278_response(service_lines=[])
        response, _ = parse_278_response(raw)

        assert response.service_line_decisions == []

    def test_no_service_lines_key(self) -> None:
        raw = {"action_code": "A1"}
        response, _ = parse_278_response(raw)

        assert response.service_line_decisions == []


class TestAllSevenHCRCodes:
    """AC #6: Parametrized test for all 7 HCR action codes."""

    @pytest.mark.parametrize(
        ("code", "expected_enum"),
        [
            ("A1", CertificationActionCode.CERTIFIED_IN_TOTAL),
            ("A2", CertificationActionCode.CERTIFIED_PARTIAL),
            ("A3", CertificationActionCode.NOT_CERTIFIED),
            ("A4", CertificationActionCode.PENDED),
            ("A6", CertificationActionCode.MODIFIED),
            ("CT", CertificationActionCode.CONTACT_PAYER),
            ("NA", CertificationActionCode.NO_ACTION_REQUIRED),
        ],
    )
    def test_maps_to_correct_enum(
        self,
        code: str,
        expected_enum: CertificationActionCode,
    ) -> None:
        raw = _make_278_response(action_code=code)
        response, findings = parse_278_response(raw)

        assert response.action_code == expected_enum
        assert len(findings) == 0


class TestConvenienceProperties:
    """AC #6: Convenience properties return correct True values."""

    def test_a1_is_approved(self) -> None:
        raw = _make_278_response(action_code="A1")
        response, _ = parse_278_response(raw)
        assert response.is_approved is True
        assert response.is_denied is False
        assert response.is_pended is False

    def test_a3_is_denied(self) -> None:
        raw = _make_278_response(action_code="A3")
        response, _ = parse_278_response(raw)
        assert response.is_approved is False
        assert response.is_denied is True
        assert response.is_pended is False

    def test_a4_is_pended(self) -> None:
        raw = _make_278_response(action_code="A4")
        response, _ = parse_278_response(raw)
        assert response.is_approved is False
        assert response.is_denied is False
        assert response.is_pended is True

    def test_a2_none_of_three(self) -> None:
        raw = _make_278_response(action_code="A2")
        response, _ = parse_278_response(raw)
        assert response.is_approved is False
        assert response.is_denied is False
        assert response.is_pended is False


class TestMissingFields:
    """AC #7: Missing fields return None, no exceptions."""

    def test_minimal_dict(self) -> None:
        raw: dict[str, object] = {"action_code": "A1"}
        response, findings = parse_278_response(raw)

        assert response.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert response.authorization_number is None
        assert response.effective_date is None
        assert response.expiration_date is None
        assert response.decision_reason_code is None
        assert response.decision_reason_description is None
        assert response.service_line_decisions == []
        assert len(findings) == 0

    def test_empty_dict(self) -> None:
        raw: dict[str, object] = {}
        response, findings = parse_278_response(raw)

        assert response.action_code is None
        assert response.authorization_number is None
        assert response.effective_date is None
        assert response.expiration_date is None
        assert response.service_line_decisions == []
        assert len(findings) == 0

    def test_none_values(self) -> None:
        raw = {
            "action_code": None,
            "authorization_number": None,
            "effective_date": None,
            "expiration_date": None,
            "service_lines": None,
        }
        response, findings = parse_278_response(raw)

        assert response.action_code is None
        assert response.authorization_number is None
        assert response.effective_date is None
        assert response.service_line_decisions == []
        assert len(findings) == 0


class TestExtraFields:
    """AC #7: Unexpected fields are silently ignored."""

    def test_extra_keys_ignored(self) -> None:
        raw = _make_278_response(
            action_code="A1",
            payer_name="Acme Insurance",
            internal_tracking_id="TRK-999",
            some_future_field=42,
        )
        response, findings = parse_278_response(raw)

        assert response.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert len(findings) == 0


class TestUnmappedActionCode:
    """AC #8: Unmapped HCR code generates WARNING finding, no exception."""

    def test_unknown_code_warning(self) -> None:
        raw = _make_278_response(action_code="ZZ", service_lines=[])
        response, findings = parse_278_response(raw)

        assert response.action_code is None
        assert len(findings) == 1
        assert findings[0].code == "PA_UNKNOWN_ACTION_CODE"
        assert findings[0].severity == Severity.WARNING
        assert findings[0].field_name == "action_code"
        assert findings[0].context is not None
        assert findings[0].context["raw_code"] == "ZZ"

    def test_unknown_code_no_exception(self) -> None:
        raw = _make_278_response(action_code="XX", service_lines=[])
        response, findings = parse_278_response(raw)

        assert response.action_code is None
        assert len(findings) == 1

    def test_unknown_service_line_code(self) -> None:
        raw = _make_278_response(
            action_code="A2",
            service_lines=[
                {"cpt_code": "99213", "action_code": "ZZ"},
            ],
        )
        response, findings = parse_278_response(raw)

        # One finding for the service line's unknown code
        assert len(findings) == 1
        assert findings[0].code == "PA_UNKNOWN_ACTION_CODE"
        assert findings[0].context is not None
        assert findings[0].context["raw_code"] == "ZZ"
        assert response.service_line_decisions[0].action_code is None

    def test_lowercase_code_normalized(self) -> None:
        raw = _make_278_response(action_code="a1")
        response, findings = parse_278_response(raw)

        assert response.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert len(findings) == 0


class TestRawResponsePreserved:
    """AC #9: raw_response contains the complete unmodified 278 JSON dict."""

    def test_raw_response_matches_input(self) -> None:
        raw = _make_278_response(action_code="A1")
        response, _ = parse_278_response(raw)

        assert response.raw_response is not None
        assert response.raw_response == raw

    def test_raw_response_is_deep_copy(self) -> None:
        raw = _make_278_response(action_code="A1")
        response, _ = parse_278_response(raw)

        assert response.raw_response is not raw
        assert response.raw_response is not None
        assert response.raw_response["service_lines"] is not raw["service_lines"]


class TestInputDictUnmodified:
    """AC #10: Original raw dict is unchanged after parsing."""

    def test_input_dict_not_mutated(self) -> None:
        raw = _make_278_response(action_code="A1")
        original = copy.deepcopy(raw)

        parse_278_response(raw)

        assert raw == original

    def test_nested_service_lines_not_mutated(self) -> None:
        raw = _make_278_response(
            action_code="A2",
            service_lines=[
                {"cpt_code": "99213", "action_code": "A1", "approved_quantity": 4},
                {"cpt_code": "99214", "action_code": "A3", "denied_reason": "Denied"},
            ],
        )
        original = copy.deepcopy(raw)

        parse_278_response(raw)

        assert raw == original


class TestPerformance:
    """AC #11: parse_278_response completes in under 50ms."""

    def test_under_50ms(self) -> None:
        raw = _make_278_response(
            action_code="A2",
            service_lines=[
                {
                    "cpt_code": f"9921{i}",
                    "action_code": "A1",
                    "authorization_number": f"AUTH-L{i}",
                    "approved_quantity": i + 1,
                    "denied_reason": None,
                }
                for i in range(10)
            ],
        )

        start = time.perf_counter()
        parse_278_response(raw)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert elapsed_ms < 50, f"parse_278_response took {elapsed_ms:.1f}ms (> 50ms)"


class TestHCR01KeyConvention:
    """Support alternate key convention 'hcr01' alongside 'action_code'."""

    def test_hcr01_key(self) -> None:
        raw = {
            "hcr01": "A1",
            "authorization_number": "AUTH-HCR",
        }
        response, findings = parse_278_response(raw)

        assert response.action_code == CertificationActionCode.CERTIFIED_IN_TOTAL
        assert response.authorization_number == "AUTH-HCR"
        assert len(findings) == 0

    def test_action_code_takes_precedence(self) -> None:
        raw = {
            "action_code": "A3",
            "hcr01": "A1",
        }
        response, _ = parse_278_response(raw)

        assert response.action_code == CertificationActionCode.NOT_CERTIFIED


class TestDateParsing:
    """Edge cases for date parsing."""

    def test_invalid_date_string(self) -> None:
        raw = _make_278_response(
            effective_date="not-a-date",
            expiration_date="2026-13-99",
        )
        response, _ = parse_278_response(raw)

        assert response.effective_date is None
        assert response.expiration_date is None

    def test_date_object_passthrough(self) -> None:
        from datetime import date as d

        raw = _make_278_response(
            effective_date=d(2026, 3, 1),
            expiration_date=d(2026, 6, 1),
        )
        response, _ = parse_278_response(raw)

        assert response.effective_date == d(2026, 3, 1)
        assert response.expiration_date == d(2026, 6, 1)


class TestServiceLineEdgeCases:
    """Edge cases for service line parsing."""

    def test_non_dict_items_skipped(self) -> None:
        raw = _make_278_response(
            service_lines=["not-a-dict", 42, None],
        )
        response, _ = parse_278_response(raw)

        assert response.service_line_decisions == []

    def test_non_list_service_lines(self) -> None:
        raw = _make_278_response(service_lines="not-a-list")
        response, _ = parse_278_response(raw)

        assert response.service_line_decisions == []

    def test_invalid_quantity_returns_none(self) -> None:
        raw = _make_278_response(
            service_lines=[
                {"cpt_code": "99213", "action_code": "A1", "approved_quantity": "abc"},
            ],
        )
        response, _ = parse_278_response(raw)

        assert response.service_line_decisions[0].approved_quantity is None
