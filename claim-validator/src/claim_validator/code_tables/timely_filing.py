"""Timely filing deadline lookup for common payers."""

from __future__ import annotations

import threading

from claim_validator.code_tables.loader import load_json

_lock = threading.Lock()
_timely_filing: dict[str, int] | None = None


def get_filing_deadline(payer_id: str) -> int | None:
    """Get timely filing deadline in days for a payer.

    Returns the deadline in days, or None if payer is unknown
    and no default exists.
    """
    global _timely_filing  # noqa: PLW0603
    if _timely_filing is None:
        with _lock:
            if _timely_filing is None:
                _timely_filing = load_json("timely_filing.json")

    normalized = payer_id.upper().strip()
    deadline = _timely_filing.get(normalized)
    if deadline is None:
        deadline = _timely_filing.get("_default")
    return deadline
