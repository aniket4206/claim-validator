"""Eligibility code table loader — lazy singleton with thread safety."""

from __future__ import annotations

import json
import threading
from importlib.resources import files
from typing import Any

from claim_validator.exceptions import CodeTableError

_global_lock = threading.Lock()
_locks: dict[str, threading.Lock] = {}
_tables: dict[str, Any] = {}


def _get_lock(table_name: str) -> threading.Lock:
    """Get or create a per-table lock (thread-safe)."""
    if table_name not in _locks:
        with _global_lock:
            if table_name not in _locks:
                _locks[table_name] = threading.Lock()
    return _locks[table_name]


def load_elig_json(filename: str) -> Any:
    """Load a JSON file from eligibility/data/ with lazy singleton caching.

    First call loads from disk; subsequent calls return the cached dict.
    Thread-safe via double-check locking.
    """
    table_name = filename.removesuffix(".json")

    if table_name in _tables:
        return _tables[table_name]

    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:
            return _tables[table_name]

        try:
            data_pkg = files("claim_validator.eligibility.data")
            resource = data_pkg.joinpath(filename)
            table: Any = json.loads(resource.read_text(encoding="utf-8"))
        except Exception as exc:
            raise CodeTableError(
                f"Failed to load eligibility code table '{filename}': {exc}"
            ) from exc

        _tables[table_name] = table
        return table
