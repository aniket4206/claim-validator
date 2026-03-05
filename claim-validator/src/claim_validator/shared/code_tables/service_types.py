"""X12 service type code table — shared accessor and lookup."""

from __future__ import annotations

from typing import cast

from claim_validator.shared.code_tables.loader import load_json


def get_service_types_table() -> dict[str, str]:
    """Return the full X12 service types table (cached after first load)."""
    return cast(dict[str, str], load_json("service_types.json"))


def lookup_service_type(code: str) -> str | None:
    """Look up an X12 service type code. Returns description or None if not found."""
    return get_service_types_table().get(code.upper().strip())
