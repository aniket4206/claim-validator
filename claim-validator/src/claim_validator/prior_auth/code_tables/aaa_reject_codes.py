"""AAA reject reason code lookup for 278 error interpretation."""

from __future__ import annotations

from typing import Any

from claim_validator.prior_auth.code_tables.loader import load_pa_json


def get_aaa_reject_code(code: str) -> dict[str, str] | None:
    """Look up an AAA reject reason code. Returns details dict or None if not found.

    The returned dict contains: meaning, description, suggested_fix.
    """
    table: dict[str, Any] = load_pa_json("aaa_reject_codes.json")
    normalized = code.upper().strip()
    return table.get(normalized)
