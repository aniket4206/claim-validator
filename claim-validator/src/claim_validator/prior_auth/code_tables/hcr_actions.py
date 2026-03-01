"""HCR action code lookup for 278 response interpretation."""

from __future__ import annotations

from typing import Any

from claim_validator.prior_auth.code_tables.loader import load_pa_json


def get_hcr_action_code(code: str) -> dict[str, str] | None:
    """Look up an HCR action code. Returns details dict or None if not found.

    The returned dict contains: description, category, suggested_action.
    """
    table: dict[str, Any] = load_pa_json("hcr_action_codes.json")
    normalized = code.upper().strip()
    return table.get(normalized)
