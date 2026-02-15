"""
Async client for ArcGIS Feature Service queries.

Handles spatial queries, WHERE clause construction, pagination,
GeoJSON output, rate limiting, and response caching.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

from .cache import ResponseCache

logger = logging.getLogger(__name__)


class ArcGISClient:
    """Async client for ArcGIS Feature Service queries.

    Provides query, count, and paginated query methods with caching
    and rate limiting.
    """

    def __init__(
        self,
        base_url: str,
        cache: ResponseCache | None = None,
        cache_ttl: int = 86400,
        timeout: float = 30.0,
        max_retries: int = 3,
        rate_limit_per_sec: float = 5.0,
        cache_prefix: str = "arcgis",
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._cache = cache
        self._cache_ttl = cache_ttl
        self._cache_prefix = cache_prefix
        self._timeout = timeout
        self._max_retries = max_retries
        self._min_interval = 1.0 / rate_limit_per_sec if rate_limit_per_sec > 0 else 0
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Lazily create the httpx client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                limits=httpx.Limits(
                    max_connections=10,
                    max_keepalive_connections=5,
                ),
            )
        return self._client

    async def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        if self._min_interval <= 0:
            return
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def query(
        self,
        layer_id: int,
        where: str = "1=1",
        geometry: dict[str, Any] | None = None,
        geometry_type: str = "esriGeometryEnvelope",
        spatial_rel: str = "esriSpatialRelIntersects",
        in_sr: int = 27700,
        out_fields: str = "*",
        out_sr: int = 27700,
        result_offset: int = 0,
        result_record_count: int = 100,
        return_count_only: bool = False,
        return_geometry: bool = True,
        order_by_fields: str | None = None,
    ) -> dict[str, Any]:
        """Execute an ArcGIS Feature Service query.

        Returns the parsed JSON response from ArcGIS.
        """
        # Build cache key
        cache_key = None
        if self._cache is not None:
            cache_key = ResponseCache.make_key(
                f"{self._cache_prefix}_{int(layer_id)}",
                where=where,
                geometry=str(geometry),
                geometry_type=geometry_type,
                spatial_rel=spatial_rel,
                in_sr=in_sr,
                out_fields=out_fields,
                out_sr=out_sr,
                offset=result_offset,
                count=result_record_count,
                count_only=return_count_only,
                return_geometry=return_geometry,
            )
            cached = self._cache.get(cache_key, self._cache_ttl)
            if cached is not None:
                logger.debug("Cache hit for layer %d query", layer_id)
                return cached

        url = f"{self._base_url}/{int(layer_id)}/query"
        params: dict[str, Any] = {
            "where": where,
            "outFields": out_fields,
            "outSR": out_sr,
            "resultOffset": result_offset,
            "resultRecordCount": result_record_count,
            "returnCountOnly": str(return_count_only).lower(),
            "returnGeometry": str(return_geometry).lower(),
            "f": "json" if return_count_only else "geojson",
        }

        if geometry is not None:
            params["geometry"] = str(geometry).replace("'", '"')
            params["geometryType"] = geometry_type
            params["spatialRel"] = spatial_rel
            params["inSR"] = in_sr

        if order_by_fields:
            params["orderByFields"] = order_by_fields

        client = await self._get_client()
        last_error: Exception | None = None

        for attempt in range(self._max_retries):
            try:
                await self._rate_limit()
                response = await client.get(url, params=params)

                if response.status_code == 429:
                    wait = 2 ** (attempt + 1)
                    logger.warning("Rate limited, waiting %ds", wait)
                    await asyncio.sleep(wait)
                    continue

                response.raise_for_status()
                data = response.json()

                # Check for ArcGIS-level errors
                if "error" in data:
                    error_msg = data["error"].get("message", str(data["error"]))
                    raise RuntimeError(f"ArcGIS error: {error_msg}")

                # Cache successful response
                if cache_key and self._cache is not None:
                    self._cache.put(cache_key, data)

                return data

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code >= 500:
                    wait = 2 ** (attempt + 1)
                    logger.warning(
                        "Server error %d, retry %d/%d in %ds",
                        e.response.status_code,
                        attempt + 1,
                        self._max_retries,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                raise
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                last_error = e
                wait = 2 ** (attempt + 1)
                logger.warning(
                    "Connection error, retry %d/%d in %ds: %s",
                    attempt + 1,
                    self._max_retries,
                    wait,
                    e,
                )
                await asyncio.sleep(wait)

        raise RuntimeError(f"ArcGIS query failed after {self._max_retries} attempts: {last_error}")

    async def count(
        self,
        layer_id: int,
        where: str = "1=1",
        geometry: dict[str, Any] | None = None,
        geometry_type: str = "esriGeometryEnvelope",
        spatial_rel: str = "esriSpatialRelIntersects",
        in_sr: int = 27700,
    ) -> int:
        """Count features matching criteria (fast, no geometry returned)."""
        result = await self.query(
            layer_id=layer_id,
            where=where,
            geometry=geometry,
            geometry_type=geometry_type,
            spatial_rel=spatial_rel,
            in_sr=in_sr,
            return_count_only=True,
        )
        return result.get("count", 0)

    async def query_all(
        self,
        layer_id: int,
        where: str = "1=1",
        geometry: dict[str, Any] | None = None,
        geometry_type: str = "esriGeometryEnvelope",
        spatial_rel: str = "esriSpatialRelIntersects",
        in_sr: int = 27700,
        out_fields: str = "*",
        out_sr: int = 27700,
        max_records: int = 2000,
        page_size: int = 500,
    ) -> list[dict[str, Any]]:
        """Query with auto-pagination up to max_records.

        Returns a list of GeoJSON features.
        """
        all_features: list[dict[str, Any]] = []
        offset = 0

        while len(all_features) < max_records:
            batch_size = min(page_size, max_records - len(all_features))
            result = await self.query(
                layer_id=layer_id,
                where=where,
                geometry=geometry,
                geometry_type=geometry_type,
                spatial_rel=spatial_rel,
                in_sr=in_sr,
                out_fields=out_fields,
                out_sr=out_sr,
                result_offset=offset,
                result_record_count=batch_size,
            )

            features = result.get("features", [])
            if not features:
                break

            all_features.extend(features)
            offset += len(features)

            if len(features) < batch_size:
                break

        return all_features

    @staticmethod
    def make_envelope(xmin: float, ymin: float, xmax: float, ymax: float) -> dict[str, Any]:
        """Create an ArcGIS envelope geometry dict."""
        return {
            "xmin": xmin,
            "ymin": ymin,
            "xmax": xmax,
            "ymax": ymax,
        }

    async def close(self) -> None:
        """Close the underlying httpx client."""
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None
