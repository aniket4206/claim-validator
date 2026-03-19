"""Payer routing code table — loads payer-to-clearinghouse mapping data.

Provides ``load_default_mapping()`` which returns a dict of payer ID to
a list of :class:`~claim_validator.routing.models.PayerRoute` entries,
sorted by priority.  Uses the same lazy-loading, thread-safe infrastructure
as all other code tables.
"""

from __future__ import annotations

import threading
from typing import Any

from claim_validator.exceptions import CodeTableError
from claim_validator.routing.models import PayerRoute
from claim_validator.shared.code_tables.loader import load_compressed_json

_routing_lock = threading.Lock()
_routing_table: dict[str, list[PayerRoute]] | None = None


def _build_routing_table(
    raw: dict[str, Any],
) -> dict[str, list[PayerRoute]]:
    """Convert raw JSON dicts into sorted PayerRoute lists."""
    table: dict[str, list[PayerRoute]] = {}
    for payer_id, entries in raw.items():
        try:
            routes = [
                PayerRoute(
                    clearinghouse=e["clearinghouse"],
                    payer_id_at_clearinghouse=e["payer_id_at_clearinghouse"],
                    priority=e["priority"],
                    supports=frozenset(e["supports"]),
                )
                for e in entries
            ]
        except (KeyError, TypeError) as exc:
            raise CodeTableError(
                f"Malformed payer routing entry for '{payer_id}': {exc}"
            ) from exc
        routes.sort(key=lambda r: r.priority)
        table[payer_id] = routes
    return table


def get_payer_routing_table() -> dict[str, list[PayerRoute]]:
    """Return the full payer routing table (cached after first load).

    Returns a dict mapping payer ID strings to lists of
    :class:`PayerRoute` entries sorted by priority.
    """
    return load_default_mapping()


def load_default_mapping() -> dict[str, list[PayerRoute]]:
    """Load the default payer-to-clearinghouse mapping from bundled data.

    First call loads ``payer_routing.json.gz``, converts entries to
    :class:`PayerRoute` dataclass instances, and caches the result.
    Subsequent calls return the cached table.  Thread-safe via
    double-check locking.
    """
    global _routing_table  # noqa: PLW0603

    if _routing_table is not None:
        return _routing_table

    with _routing_lock:
        if _routing_table is not None:
            return _routing_table

        raw = load_compressed_json("payer_routing.json.gz")
        _routing_table = _build_routing_table(raw)
        return _routing_table


def _clear_routing_cache() -> None:
    """Clear the cached routing table.  For testing only."""
    global _routing_table  # noqa: PLW0603
    with _routing_lock:
        _routing_table = None
