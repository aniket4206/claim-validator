"""HCPCS/CPT code table — shared accessor and lookup."""

from __future__ import annotations

from claim_validator.shared.code_tables.loader import load_compressed_json


def get_hcpcs_table() -> dict[str, str]:
    """Return the full HCPCS code table (cached after first load)."""
    return load_compressed_json("hcpcs.json.gz")


def lookup_hcpcs(code: str) -> str | None:
    """Look up an HCPCS code. Returns description or None if not found."""
    return get_hcpcs_table().get(code.upper().strip())
