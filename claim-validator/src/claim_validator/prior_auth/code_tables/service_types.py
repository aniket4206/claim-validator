"""PA service type code lookup for UM segment interpretation."""

from __future__ import annotations

from typing import Any

from claim_validator.prior_auth.code_tables.loader import load_pa_json


def get_pa_service_type(code: str) -> str | None:
    """Look up a PA service type code. Returns description or None if not found."""
    table: dict[str, Any] = load_pa_json("service_types.json")
    normalized = code.upper().strip()
    return table.get(normalized)
