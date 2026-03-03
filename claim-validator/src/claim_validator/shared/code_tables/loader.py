"""Unified lazy loader for code table data files (compressed and plain JSON).

All code tables are loaded from the ``claim_validator.shared.data`` package
using ``importlib.resources``. Each table is cached as a lazy singleton with
per-table ``threading.Lock`` for thread-safe initialization.
"""

from __future__ import annotations

import gzip
import json
import threading
from importlib.resources import files
from typing import Any, cast

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


def load_compressed_json(filename: str) -> dict[str, str]:
    """Load a ``.json.gz`` file from ``shared/data/`` with lazy singleton caching.

    First call loads from disk; subsequent calls return the cached dict.
    Thread-safe via double-check locking.
    """
    table_name = filename.removesuffix(".json.gz")

    if table_name in _tables:
        return cast(dict[str, str], _tables[table_name])

    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:
            return cast(dict[str, str], _tables[table_name])

        try:
            data_pkg = files("claim_validator.shared.data")
            raw = data_pkg.joinpath(filename).read_bytes()
            table: dict[str, str] = json.loads(gzip.decompress(raw))
        except Exception as exc:
            raise CodeTableError(
                f"Failed to load code table '{filename}': {exc}"
            ) from exc

        _tables[table_name] = table
        return table


def load_json(filename: str) -> Any:
    """Load a plain ``.json`` file from ``shared/data/`` with lazy singleton caching.

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
            data_pkg = files("claim_validator.shared.data")
            text = data_pkg.joinpath(filename).read_text(encoding="utf-8")
            table: Any = json.loads(text)
        except Exception as exc:
            raise CodeTableError(
                f"Failed to load '{filename}': {exc}"
            ) from exc

        _tables[table_name] = table
        return table


def _clear_cache() -> None:
    """Clear all cached tables. For testing only."""
    with _global_lock:
        _tables.clear()
        _locks.clear()
