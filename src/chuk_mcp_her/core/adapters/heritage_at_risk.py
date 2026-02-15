"""
Heritage at Risk Register adapter.

Queries the Historic England Heritage at Risk ArcGIS Feature Service
for heritage assets at risk of loss through neglect, decay, or
inappropriate development.  Layer 0 contains ~4,877 polygon features
covering scheduled monuments, listed buildings, conservation areas,
parks and gardens, battlefields, and protected wreck sites.

IMPORTANT: This service uses SRID 3857 (Web Mercator), NOT 27700 (BNG).
We pass ``in_sr=27700`` so ArcGIS reprojects our BNG envelopes, and
``out_sr=27700`` so we get BNG coordinates back for centroid conversion.
"""

from __future__ import annotations

import logging
from typing import Any

from ...constants import SOURCE_METADATA
from ..arcgis_client import ArcGISClient
from ..cache import ResponseCache
from ..coordinates import bng_to_wgs84, wgs84_to_bng
from .base import BaseSourceAdapter, PaginatedResult, SourceCapabilities

logger = logging.getLogger(__name__)


class HeritageAtRiskAdapter(BaseSourceAdapter):
    """Adapter for the Heritage at Risk Register.

    Queries the ArcGIS Feature Service hosted by Historic England.
    Supports spatial queries, text search, heritage category filtering,
    and pagination.
    """

    @property
    def source_id(self) -> str:
        return "heritage_at_risk"

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
        meta = SOURCE_METADATA["heritage_at_risk"]
        self._client = ArcGISClient(
            base_url=meta["base_url"],
            cache=cache,
            cache_ttl=meta["cache_ttl_seconds"],
            cache_prefix="har",
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
        """Search Heritage at Risk features.

        Args:
            query: Text search on EntryName field (partial, case-insensitive).
            bbox: Bounding box as (xmin, ymin, xmax, ymax) in BNG.
            lat, lon: WGS84 point for radius search.
            radius_m: Radius in metres (requires lat/lon).
            designation_type: Unused (use heritage_category instead).
            grade: Unused (HAR features have no grade).
            max_results: Max features to return.
            offset: Pagination offset.
            **kwargs: heritage_category -- additional HAR-specific filter.
        """
        layer_id = 0
        geometry = self._build_geometry(bbox, lat, lon, radius_m)
        where = self._build_where(
            query,
            kwargs.get("heritage_category"),
        )

        total_count = await self._client.count(
            layer_id=layer_id,
            where=where,
            geometry=geometry,
            in_sr=27700,
        )

        result = await self._client.query(
            layer_id=layer_id,
            where=where,
            geometry=geometry,
            in_sr=27700,
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
        """Get a single Heritage at Risk record by List_Entry or uid."""
        raw_id = record_id.replace("har:", "")
        layer_id = 0

        # Try as integer List_Entry first, then as uid string
        if raw_id.isdigit():
            where = f"List_Entry = {raw_id}"
        else:
            safe = raw_id.replace("'", "''")
            where = f"uid = '{safe}'"

        result = await self._client.query(
            layer_id=layer_id,
            where=where,
            in_sr=27700,
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
        """Fast count of Heritage at Risk features (no geometry returned)."""
        layer_id = 0
        geometry = self._build_geometry(bbox)
        where = self._build_where(
            kwargs.get("query"),
            kwargs.get("heritage_category"),
        )
        return await self._client.count(
            layer_id=layer_id,
            where=where,
            geometry=geometry,
            in_sr=27700,
        )

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
        """Build ArcGIS envelope geometry from bbox or point+radius.

        All envelopes are in BNG (EPSG:27700).  We pass ``in_sr=27700``
        in every query call so ArcGIS reprojects to the layer's native
        SRID 3857 on the server side.
        """
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
        heritage_category: str | None = None,
    ) -> str:
        """Build ArcGIS WHERE clause from filters.

        Uses LIKE for query (free-text on EntryName) and exact match
        for heritage_category (HeritageCa).
        """
        clauses: list[str] = []

        if query:
            safe = query.replace("'", "''")
            clauses.append(f"EntryName LIKE '%{safe}%'")

        if heritage_category:
            safe = heritage_category.replace("'", "''")
            clauses.append(f"HeritageCa = '{safe}'")

        return " AND ".join(clauses) if clauses else "1=1"

    @staticmethod
    def _normalize_feature(
        feature: dict[str, Any],
    ) -> dict[str, Any]:
        """Map ArcGIS HAR feature to normalised heritage asset dict."""
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        # Extract centroid from polygon geometry (returned in BNG via out_sr=27700)
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

        list_entry = props.get("List_Entry") or props.get("list_entry")
        fid = props.get("FID") or props.get("OBJECTID")
        record_key = list_entry if list_entry else fid

        result: dict[str, Any] = {
            "record_id": f"har:{record_key}",
            "list_entry": list_entry,
            "name": props.get("EntryName") or props.get("entryname") or "Unknown",
            "source": "heritage_at_risk",
            "heritage_category": props.get("HeritageCa") or props.get("heritageCA"),
            "risk_methodology": props.get("Risk_Metho") or props.get("risk_metho"),
            "area_sqm": props.get("Shape_Area") or props.get("shape_area"),
            "url": props.get("URL") or props.get("url"),
        }

        if easting is not None:
            result["easting"] = round(easting, 1)
            result["northing"] = round(northing, 1)
        if lat is not None:
            result["lat"] = round(lat, 6)
            result["lon"] = round(lon, 6)

        return result
