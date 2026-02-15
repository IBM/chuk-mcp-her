"""Tests for chuk_mcp_her.core.cache."""

from __future__ import annotations

import os
import time


from chuk_mcp_her.core.cache import ResponseCache


class TestResponseCachePutAndGet:
    def test_put_and_get_within_ttl(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("test/key1", {"foo": "bar"})
        result = cache.get("test/key1", ttl_seconds=3600)
        assert result == {"foo": "bar"}

    def test_put_complex_data(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        data = {
            "features": [{"name": "Church", "grade": "I", "coords": [533500, 180500]}],
            "count": 1,
        }
        cache.put("nhle/complex", data)
        result = cache.get("nhle/complex", ttl_seconds=3600)
        assert result == data
        assert result["features"][0]["name"] == "Church"

    def test_get_returns_none_for_missing_key(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        result = cache.get("nonexistent/key", ttl_seconds=3600)
        assert result is None

    def test_overwrite_existing_key(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("test/key1", {"version": 1})
        cache.put("test/key1", {"version": 2})
        result = cache.get("test/key1", ttl_seconds=3600)
        assert result == {"version": 2}


class TestResponseCacheTTLExpiry:
    def test_expired_entry_returns_none(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("test/expire", {"data": "old"})
        # Use TTL of 0 to ensure immediate expiry
        time.sleep(0.1)
        result = cache.get("test/expire", ttl_seconds=0)
        assert result is None

    def test_entry_within_ttl_returns_data(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("test/valid", {"data": "fresh"})
        result = cache.get("test/valid", ttl_seconds=3600)
        assert result == {"data": "fresh"}


class TestResponseCacheMakeKey:
    def test_determinism(self):
        key1 = ResponseCache.make_key("nhle", where="1=1", layer=6)
        key2 = ResponseCache.make_key("nhle", where="1=1", layer=6)
        assert key1 == key2

    def test_different_params_different_keys(self):
        key1 = ResponseCache.make_key("nhle", where="1=1", layer=6)
        key2 = ResponseCache.make_key("nhle", where="1=1", layer=7)
        assert key1 != key2

    def test_key_starts_with_source_id(self):
        key = ResponseCache.make_key("nhle", where="1=1")
        assert key.startswith("nhle/")

    def test_different_sources_different_keys(self):
        key1 = ResponseCache.make_key("nhle", where="1=1")
        key2 = ResponseCache.make_key("aim", where="1=1")
        assert key1 != key2

    def test_param_order_does_not_matter(self):
        key1 = ResponseCache.make_key("nhle", alpha="a", beta="b")
        key2 = ResponseCache.make_key("nhle", beta="b", alpha="a")
        assert key1 == key2

    def test_none_values_excluded(self):
        key1 = ResponseCache.make_key("nhle", where="1=1", extra=None)
        key2 = ResponseCache.make_key("nhle", where="1=1")
        assert key1 == key2


class TestResponseCacheClear:
    def test_clear_all(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("nhle/key1", {"a": 1})
        cache.put("aim/key2", {"b": 2})
        count = cache.clear()
        assert count == 2
        assert cache.get("nhle/key1", ttl_seconds=3600) is None
        assert cache.get("aim/key2", ttl_seconds=3600) is None

    def test_clear_by_source(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("nhle/key1", {"a": 1})
        cache.put("aim/key2", {"b": 2})
        count = cache.clear(source_id="nhle")
        assert count == 1
        assert cache.get("nhle/key1", ttl_seconds=3600) is None
        # aim entry should still be there
        assert cache.get("aim/key2", ttl_seconds=3600) == {"b": 2}

    def test_clear_empty_cache(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        count = cache.clear()
        assert count == 0


class TestResponseCacheInvalidate:
    def test_invalidate_existing_key(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("test/key1", {"data": "value"})
        cache.invalidate("test/key1")
        result = cache.get("test/key1", ttl_seconds=3600)
        assert result is None

    def test_invalidate_nonexistent_key(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        # Should not raise
        cache.invalidate("nonexistent/key")

    def test_invalidate_does_not_affect_others(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        cache.put("test/key1", {"a": 1})
        cache.put("test/key2", {"b": 2})
        cache.invalidate("test/key1")
        assert cache.get("test/key1", ttl_seconds=3600) is None
        assert cache.get("test/key2", ttl_seconds=3600) == {"b": 2}


class TestResponseCacheErrorHandling:
    def test_corrupt_json_returns_none(self, tmp_path):
        """Corrupt cache file should return None and be cleaned up."""
        cache = ResponseCache(cache_dir=str(tmp_path))
        # Write corrupt JSON
        key_path = cache._key_path("test/corrupt")
        key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(key_path, "w") as f:
            f.write("not valid json {{{")
        result = cache.get("test/corrupt", ttl_seconds=3600)
        assert result is None
        # Corrupt file should be cleaned up
        assert not key_path.exists()

    def test_write_to_readonly_dir_does_not_raise(self, tmp_path):
        """Cache write failure should log warning, not raise."""
        readonly_dir = tmp_path / "readonly"
        readonly_dir.mkdir()
        cache = ResponseCache(cache_dir=str(readonly_dir))
        cache.put("test/key", {"data": 1})
        # Now make it readonly
        cache_file = cache._key_path("test/key")
        os.chmod(str(cache_file), 0o000)
        try:
            # Writing again should fail silently
            cache.put("test/key", {"data": 2})
        finally:
            os.chmod(str(cache_file), 0o644)

    def test_clear_nonexistent_source_returns_zero(self, tmp_path):
        cache = ResponseCache(cache_dir=str(tmp_path))
        count = cache.clear(source_id="nonexistent_source")
        assert count == 0
