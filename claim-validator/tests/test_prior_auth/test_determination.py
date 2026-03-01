"""Tests for PA determination from eligibility response."""

from __future__ import annotations

import time
from typing import Any

from claim_validator.prior_auth.determination import determine_pa_required
from claim_validator.prior_auth.models.result import PADeterminationResult


def _make_response(
    indicator: str | None = None,
    descriptions: list[str] | None = None,
) -> dict[str, Any]:
    """Build a minimal 271 eligibility response dict."""
    benefit: dict[str, Any] = {"serviceTypeCodes": ["73"]}
    if indicator is not None:
        benefit["authOrCertIndicator"] = indicator
    if descriptions:
        benefit["additionalInformation"] = [
            {"description": d} for d in descriptions
        ]
    return {"benefitsInformation": [benefit]}


# ── Indicator "Y" ──────────────────────────────────────────────


class TestIndicatorY:
    """AC1: authOrCertIndicator=Y → required=True, confidence=high."""

    def test_required_true(self) -> None:
        result = determine_pa_required(_make_response(indicator="Y"))
        assert result.required is True

    def test_confidence_high(self) -> None:
        result = determine_pa_required(_make_response(indicator="Y"))
        assert result.confidence == "high"

    def test_reason_contains_indicator(self) -> None:
        result = determine_pa_required(_make_response(indicator="Y"))
        assert "authOrCertIndicator=Y" in result.reason

    def test_auth_or_cert_indicator_field(self) -> None:
        result = determine_pa_required(_make_response(indicator="Y"))
        assert result.auth_or_cert_indicator == "Y"

    def test_returns_pa_determination_result(self) -> None:
        result = determine_pa_required(_make_response(indicator="Y"))
        assert isinstance(result, PADeterminationResult)

    def test_indicator_y_with_free_text_stays_high(self) -> None:
        """AC: indicator=Y + free-text → required=True, confidence stays high."""
        resp = _make_response(
            indicator="Y",
            descriptions=["Prior authorization required"],
        )
        result = determine_pa_required(resp)
        assert result.required is True
        assert result.confidence == "high"
        assert len(result.free_text_indicators) > 0


# ── Indicator "N" ──────────────────────────────────────────────


class TestIndicatorN:
    """AC2: authOrCertIndicator=N → required=False, confidence=high."""

    def test_required_false(self) -> None:
        result = determine_pa_required(_make_response(indicator="N"))
        assert result.required is False

    def test_confidence_high(self) -> None:
        result = determine_pa_required(_make_response(indicator="N"))
        assert result.confidence == "high"

    def test_auth_or_cert_indicator_field(self) -> None:
        result = determine_pa_required(_make_response(indicator="N"))
        assert result.auth_or_cert_indicator == "N"

    def test_empty_free_text_indicators(self) -> None:
        result = determine_pa_required(_make_response(indicator="N"))
        assert result.free_text_indicators == []


# ── Indicator "U" or missing ───────────────────────────────────


class TestIndicatorUnknown:
    """AC3: authOrCertIndicator=U or missing → confidence=low."""

    def test_indicator_u_confidence_low(self) -> None:
        result = determine_pa_required(_make_response(indicator="U"))
        assert result.confidence == "low"

    def test_indicator_u_required_false(self) -> None:
        result = determine_pa_required(_make_response(indicator="U"))
        assert result.required is False

    def test_indicator_u_auth_field(self) -> None:
        result = determine_pa_required(_make_response(indicator="U"))
        assert result.auth_or_cert_indicator == "U"

    def test_missing_indicator_confidence_low(self) -> None:
        result = determine_pa_required(_make_response(indicator=None))
        assert result.confidence == "low"

    def test_missing_indicator_required_false(self) -> None:
        result = determine_pa_required(_make_response(indicator=None))
        assert result.required is False

    def test_missing_indicator_auth_field_none(self) -> None:
        result = determine_pa_required(_make_response(indicator=None))
        assert result.auth_or_cert_indicator is None

    def test_indicator_u_with_free_text_required(self) -> None:
        """U indicator + free-text PA keywords → required=True, medium."""
        resp = _make_response(
            indicator="U",
            descriptions=["Prior authorization required"],
        )
        result = determine_pa_required(resp)
        assert result.required is True
        assert result.confidence == "medium"
        assert len(result.free_text_indicators) > 0


# ── Free-text matching ─────────────────────────────────────────


class TestFreeText:
    """AC4: Free-text PA keywords → required=True, confidence=medium."""

    def test_prior_auth_keyword(self) -> None:
        resp = _make_response(descriptions=["Prior authorization is required"])
        result = determine_pa_required(resp)
        assert result.required is True
        assert result.confidence == "medium"
        assert "prior auth" in result.free_text_indicators

    def test_precertification_keyword(self) -> None:
        resp = _make_response(descriptions=["Precertification needed"])
        result = determine_pa_required(resp)
        assert result.required is True
        assert "precertification" in result.free_text_indicators

    def test_preauthorization_keyword(self) -> None:
        resp = _make_response(descriptions=["Preauthorization required"])
        result = determine_pa_required(resp)
        assert result.required is True
        assert "preauthorization" in result.free_text_indicators

    def test_pre_certification_hyphenated(self) -> None:
        resp = _make_response(descriptions=["Pre-certification required"])
        result = determine_pa_required(resp)
        assert result.required is True
        assert "pre-certification" in result.free_text_indicators

    def test_pre_authorization_hyphenated(self) -> None:
        resp = _make_response(descriptions=["Pre-authorization needed"])
        result = determine_pa_required(resp)
        assert result.required is True
        assert "pre-authorization" in result.free_text_indicators

    def test_case_insensitive(self) -> None:
        resp = _make_response(descriptions=["PRIOR AUTHORIZATION REQUIRED"])
        result = determine_pa_required(resp)
        assert result.required is True
        assert "prior auth" in result.free_text_indicators

    def test_no_match_returns_not_required(self) -> None:
        resp = _make_response(descriptions=["Copay information available"])
        result = determine_pa_required(resp)
        assert result.required is False


# ── Conflict resolution (FR4) ─────────────────────────────────


class TestConflictResolution:
    """AC5: indicator=N + free-text PA → required=True (free-text wins)."""

    def test_free_text_overrides_indicator_n(self) -> None:
        resp = _make_response(
            indicator="N",
            descriptions=["Prior authorization required for this service"],
        )
        result = determine_pa_required(resp)
        assert result.required is True

    def test_confidence_medium_on_conflict(self) -> None:
        resp = _make_response(
            indicator="N",
            descriptions=["Prior authorization required"],
        )
        result = determine_pa_required(resp)
        assert result.confidence == "medium"

    def test_reason_explains_conflict(self) -> None:
        resp = _make_response(
            indicator="N",
            descriptions=["Prior authorization required"],
        )
        result = determine_pa_required(resp)
        assert "free-text" in result.reason.lower()
        assert "N" in result.reason

    def test_auth_indicator_preserved(self) -> None:
        resp = _make_response(
            indicator="N",
            descriptions=["Precertification needed"],
        )
        result = determine_pa_required(resp)
        assert result.auth_or_cert_indicator == "N"
        assert len(result.free_text_indicators) > 0


# ── Duck typing (dict input) ──────────────────────────────────


class TestDuckTyping:
    """AC6: Plain dict works without EligibilityResponse import."""

    def test_plain_dict(self) -> None:
        resp = {
            "benefitsInformation": [
                {"authOrCertIndicator": "Y"},
            ],
        }
        result = determine_pa_required(resp)
        assert result.required is True

    def test_object_with_attributes(self) -> None:
        """Simulate a typed object with matching attributes."""

        class FakeInfo:
            description = "Prior authorization required"

        class FakeBenefit:
            authOrCertIndicator = "N"  # noqa: N815
            additionalInformation = [FakeInfo()]  # noqa: N815

        class FakeResponse:
            benefitsInformation = [FakeBenefit()]  # noqa: N815

        result = determine_pa_required(FakeResponse())
        assert result.required is True  # free-text overrides N


# ── Edge cases and graceful fallback ───────────────────────────


class TestEdgeCases:
    """Graceful handling of missing/malformed input."""

    def test_none_response(self) -> None:
        result = determine_pa_required(None)
        assert result.required is False
        assert result.confidence == "low"

    def test_empty_dict(self) -> None:
        result = determine_pa_required({})
        assert result.required is False
        assert result.confidence == "low"

    def test_no_benefits_information(self) -> None:
        result = determine_pa_required({"other": "data"})
        assert result.required is False
        assert result.confidence == "low"

    def test_empty_benefits_list(self) -> None:
        result = determine_pa_required({"benefitsInformation": []})
        assert result.required is False
        assert result.confidence == "low"

    def test_benefits_not_a_list(self) -> None:
        result = determine_pa_required({"benefitsInformation": "invalid"})
        assert result.required is False
        assert result.confidence == "low"

    def test_additional_info_not_a_list(self) -> None:
        resp = {
            "benefitsInformation": [
                {"additionalInformation": "not a list"},
            ],
        }
        result = determine_pa_required(resp)
        assert result.required is False

    def test_description_not_a_string(self) -> None:
        resp = {
            "benefitsInformation": [
                {
                    "additionalInformation": [{"description": 12345}],
                },
            ],
        }
        result = determine_pa_required(resp)
        assert result.required is False

    def test_multiple_benefits_y_before_n(self) -> None:
        resp = {
            "benefitsInformation": [
                {"authOrCertIndicator": "Y"},
                {"authOrCertIndicator": "N"},
            ],
        }
        result = determine_pa_required(resp)
        assert result.required is True
        assert result.auth_or_cert_indicator == "Y"

    def test_multiple_benefits_n_before_y_most_restrictive_wins(self) -> None:
        """Most restrictive indicator wins regardless of position."""
        resp = {
            "benefitsInformation": [
                {"authOrCertIndicator": "N"},
                {"authOrCertIndicator": "Y"},
            ],
        }
        result = determine_pa_required(resp)
        assert result.required is True
        assert result.auth_or_cert_indicator == "Y"

    def test_multiple_benefits_free_text_across_entries(self) -> None:
        resp = {
            "benefitsInformation": [
                {"additionalInformation": [{"description": "Copay info"}]},
                {
                    "additionalInformation": [
                        {"description": "Prior auth required for imaging"},
                    ],
                },
            ],
        }
        result = determine_pa_required(resp)
        assert result.required is True
        assert "prior auth" in result.free_text_indicators

    def test_indicator_lowercase_normalized(self) -> None:
        resp = _make_response(indicator="y")
        result = determine_pa_required(resp)
        assert result.required is True
        assert result.auth_or_cert_indicator == "Y"

    def test_indicator_with_whitespace_normalized(self) -> None:
        resp = _make_response(indicator="  Y  ")
        result = determine_pa_required(resp)
        assert result.required is True
        assert result.auth_or_cert_indicator == "Y"

    def test_unrecognized_indicator_value(self) -> None:
        resp = _make_response(indicator="X")
        result = determine_pa_required(resp)
        assert result.required is False
        assert result.confidence == "low"
        assert result.auth_or_cert_indicator == "X"

    def test_empty_string_indicator_treated_as_missing(self) -> None:
        resp = _make_response(indicator="")
        result = determine_pa_required(resp)
        assert result.required is False
        assert result.confidence == "low"
        assert result.auth_or_cert_indicator is None


# ── Performance ────────────────────────────────────────────────


class TestPerformance:
    """AC7: Execution under 10ms."""

    def test_execution_under_10ms(self) -> None:
        resp = _make_response(
            indicator="Y",
            descriptions=["Prior authorization required"],
        )
        start = time.perf_counter()
        for _ in range(100):
            determine_pa_required(resp)
        elapsed_ms = (time.perf_counter() - start) * 1000 / 100
        assert elapsed_ms < 10, f"Avg execution took {elapsed_ms:.3f}ms (limit: 10ms)"


# ── Re-exports ─────────────────────────────────────────────────


class TestReExports:
    """AC8: Available via top-level import."""

    def test_import_from_prior_auth(self) -> None:
        from claim_validator.prior_auth import determine_pa_required as fn

        assert callable(fn)

    def test_import_from_top_level(self) -> None:
        from claim_validator import determine_pa_required as fn

        assert callable(fn)

    def test_in_prior_auth_all(self) -> None:
        import claim_validator.prior_auth as pa

        assert "determine_pa_required" in pa.__all__

    def test_in_top_level_all(self) -> None:
        import claim_validator

        assert "determine_pa_required" in claim_validator.__all__
