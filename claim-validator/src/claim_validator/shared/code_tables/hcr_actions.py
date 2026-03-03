"""HCR certification action code table — shared accessor and lookup."""

from __future__ import annotations

from typing import Any, cast

from claim_validator.shared.code_tables.loader import load_json


def get_hcr_action_codes_table() -> dict[str, Any]:
    """Return the full HCR action codes table (cached after first load)."""
    return cast(dict[str, Any], load_json("hcr_action_codes.json"))


def lookup_hcr_action(code: str) -> dict[str, str] | None:
    """Look up an HCR action code. Returns details dict or None if not found.

    The returned dict contains: ``description``, ``category``, ``suggested_action``.
    """
    return get_hcr_action_codes_table().get(code.upper().strip())
