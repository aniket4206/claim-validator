"""AAA reject reason code table — shared accessor and lookup."""

from __future__ import annotations

from typing import Any, cast

from claim_validator.shared.code_tables.loader import load_json


def get_aaa_reject_codes_table() -> dict[str, Any]:
    """Return the full AAA reject reason codes table (cached after first load)."""
    return cast(dict[str, Any], load_json("aaa_reject_codes.json"))


def lookup_aaa_reject(code: str) -> dict[str, str] | None:
    """Look up an AAA reject reason code. Returns details dict or None if not found.

    The returned dict contains: ``meaning``, ``description``, ``suggested_fix``.
    """
    return get_aaa_reject_codes_table().get(code.upper().strip())
