"""Tests for ClaimMD XML response parsing.

Covers error XML, eligibility XML, and edge cases in _parse_xml_response
and _handle_response XML fallback.
"""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from claim_validator.clearinghouse.exceptions import (
    ClearinghouseValidationError,
)
from claim_validator.clearinghouse.models import (
    ClearinghouseEligibilityResponse,
)
from claim_validator.clearinghouse.providers.claimmd import (
    DEFAULT_BASE_URL,
    ClaimMDClient,
)


def _make_client(handler: Any) -> ClaimMDClient:
    transport = httpx.MockTransport(handler)
    client = ClaimMDClient(account_key="test-key")
    client._client.close()
    client._client = httpx.Client(transport=transport, base_url=DEFAULT_BASE_URL)
    return client


class TestParseXmlErrorResponse:
    """Test XML error response parsing."""

    def test_single_error_parsed(self) -> None:
        xml = '<result><error error_code="430B" error_mesg="Tax ID invalid." /></result>'
        result = ClaimMDClient._parse_xml_response(xml)
        assert result["status"] == "error"
        assert "430B" in result["message"]
        assert "Tax ID invalid." in result["message"]
        assert len(result["errors"]) == 1

    def test_multiple_errors_parsed(self) -> None:
        xml = (
            '<result>'
            '<error error_code="100" error_mesg="First error" />'
            '<error error_code="200" error_mesg="Second error" />'
            '</result>'
        )
        result = ClaimMDClient._parse_xml_response(xml)
        assert result["status"] == "error"
        assert len(result["errors"]) == 2
        assert "100: First error" in result["errors"]
        assert "200: Second error" in result["errors"]

    def test_error_message_joined_with_semicolon(self) -> None:
        xml = (
            '<result>'
            '<error error_code="A" error_mesg="msg1" />'
            '<error error_code="B" error_mesg="msg2" />'
            '</result>'
        )
        result = ClaimMDClient._parse_xml_response(xml)
        assert "; " in result["message"]

    def test_raw_xml_preserved(self) -> None:
        xml = '<result><error error_code="99" error_mesg="test" /></result>'
        result = ClaimMDClient._parse_xml_response(xml)
        assert result["raw_xml"] == xml

    def test_unknown_xml_returns_unknown_status(self) -> None:
        xml = "<result><something>data</something></result>"
        result = ClaimMDClient._parse_xml_response(xml)
        assert result["status"] == "unknown"
        assert result["raw_xml"] == xml


class TestParseXmlEligibilityResponse:
    """Test XML eligibility response parsing."""

    def test_active_coverage_detected(self) -> None:
        xml = (
            '<result>'
            '<elig eligid="12345" group_number="GRP1" plan_number="PLN1" '
            'plan_begin_date="20260101-20261231" ins_number="SUB123" '
            'ins_dob="19800115" ins_sex="M">'
            '<benefit benefit_coverage_code="1" benefit_description="Active" />'
            '</elig>'
            '</result>'
        )
        result = ClaimMDClient._parse_xml_response(xml)
        assert result["status"] == "active"
        assert result["responseID"] == "12345"
        assert result["plan"]["group_number"] == "GRP1"
        assert result["plan"]["plan_number"] == "PLN1"
        assert result["subscriber"]["ins_number"] == "SUB123"

    def test_inactive_coverage_detected(self) -> None:
        xml = (
            '<result>'
            '<elig eligid="99" ins_number="X">'
            '<benefit benefit_coverage_code="6" />'
            '</elig>'
            '</result>'
        )
        result = ClaimMDClient._parse_xml_response(xml)
        assert result["status"] == "inactive"

    def test_eligibility_parsed_into_response_model(self) -> None:
        """Verify XML eligibility flows through to ClearinghouseEligibilityResponse."""
        xml = (
            '<result>'
            '<elig eligid="777" group_number="G1" plan_number="P1" '
            'plan_begin_date="20260101" ins_number="S1" ins_dob="19900101" ins_sex="F">'
            '<benefit benefit_coverage_code="1" />'
            '</elig>'
            '</result>'
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, text=xml,
                headers={"content-type": "text/xml; charset=ISO-8859-1"},
            )

        client = _make_client(handler)
        result = client.check_eligibility({"payer_id": "60054", "npi": "123", "tax_id": "999"})

        assert isinstance(result, ClearinghouseEligibilityResponse)
        assert result.status == "active"
        assert result.eligible is True
        assert result.reference_id == "777"
        assert result.plan_info["group_number"] == "G1"


class TestHandleResponseXmlFallback:
    """Test that _handle_response handles XML content-type."""

    def test_xml_content_type_triggers_xml_parser(self) -> None:
        xml_error = '<result><error error_code="50" error_mesg="Bad" /></result>'

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, text=xml_error,
                headers={"content-type": "text/xml; charset=ISO-8859-1"},
            )

        client = _make_client(handler)
        with pytest.raises(ClearinghouseValidationError, match="50: Bad"):
            client.check_eligibility({"payer_id": "X", "npi": "Y", "tax_id": "Z"})

    def test_xml_body_without_xml_content_type(self) -> None:
        """Body starting with < triggers XML parser regardless of content-type."""
        xml_error = '<result><error error_code="99" error_mesg="Oops" /></result>'

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, text=xml_error,
                headers={"content-type": "text/html"},
            )

        client = _make_client(handler)
        with pytest.raises(ClearinghouseValidationError, match="99: Oops"):
            client.check_eligibility({"payer_id": "X", "npi": "Y", "tax_id": "Z"})

    def test_json_response_still_works(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200, json={"status": "active", "responseID": "R1"},
            )

        client = _make_client(handler)
        result = client.check_eligibility({"payer_id": "X", "npi": "Y"})
        assert result.status == "active"
        assert result.eligible is True


class TestEligibilityFieldMapping:
    """Test that eligibility uses correct ClaimMD field names."""

    def test_correct_field_names_sent(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "active"})

        client = _make_client(handler)
        client.check_eligibility({
            "payer_id": "60054",
            "npi": "1111111112",
            "tax_id": "999999999",
            "subscriber_id": "W999",
            "first_name": "Jane",
            "last_name": "Smith",
            "dob": "1985-06-15",
            "service_date": "2026-03-18",
        })

        from urllib.parse import parse_qs
        form = {k: v[0] for k, v in parse_qs(captured[0].content.decode()).items()}

        assert form["payerid"] == "60054"
        assert form["prov_npi"] == "1111111112"
        assert form["prov_taxid"] == "999999999"
        assert form["ins_number"] == "W999"
        assert form["pat_name_f"] == "Jane"
        assert form["pat_name_l"] == "Smith"
        assert form["ins_dob"] == "06/15/1985"
        assert form["fdos"] == "03/18/2026"

    def test_tax_id_in_prior_auth_mapping(self) -> None:
        captured: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            captured.append(request)
            return httpx.Response(200, json={"status": "approved"})

        client = _make_client(handler)
        client.submit_prior_auth({
            "payer_id": "60054",
            "npi": "1111111112",
            "tax_id": "999999999",
            "subscriber_id": "W999",
        })

        from urllib.parse import parse_qs
        form = {k: v[0] for k, v in parse_qs(captured[0].content.decode()).items()}
        assert form["ProviderTaxID"] == "999999999"
