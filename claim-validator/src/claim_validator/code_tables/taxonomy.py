"""Provider taxonomy code lookup against bundled NUCC table."""

from __future__ import annotations

from claim_validator.code_tables.loader import load_compressed_json


def lookup_taxonomy(code: str) -> str | None:
    """Look up a provider taxonomy code. Returns description or None if not found."""
    table = load_compressed_json("taxonomy.json.gz")
    normalized = code.upper().strip()
    return table.get(normalized)
