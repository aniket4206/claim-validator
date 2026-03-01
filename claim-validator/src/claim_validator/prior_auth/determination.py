"""PA determination from eligibility response — cross-module bridge.

Determines whether prior authorization is required by analyzing a 271
eligibility response's ``authOrCertIndicator`` field and free-text
``additionalInformation`` descriptions.

Architecture decision D28: uses duck typing so the eligibility module
is never hard-imported.
"""

from __future__ import annotations

from typing import Any

from claim_validator.prior_auth.models.result import PADeterminationResult

# Case-insensitive substrings that indicate PA is required.
_PA_KEYWORDS: tuple[str, ...] = (
    "prior auth",
    "precertification",
    "preauthorization",
    "pre-certification",
    "pre-authorization",
)


def _get_field(obj: Any, key: str, default: Any = None) -> Any:
    """Get a field from a dict or an object attribute (duck typing)."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _extract_indicator(benefits: list[Any]) -> str | None:
    """Return the most restrictive ``authOrCertIndicator`` across benefits.

    Priority: ``"Y"`` (PA required) > ``"U"``/unknown > ``"N"`` (not required).
    If any benefit entry requires PA, the overall indicator is ``"Y"``.
    """
    priority = {"Y": 3, "U": 2, "N": 1}
    best: str | None = None
    best_rank = -1
    for benefit in benefits:
        raw = _get_field(benefit, "authOrCertIndicator")
        if raw is None:
            continue
        indicator = str(raw).strip().upper()
        if not indicator:
            continue
        rank = priority.get(indicator, 2)  # unknown values treated like "U"
        if rank > best_rank:
            best = indicator
            best_rank = rank
    return best


def _scan_free_text(benefits: list[Any]) -> list[str]:
    """Scan ``additionalInformation[*].description`` for PA keywords."""
    matched: list[str] = []
    for benefit in benefits:
        additional_info = _get_field(benefit, "additionalInformation", [])
        if not isinstance(additional_info, list):
            continue
        for info_entry in additional_info:
            description = _get_field(info_entry, "description", "")
            if not isinstance(description, str) or not description:
                continue
            lower_desc = description.lower()
            for keyword in _PA_KEYWORDS:
                if keyword in lower_desc and keyword not in matched:
                    matched.append(keyword)
    return matched


def determine_pa_required(response: Any) -> PADeterminationResult:
    """Determine whether prior authorization is required from a 271 response.

    Accepts a dict (Stedi JSON) or any object with a ``benefitsInformation``
    attribute.  No eligibility module imports are required.

    Logic (architecture decision D28):
      1. Extract ``authOrCertIndicator`` → Y/N/U
      2. Scan free-text ``additionalInformation.description`` for PA keywords
      3. Conflict resolution (FR4): free-text overrides indicator=N

    Parameters
    ----------
    response:
        A 271 eligibility response as a dict or typed object.

    Returns
    -------
    PADeterminationResult
        Contains ``required``, ``confidence``, ``reason``,
        ``auth_or_cert_indicator``, and ``free_text_indicators``.
    """
    benefits = _get_field(response, "benefitsInformation", [])
    if not isinstance(benefits, list):
        benefits = []

    # --- Step 1: Extract structured indicator ---
    indicator = _extract_indicator(benefits)

    # --- Step 2: Scan free-text ---
    free_text_indicators = _scan_free_text(benefits)
    has_free_text = len(free_text_indicators) > 0

    # --- Step 3: Determine result with conflict resolution ---
    if indicator == "Y":
        return PADeterminationResult(
            required=True,
            confidence="high",
            reason="authOrCertIndicator=Y indicates prior authorization required",
            auth_or_cert_indicator="Y",
            free_text_indicators=free_text_indicators,
        )

    if indicator == "N":
        if has_free_text:
            # FR4: free-text overrides indicator=N
            return PADeterminationResult(
                required=True,
                confidence="medium",
                reason=(
                    "authOrCertIndicator=N but free-text indicates PA required "
                    "(free-text takes precedence per FR4)"
                ),
                auth_or_cert_indicator="N",
                free_text_indicators=free_text_indicators,
            )
        return PADeterminationResult(
            required=False,
            confidence="high",
            reason="authOrCertIndicator=N indicates prior authorization not required",
            auth_or_cert_indicator="N",
            free_text_indicators=[],
        )

    # indicator is "U", None, or any other value
    if has_free_text:
        return PADeterminationResult(
            required=True,
            confidence="medium",
            reason="Free-text indicates prior authorization required",
            auth_or_cert_indicator=indicator,
            free_text_indicators=free_text_indicators,
        )

    return PADeterminationResult(
        required=False,
        confidence="low",
        reason=(
            "authOrCertIndicator is unknown/missing and no free-text PA indicators found"
            if indicator is None
            else f"authOrCertIndicator={indicator} (unknown) and no free-text PA indicators found"
        ),
        auth_or_cert_indicator=indicator,
        free_text_indicators=[],
    )
