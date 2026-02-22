"""HCPCS code lookup against bundled table."""

from __future__ import annotations

from claim_validator.code_tables.loader import load_compressed_json


def lookup_hcpcs(code: str) -> str | None:
    """Look up an HCPCS code. Returns description or None if not found."""
    table = load_compressed_json("hcpcs.json.gz")
    normalized = code.upper().strip()
    return table.get(normalized)
