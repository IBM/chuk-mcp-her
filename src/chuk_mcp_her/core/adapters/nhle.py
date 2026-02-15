"""
NHLE (National Heritage List for England) adapter.

Queries the Historic England ArcGIS Feature Service for listed buildings,
scheduled monuments, registered parks and gardens, battlefields,
protected wrecks, and World Heritage Sites.
"""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from ...constants import (
    ALL_NHLE_POINT_LAYERS,
    DESIGNATION_LAYERS,
    DESIGNATION_TYPES,
    LAYER_DESIGNATION,
    SOURCE_METADATA,
)
from ..arcgis_client import ArcGISClient
from ..cache import ResponseCache
from ..coordinates import bng_to_wgs84, wgs84_to_bng
from .base import BaseSourceAdapter, PaginatedResult, SourceCapabilities

logger = logging.getLogger(__name__)


class NHLEAdapter(BaseSourceAdapter):
    """Adapter for the National Heritage List for England (NHLE).

    Queries the ArcGIS Feature Service hosted by Historic England.
    Supports spatial queries, text search, designation filtering,
    grade filtering, and pagination.
    """

    @property
    def source_id(self) -> str:
        return "nhle"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_spatial_query=True,
            supports_text_search=True,
            supports_feature_count=True,
            supports_attribute_filter=True,
            supports_pagination=True,
            supported_designation_types=DESIGNATION_TYPES,
        )

    def __init__(self, cache: ResponseCache | None = None) -> None:
        meta = SOURCE_METADATA["nhle"]
        self._client = ArcGISClient(
            base_url=meta["base_url"],
            cache=cache,
            cache_ttl=meta["cache_ttl_seconds"],
            cache_prefix="nhle",
        )

    async def search(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        designation_type: str | None = None,
        grade: str | None = None,
        max_results: int = 100,
        offset: int = 0,
        **kwargs: Any,
    ) -> PaginatedResult:
        """Search NHLE features.

        Args:
            query: Text search on Name field (partial, case-insensitive).
            bbox: Bounding box as (xmin, ymin, xmax, ymax) in BNG.
            lat, lon: WGS84 point for radius search.
            radius_m: Radius in metres (requires lat/lon).
            designation_type: Filter by type (e.g. 'scheduled_monument').
            grade: Filter by listing grade ('I', 'II*', 'II').
            max_results: Max features to return.
            offset: Pagination offset.
        """
        # Determine which layers to query
        layers = self._resolve_layers(designation_type)

        # Build spatial geometry
        geometry = self._build_geometry(bbox, lat, lon, radius_m)

        # Build WHERE clause
        where = self._build_where(query, grade)

        # Query each layer and merge results
        all_features: list[dict[str, Any]] = []
        total_count = 0

        if len(layers) == 1:
            # Single layer — straightforward
            layer_id = layers[0]
            count = await self._client.count(
                layer_id=layer_id,
                where=where,
                geometry=geometry,
            )
            total_count = count

            result = await self._client.query(
                layer_id=layer_id,
                where=where,
                geometry=geometry,
                out_sr=27700,
                result_offset=offset,
                result_record_count=max_results,
            )
            raw_features = result.get("features", [])
            for f in raw_features:
                all_features.append(self._normalize_feature(f, layer_id))
        else:
            # Multiple layers — query in parallel
            tasks = [
                self._client.count(layer_id=lid, where=where, geometry=geometry) for lid in layers
            ]
            counts = await asyncio.gather(*tasks, return_exceptions=True)
            for c in counts:
                if isinstance(c, int):
                    total_count += c

            # Distribute offset and max_results across layers
            remaining_offset = offset
            remaining_results = max_results

            for layer_id in layers:
                if remaining_results <= 0:
                    break

                layer_count = await self._client.count(
                    layer_id=layer_id,
                    where=where,
                    geometry=geometry,
                )

                if remaining_offset >= layer_count:
                    remaining_offset -= layer_count
                    continue

                result = await self._client.query(
                    layer_id=layer_id,
                    where=where,
                    geometry=geometry,
                    out_sr=27700,
                    result_offset=remaining_offset,
                    result_record_count=remaining_results,
                )
                raw_features = result.get("features", [])
                for f in raw_features:
                    all_features.append(self._normalize_feature(f, layer_id))

                remaining_offset = 0
                remaining_results -= len(raw_features)

        has_more = (offset + len(all_features)) < total_count
        next_offset = (offset + len(all_features)) if has_more else None

        return PaginatedResult(
            features=all_features,
            total_count=total_count,
            has_more=has_more,
            next_offset=next_offset,
        )

    async def get_by_id(self, record_id: str) -> dict[str, Any] | None:
        """Get a single NHLE record by list entry number."""
        entry_number = record_id.replace("nhle:", "")
        where = f"ListEntry = '{entry_number}'"

        # Try each layer until found
        for layer_id in ALL_NHLE_POINT_LAYERS:
            result = await self._client.query(
                layer_id=layer_id,
                where=where,
                out_sr=27700,
                result_record_count=1,
            )
            features = result.get("features", [])
            if features:
                return self._normalize_feature(features[0], layer_id)

        return None

    async def count(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        designation_type: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Fast count of features (no geometry returned)."""
        layers = self._resolve_layers(designation_type)
        geometry = self._build_geometry(bbox)
        where = self._build_where(kwargs.get("query"), kwargs.get("grade"))

        if len(layers) == 1:
            return await self._client.count(layer_id=layers[0], where=where, geometry=geometry)

        tasks = [self._client.count(layer_id=lid, where=where, geometry=geometry) for lid in layers]
        counts = await asyncio.gather(*tasks, return_exceptions=True)
        return sum(c for c in counts if isinstance(c, int))

    async def close(self) -> None:
        """Close the ArcGIS client."""
        await self._client.close()

    # ================================================================
    # Private helpers
    # ================================================================

    @staticmethod
    def _epoch_ms_to_date(value: Any) -> str | None:
        """Convert ArcGIS epoch-ms timestamp to ISO date string."""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        try:
            dt = datetime.datetime.fromtimestamp(int(value) / 1000, tz=datetime.timezone.utc)
            return dt.strftime("%Y-%m-%d")
        except (ValueError, TypeError, OSError):
            return str(value)

    def _resolve_layers(self, designation_type: str | None) -> list[int]:
        """Determine which NHLE layers to query."""
        if designation_type and designation_type in DESIGNATION_LAYERS:
            return DESIGNATION_LAYERS[designation_type]
        return ALL_NHLE_POINT_LAYERS

    def _build_geometry(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
    ) -> dict[str, Any] | None:
        """Build ArcGIS envelope geometry from bbox or point+radius."""
        if bbox is not None:
            return ArcGISClient.make_envelope(*bbox)

        if lat is not None and lon is not None and radius_m is not None:
            easting, northing = wgs84_to_bng(lat, lon)
            return ArcGISClient.make_envelope(
                easting - radius_m,
                northing - radius_m,
                easting + radius_m,
                northing + radius_m,
            )

        return None

    def _build_where(
        self,
        query: str | None = None,
        grade: str | None = None,
    ) -> str:
        """Build ArcGIS WHERE clause from filters."""
        clauses: list[str] = []

        if query:
            safe_query = query.replace("'", "''")
            clauses.append(f"Name LIKE '%{safe_query}%'")

        if grade:
            safe_grade = grade.replace("'", "''")
            clauses.append(f"Grade = '{safe_grade}'")

        return " AND ".join(clauses) if clauses else "1=1"

    def _normalize_feature(self, feature: dict[str, Any], layer_id: int) -> dict[str, Any]:
        """Map ArcGIS feature to normalised heritage asset dict."""
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        # Extract coordinates
        lat = None
        lon = None
        easting = None
        northing = None

        if geom and geom.get("coordinates"):
            coords = geom["coordinates"]
            if geom["type"] == "Point":
                easting, northing = coords[0], coords[1]
            elif geom["type"] == "MultiPoint" and coords:
                # Listed building points — use first point
                easting, northing = coords[0][0], coords[0][1]
            elif geom["type"] in ("Polygon", "MultiPolygon"):
                # Use centroid of first ring
                ring = coords[0] if geom["type"] == "Polygon" else coords[0][0]
                if ring:
                    easting = sum(c[0] for c in ring) / len(ring)
                    northing = sum(c[1] for c in ring) / len(ring)

        if easting is not None and northing is not None:
            lat, lon = bng_to_wgs84(easting, northing)

        entry = props.get("ListEntry") or props.get("list_entry") or ""
        designation = LAYER_DESIGNATION.get(layer_id, "unknown")

        result: dict[str, Any] = {
            "record_id": f"nhle:{entry}",
            "nhle_id": str(entry),
            "name": props.get("Name") or props.get("name") or "",
            "source": "nhle",
            "designation_type": designation,
            "grade": props.get("Grade") or props.get("grade"),
            "list_date": self._epoch_ms_to_date(props.get("ListDate") or props.get("list_date")),
            "amendment_date": self._epoch_ms_to_date(
                props.get("AmendDate") or props.get("amend_date")
            ),
            "url": props.get("HyperLink") or props.get("hyperlink"),
        }

        if easting is not None:
            result["easting"] = round(easting, 1)
            result["northing"] = round(northing, 1)
        if lat is not None:
            result["lat"] = round(lat, 6)
            result["lon"] = round(lon, 6)

        # Include NGR if present
        ngr = props.get("NGR") or props.get("ngr")
        if ngr:
            result["ngr"] = ngr

        return result
