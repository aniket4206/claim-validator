"""Generic lazy loader for compressed JSON code tables."""

from __future__ import annotations

import gzip
import json
import logging
import threading
from importlib.resources import files
from typing import Any

from claim_validator.exceptions import CodeTableError

logger = logging.getLogger(__name__)

_global_lock = threading.Lock()
_locks: dict[str, threading.Lock] = {}
_tables: dict[str, dict[str, str]] = {}


def _get_lock(table_name: str) -> threading.Lock:
    """Get or create a per-table lock (thread-safe)."""
    if table_name not in _locks:
        with _global_lock:
            if table_name not in _locks:
                _locks[table_name] = threading.Lock()
    return _locks[table_name]


def load_compressed_json(filename: str) -> dict[str, str]:
    """Load a .json.gz file from package data with lazy singleton caching.

    First call loads from disk; subsequent calls return the cached dict.
    Thread-safe via double-check locking.
    """
    table_name = filename.removesuffix(".json.gz")

    if table_name in _tables:
        return _tables[table_name]

    lock = _get_lock(table_name)
    with lock:
        if table_name in _tables:
            return _tables[table_name]

        try:
            data_pkg = files("claim_validator.data")
            resource = data_pkg.joinpath(filename)
            raw = resource.read_bytes()
            decompressed = gzip.decompress(raw)
            table: dict[str, str] = json.loads(decompressed)
        except Exception as exc:
            raise CodeTableError(
                f"Failed to load code table '{filename}': {exc}"
            ) from exc

        _tables[table_name] = table
        return table


def load_json(filename: str) -> Any:
    """Load a plain .json file from package data (not cached)."""
    try:
        data_pkg = files("claim_validator.data")
        resource = data_pkg.joinpath(filename)
        return json.loads(resource.read_text(encoding="utf-8"))
    except Exception as exc:
        raise CodeTableError(f"Failed to load '{filename}': {exc}") from exc
