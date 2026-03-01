"""Service type code lookup for eligibility verification."""

from __future__ import annotations

from claim_validator.eligibility.code_tables.loader import load_elig_json


def get_service_type(code: str) -> str | None:
    """Look up an X12 service type code. Returns description or None if not found."""
    table: dict[str, str] = load_elig_json("service_types.json")
    normalized = code.upper().strip()
    return table.get(normalized)
