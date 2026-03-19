"""Revenue codes code table — UB-04 revenue code lookup for institutional claims."""

from __future__ import annotations

from typing import cast

from claim_validator.shared.code_tables.loader import load_compressed_json


def get_revenue_codes_table() -> dict[str, str]:
    """Return the full revenue codes table (cached after first load).

    Returns a dict mapping 4-digit revenue code strings to descriptions.
    """
    return cast(dict[str, str], load_compressed_json("revenue_codes.json.gz"))


def lookup_revenue_code(code: str) -> str | None:
    """Look up a revenue code. Returns description or None if not found."""
    table = get_revenue_codes_table()
    normalized = code.strip().zfill(4)
    return table.get(normalized)
