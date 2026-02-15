"""
Filesystem-based HTTP response cache with per-source TTL.

Caches ArcGIS and Heritage Gateway API responses to reduce load
and improve response times.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

from ..constants import EnvVar

logger = logging.getLogger(__name__)

_DEFAULT_CACHE_DIR = Path.home() / ".cache" / "chuk-mcp-her"


class ResponseCache:
    """Filesystem-based HTTP response cache with TTL."""

    def __init__(self, cache_dir: str | None = None) -> None:
        dir_path = cache_dir or os.environ.get(EnvVar.HER_CACHE_DIR)
        self._cache_dir = Path(dir_path) if dir_path else _DEFAULT_CACHE_DIR

    def get(self, cache_key: str, ttl_seconds: int) -> dict[str, Any] | None:
        """Retrieve cached response if within TTL."""
        path = self._key_path(cache_key)
        if not path.exists():
            return None

        try:
            with open(path) as f:
                entry = json.load(f)

            stored_at = entry.get("_cached_at", 0)
            if time.time() - stored_at > ttl_seconds:
                path.unlink(missing_ok=True)
                return None

            return entry.get("data")
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Cache read error for %s: %s", cache_key, e)
            path.unlink(missing_ok=True)
            return None

    def put(self, cache_key: str, data: dict[str, Any]) -> None:
        """Store response data to cache."""
        path = self._key_path(cache_key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            entry = {"_cached_at": time.time(), "data": data}
            with open(path, "w") as f:
                json.dump(entry, f)
        except OSError as e:
            logger.warning("Cache write error for %s: %s", cache_key, e)

    def invalidate(self, cache_key: str) -> None:
        """Remove a cached entry."""
        path = self._key_path(cache_key)
        path.unlink(missing_ok=True)

    def clear(self, source_id: str | None = None) -> int:
        """Clear cached entries, optionally filtered by source prefix.

        Returns:
            Number of entries removed.
        """
        count = 0
        target = self._cache_dir / source_id if source_id else self._cache_dir
        if not target.exists():
            return 0

        for path in target.rglob("*.json"):
            path.unlink(missing_ok=True)
            count += 1

        return count

    @staticmethod
    def make_key(source_id: str, **params: Any) -> str:
        """Generate deterministic cache key from source and parameters.

        Returns a string like 'nhle/abc123def456'.
        """
        sorted_params = sorted((k, str(v)) for k, v in params.items() if v is not None)
        raw = json.dumps(sorted_params, sort_keys=True)
        digest = hashlib.sha256(raw.encode()).hexdigest()[:16]
        return f"{source_id}/{digest}"

    def _key_path(self, cache_key: str) -> Path:
        """Convert cache key to filesystem path."""
        return self._cache_dir / f"{cache_key}.json"
