"""
AIM (Aerial Investigation and Mapping) adapter.

Queries the Historic England AIM ArcGIS Feature Service for
archaeological features identified from aerial photographs and LiDAR.
Layer 1 (Detailed_Mapping) contains 470,000+ polygon features with
monument type, period, evidence, HER references, and project metadata.
"""

from __future__ import annotations

import logging
from typing import Any

from ...constants import AIM_DEFAULT_SEARCH_LAYER, AIMLayer, SOURCE_METADATA
from ..arcgis_client import ArcGISClient
from ..cache import ResponseCache
from ..coordinates import bng_to_wgs84, wgs84_to_bng
from .base import BaseSourceAdapter, PaginatedResult, SourceCapabilities

logger = logging.getLogger(__name__)


class AIMAdapter(BaseSourceAdapter):
    """Adapter for Aerial Investigation and Mapping (AIM).

    Queries the ArcGIS Feature Service hosted by Historic England.
    Supports spatial queries, text search, monument type and period
    filtering, and pagination.
    """

    @property
    def source_id(self) -> str:
        return "aim"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_spatial_query=True,
            supports_text_search=True,
            supports_feature_count=True,
            supports_attribute_filter=True,
            supports_pagination=True,
        )

    def __init__(self, cache: ResponseCache | None = None) -> None:
        meta = SOURCE_METADATA["aim"]
        self._client = ArcGISClient(
            base_url=meta["base_url"],
            cache=cache,
            cache_ttl=meta["cache_ttl_seconds"],
            cache_prefix="aim",
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
        """Search AIM features.

        Args:
            query: Text search on MONUMENT_TYPE field (partial, case-insensitive).
            bbox: Bounding box as (xmin, ymin, xmax, ymax) in BNG.
            lat, lon: WGS84 point for radius search.
            radius_m: Radius in metres (requires lat/lon).
            designation_type: Unused (AIM features are undesignated).
            grade: Unused (AIM features have no grade).
            max_results: Max features to return.
            offset: Pagination offset.
            **kwargs: monument_type, period — additional AIM-specific filters.
        """
        # Coerce numeric params (may arrive as strings via MCP)
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
        radius_m = float(radius_m) if radius_m is not None else None
        max_results = int(max_results)
        offset = int(offset)

        layer_id = int(AIM_DEFAULT_SEARCH_LAYER)
        geometry = self._build_geometry(bbox, lat, lon, radius_m)
        where = self._build_where(
            query,
            kwargs.get("monument_type"),
            kwargs.get("period"),
        )

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
        """Get a single AIM record by HE_UID."""
        he_uid = record_id.replace("aim:", "")
        where = f"HE_UID = '{he_uid}'"

        # Try Detailed_Mapping first, then Monument_Extents
        for layer_id in [
            int(AIMLayer.DETAILED_MAPPING),
            int(AIMLayer.MONUMENT_EXTENTS),
        ]:
            result = await self._client.query(
                layer_id=layer_id,
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
        """Fast count of AIM features (no geometry returned)."""
        layer_id = int(AIM_DEFAULT_SEARCH_LAYER)
        geometry = self._build_geometry(bbox)
        where = self._build_where(
            kwargs.get("query"),
            kwargs.get("monument_type"),
            kwargs.get("period"),
        )
        return await self._client.count(layer_id=layer_id, where=where, geometry=geometry)

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
        monument_type: str | None = None,
        period: str | None = None,
    ) -> str:
        """Build ArcGIS WHERE clause from filters.

        Uses LIKE for monument_type and period because AIM values are
        often compound (e.g. "IRON AGE TO ROMAN", "ENCLOSURE: OVAL").
        """
        clauses: list[str] = []

        if query:
            safe = query.replace("'", "''")
            clauses.append(f"MONUMENT_TYPE LIKE '%{safe}%'")

        if monument_type:
            safe = monument_type.replace("'", "''")
            clauses.append(f"MONUMENT_TYPE LIKE '%{safe}%'")

        if period:
            safe = period.replace("'", "''")
            clauses.append(f"PERIOD LIKE '%{safe}%'")

        return " AND ".join(clauses) if clauses else "1=1"

    @staticmethod
    def _build_name(props: dict[str, Any]) -> str:
        """Generate a descriptive name from AIM properties."""
        monument = props.get("MONUMENT_TYPE") or props.get("monument_type") or ""
        period = props.get("PERIOD") or props.get("period") or ""
        if monument and period:
            return f"{monument} ({period})"
        return monument or period or "Unknown feature"

    def _normalize_feature(self, feature: dict[str, Any]) -> dict[str, Any]:
        """Map ArcGIS AIM feature to normalised heritage asset dict."""
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        # Extract centroid from polygon geometry
        easting = None
        northing = None
        lat = None
        lon = None

        if geom and geom.get("coordinates"):
            coords = geom["coordinates"]
            if geom["type"] == "Polygon" and coords:
                ring = coords[0]
                if ring:
                    easting = sum(c[0] for c in ring) / len(ring)
                    northing = sum(c[1] for c in ring) / len(ring)
            elif geom["type"] == "MultiPolygon" and coords:
                ring = coords[0][0] if coords[0] else []
                if ring:
                    easting = sum(c[0] for c in ring) / len(ring)
                    northing = sum(c[1] for c in ring) / len(ring)
            elif geom["type"] == "Point":
                easting, northing = coords[0], coords[1]

        if easting is not None and northing is not None:
            lat, lon = bng_to_wgs84(easting, northing)

        he_uid = props.get("HE_UID") or props.get("he_uid") or props.get("OBJECTID") or ""

        result: dict[str, Any] = {
            "record_id": f"aim:{he_uid}",
            "aim_id": str(he_uid),
            "name": self._build_name(props),
            "source": "aim",
            "monument_type": props.get("MONUMENT_TYPE") or props.get("monument_type"),
            "broad_type": props.get("BROAD_TYPE") or props.get("broad_type"),
            "narrow_type": props.get("NARROW_TYPE") or props.get("narrow_type"),
            "period": props.get("PERIOD") or props.get("period"),
            "form": props.get("FORM") or props.get("form"),
            "evidence": props.get("EVIDENCE_1") or props.get("evidence_1"),
            "project": props.get("PROJECT") or props.get("project"),
            "her_no": props.get("HER_NO") or props.get("her_no"),
        }

        if easting is not None:
            result["easting"] = round(easting, 1)
            result["northing"] = round(northing, 1)
        if lat is not None:
            result["lat"] = round(lat, 6)
            result["lon"] = round(lon, 6)

        return result
