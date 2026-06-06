"""
Conservation Area adapter.

Queries the Historic England Conservation Areas ArcGIS Feature Service
for areas of special architectural or historic interest designated by
Local Planning Authorities across England. Layer 0 contains 8,000+
polygon features with name, LPA, designation date, and centroid
coordinates.
"""

from __future__ import annotations

import logging
from typing import Any

from ...constants import ErrorMessages, SOURCE_METADATA
from ..arcgis_client import ArcGISClient
from ..cache import ResponseCache
from ..coordinates import bng_to_wgs84, wgs84_to_bng
from .base import BaseSourceAdapter, PaginatedResult, SourceCapabilities

logger = logging.getLogger(__name__)


class ConservationAreaAdapter(BaseSourceAdapter):
    """Adapter for Conservation Areas in England.

    Queries the ArcGIS Feature Service hosted by Historic England.
    Supports spatial queries, text search on name and LPA,
    feature counting, and pagination.
    """

    @property
    def source_id(self) -> str:
        return "conservation_area"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_spatial_query=True,
            supports_text_search=True,
            supports_feature_count=True,
            supports_pagination=True,
        )

    def __init__(self, cache: ResponseCache | None = None) -> None:
        meta = SOURCE_METADATA["conservation_area"]
        self._client = ArcGISClient(
            base_url=meta["base_url"],
            cache=cache,
            cache_ttl=meta["cache_ttl_seconds"],
            cache_prefix="ca",
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
        """Search conservation areas.

        Args:
            query: Text search on NAME field (partial, case-insensitive).
            bbox: Bounding box as (xmin, ymin, xmax, ymax) in BNG.
            lat, lon: WGS84 point for radius search.
            radius_m: Radius in metres (requires lat/lon).
            designation_type: Unused (all features are conservation areas).
            grade: Unused (conservation areas have no grade).
            max_results: Max features to return.
            offset: Pagination offset.
            **kwargs: lpa — additional conservation-area-specific filter.
        """
        layer_id = 0
        geometry = self._build_geometry(bbox, lat, lon, radius_m)
        where = self._build_where(query, kwargs.get("lpa"))

        total_count = await self._client.count(
            layer_id=layer_id,
            where=where,
            geometry=geometry,
        )

        result = await self._client.query(
            layer_id=layer_id,
            where=where,
            geometry=geometry,
            out_sr=27700,
            result_offset=offset,
            result_record_count=max_results,
        )

        features = [self._normalize_feature(f) for f in result.get("features", [])]

        has_more = (offset + len(features)) < total_count
        next_offset = (offset + len(features)) if has_more else None

        return PaginatedResult(
            features=features,
            total_count=total_count,
            has_more=has_more,
            next_offset=next_offset,
        )

    async def get_by_id(self, record_id: str) -> dict[str, Any] | None:
        """Get a single conservation area by UID."""
        uid = record_id.replace("ca:", "")
        where = f"UID = {int(uid)}"

        result = await self._client.query(
            layer_id=0,
            where=where,
            out_sr=27700,
            result_record_count=1,
        )
        features = result.get("features", [])
        if features:
            return self._normalize_feature(features[0])

        return None

    async def count(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        designation_type: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Fast count of conservation areas (no geometry returned)."""
        geometry = self._build_geometry(bbox)
        where = self._build_where(kwargs.get("query"), kwargs.get("lpa"))
        return await self._client.count(layer_id=0, where=where, geometry=geometry)

    async def close(self) -> None:
        """Close the ArcGIS client."""
        await self._client.close()

    # ================================================================
    # Private helpers
    # ================================================================

    @staticmethod
    def _build_geometry(
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

    @staticmethod
    def _build_where(
        query: str | None = None,
        lpa: str | None = None,
    ) -> str:
        """Build ArcGIS WHERE clause from filters.

        Uses LIKE for NAME and LPA because searches should be
        partial and case-insensitive.
        """
        clauses: list[str] = []

        if query:
            safe = query.replace("'", "''")
            clauses.append(f"NAME LIKE '%{safe}%'")

        if lpa:
            safe = lpa.replace("'", "''")
            clauses.append(f"LPA LIKE '%{safe}%'")

        return " AND ".join(clauses) if clauses else "1=1"

    @staticmethod
    def _normalize_feature(
        feature: dict[str, Any],
    ) -> dict[str, Any]:
        """Map ArcGIS conservation area feature to normalised dict."""
        props = feature.get("properties", {})

        uid = props.get("UID") or props.get("OBJECTID") or ""
        easting = props.get("x")
        northing = props.get("y")

        lat = None
        lon = None
        if easting is not None and northing is not None:
            lat, lon = bng_to_wgs84(easting, northing)

        result: dict[str, Any] = {
            "record_id": f"ca:{uid}",
            "uid": uid,
            "name": props.get("NAME") or ErrorMessages.UNKNOWN_CONSERVATION_AREA,
            "source": "conservation_area",
            "lpa": props.get("LPA"),
            "designation_date": props.get("DATE_OF_DE"),
            "easting": easting,
            "northing": northing,
        }

        if lat is not None:
            result["lat"] = round(lat, 6)
            result["lon"] = round(lon, 6)

        area = props.get("Shape__Area")
        if area is not None:
            result["area_sqm"] = area

        return result
