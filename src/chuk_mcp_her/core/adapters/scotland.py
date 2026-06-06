"""
Scotland (Historic Environment Scotland) adapter.

Queries two ArcGIS MapServer endpoints at inspire.hes.scot:
1. Canmore Points — 320,000+ NRHE records (terrestrial and maritime)
2. HES Designations — listed buildings, scheduled monuments, gardens,
   battlefields, world heritage sites, conservation areas

Both use SRID 27700 (BNG) and return GeoJSON. These are MapServer
endpoints (not FeatureServer): no offset pagination and no
returnCountOnly.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from ...constants import (
    ALL_SCOTLAND_DESIGNATION_POINT_LAYERS,
    SCOTLAND_DESIGNATION_LAYERS,
    SCOTLAND_DESIGNATION_TYPES,
    SCOTLAND_LAYER_DESIGNATION,
    SOURCE_METADATA,
    ScotlandNRHELayer,
)
from ..arcgis_client import ArcGISClient
from ..cache import ResponseCache
from ..coordinates import bng_to_wgs84, wgs84_to_bng
from .base import BaseSourceAdapter, PaginatedResult, SourceCapabilities

logger = logging.getLogger(__name__)

# MapServer endpoints
_NRHE_BASE_URL = "https://inspire.hes.scot/arcgis/rest/services/CANMORE/Canmore_Points/MapServer"
_DESIGNATIONS_BASE_URL = (
    "https://inspire.hes.scot/arcgis/rest/services/HES/HES_Designations/MapServer"
)


class ScotlandAdapter(BaseSourceAdapter):
    """Adapter for Historic Environment Scotland.

    Provides access to the National Record of the Historic Environment
    (NRHE) via Canmore Points and to Scottish designated heritage assets
    via HES Designations.
    """

    @property
    def source_id(self) -> str:
        return "scotland"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_spatial_query=True,
            supports_text_search=True,
            supports_feature_count=False,  # MapServer: no returnCountOnly
            supports_attribute_filter=True,
            supports_pagination=False,  # MapServer: no resultOffset
            supported_designation_types=SCOTLAND_DESIGNATION_TYPES,
        )

    def __init__(self, cache: ResponseCache | None = None) -> None:
        meta = SOURCE_METADATA["scotland"]
        cache_ttl = meta["cache_ttl_seconds"]

        self._nrhe_client = ArcGISClient(
            base_url=_NRHE_BASE_URL,
            cache=cache,
            cache_ttl=cache_ttl,
            cache_prefix="scotland_nrhe",
        )
        self._designations_client = ArcGISClient(
            base_url=_DESIGNATIONS_BASE_URL,
            cache=cache,
            cache_ttl=cache_ttl,
            cache_prefix="scotland_des",
        )

    # ================================================================
    # NRHE search (Canmore Points)
    # ================================================================

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
        """Search NRHE records (Canmore Points).

        Args:
            query: Text search on NMRSNAME (partial, case-insensitive).
            bbox: Bounding box as (xmin, ymin, xmax, ymax) in BNG.
            lat, lon: WGS84 point for radius search.
            radius_m: Radius in metres (requires lat/lon).
            designation_type: Unused for NRHE search.
            grade: Unused for NRHE search.
            max_results: Max features to return (max 1000).
            offset: Unused (MapServer does not support pagination).
            **kwargs: site_type, broad_class, council — NRHE filters.
        """
        layer_id = int(ScotlandNRHELayer.TERRESTRIAL)
        geometry = self._build_geometry(bbox, lat, lon, radius_m)
        where = self._build_nrhe_where(
            query,
            kwargs.get("site_type"),
            kwargs.get("broad_class"),
            kwargs.get("council"),
        )

        result = await self._nrhe_client.query(
            layer_id=layer_id,
            where=where,
            geometry=geometry,
            out_sr=27700,
            result_record_count=max_results,
            supports_pagination=False,
        )

        features = [self._normalize_nrhe_feature(f) for f in result.get("features", [])]

        has_more = len(features) >= max_results

        return PaginatedResult(
            features=features,
            total_count=len(features),
            has_more=has_more,
            next_offset=None,
        )

    # ================================================================
    # Designation search (HES Designations)
    # ================================================================

    async def search_designations(
        self,
        designation_type: str | None = None,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 100,
        **kwargs: Any,
    ) -> PaginatedResult:
        """Search Scottish designated heritage assets.

        Args:
            designation_type: Filter by type (e.g. 'scheduled_monument').
            query: Text search on DES_TITLE (partial, case-insensitive).
            bbox: Bounding box as (xmin, ymin, xmax, ymax) in BNG.
            lat, lon: WGS84 point for radius search.
            radius_m: Radius in metres (requires lat/lon).
            max_results: Max features to return.
        """
        layers = self._resolve_designation_layers(designation_type)
        geometry = self._build_geometry(bbox, lat, lon, radius_m)
        where = self._build_designation_where(query)

        async def _query_layer(layer_id: int) -> list[dict[str, Any]]:
            result = await self._designations_client.query(
                layer_id=layer_id,
                where=where,
                geometry=geometry,
                out_sr=27700,
                result_record_count=max_results,
                supports_pagination=False,
            )
            return [
                self._normalize_designation_feature(f, layer_id) for f in result.get("features", [])
            ]

        layer_results = await asyncio.gather(*[_query_layer(lid) for lid in layers])

        all_features: list[dict[str, Any]] = []
        for features in layer_results:
            all_features.extend(features)
            if len(all_features) >= max_results:
                all_features = all_features[:max_results]
                break

        has_more = len(all_features) >= max_results

        return PaginatedResult(
            features=all_features,
            total_count=len(all_features),
            has_more=has_more,
            next_offset=None,
        )

    # ================================================================
    # Get by ID
    # ================================================================

    async def get_by_id(self, record_id: str) -> dict[str, Any] | None:
        """Get a single NRHE record by Canmore ID."""
        canmore_id = record_id.replace("scotland:", "")
        where = f"CANMOREID = '{canmore_id}'"

        # Search terrestrial first, then maritime
        for layer_id in [
            int(ScotlandNRHELayer.TERRESTRIAL),
            int(ScotlandNRHELayer.MARITIME),
        ]:
            result = await self._nrhe_client.query(
                layer_id=layer_id,
                where=where,
                out_sr=27700,
                result_record_count=1,
                supports_pagination=False,
            )
            features = result.get("features", [])
            if features:
                return self._normalize_nrhe_feature(features[0])

        return None

    async def close(self) -> None:
        """Close both ArcGIS clients."""
        await self._nrhe_client.close()
        await self._designations_client.close()

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
    def _build_nrhe_where(
        query: str | None = None,
        site_type: str | None = None,
        broad_class: str | None = None,
        council: str | None = None,
    ) -> str:
        """Build WHERE clause for NRHE (Canmore Points) queries."""
        clauses: list[str] = []

        if query:
            safe = query.replace("'", "''")
            clauses.append(f"NMRSNAME LIKE '%{safe}%'")

        if site_type:
            safe = site_type.replace("'", "''")
            clauses.append(f"SITETYPE LIKE '%{safe}%'")

        if broad_class:
            safe = broad_class.replace("'", "''")
            clauses.append(f"BROADCLASS LIKE '%{safe}%'")

        if council:
            safe = council.replace("'", "''")
            clauses.append(f"COUNCIL LIKE '%{safe}%'")

        return " AND ".join(clauses) if clauses else "1=1"

    @staticmethod
    def _build_designation_where(query: str | None = None) -> str:
        """Build WHERE clause for HES Designations queries."""
        if query:
            safe = query.replace("'", "''")
            return f"DES_TITLE LIKE '%{safe}%'"
        return "1=1"

    @staticmethod
    def _resolve_designation_layers(
        designation_type: str | None,
    ) -> list[int]:
        """Determine which HES Designation layers to query."""
        if designation_type and designation_type in SCOTLAND_DESIGNATION_LAYERS:
            return SCOTLAND_DESIGNATION_LAYERS[designation_type]
        return ALL_SCOTLAND_DESIGNATION_POINT_LAYERS

    def _normalize_nrhe_feature(self, feature: dict[str, Any]) -> dict[str, Any]:
        """Map Canmore Points feature to normalised dict."""
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        easting, northing, lat, lon = self._extract_coordinates(geom, props)

        canmore_id = props.get("CANMOREID") or props.get("canmoreid") or ""

        result: dict[str, Any] = {
            "record_id": f"scotland:{canmore_id}",
            "canmore_id": str(canmore_id),
            "site_number": props.get("SITENUMBER") or props.get("sitenumber"),
            "name": props.get("NMRSNAME") or props.get("nmrsname") or "",
            "alt_name": props.get("ALTNAME") or props.get("altname"),
            "source": "scotland",
            "broad_class": props.get("BROADCLASS") or props.get("broadclass"),
            "site_type": props.get("SITETYPE") or props.get("sitetype"),
            "form": props.get("FORM") or props.get("form"),
            "county": props.get("COUNTY") or props.get("county"),
            "council": props.get("COUNCIL") or props.get("council"),
            "parish": props.get("PARISH") or props.get("parish"),
            "grid_reference": props.get("GRIDREF") or props.get("gridref"),
            "url": props.get("URL") or props.get("url"),
        }

        if easting is not None:
            result["easting"] = round(easting, 1)
            result["northing"] = round(northing, 1)
        if lat is not None:
            result["lat"] = round(lat, 6)
            result["lon"] = round(lon, 6)

        return result

    def _normalize_designation_feature(
        self, feature: dict[str, Any], layer_id: int
    ) -> dict[str, Any]:
        """Map HES Designation feature to normalised dict."""
        props = feature.get("properties", {})
        geom = feature.get("geometry")

        easting, northing, lat, lon = self._extract_coordinates(geom, props)

        des_ref = props.get("DES_REF") or props.get("des_ref") or ""
        designation = SCOTLAND_LAYER_DESIGNATION.get(layer_id, "unknown")

        result: dict[str, Any] = {
            "record_id": f"scotland_des:{des_ref}",
            "designation_reference": str(des_ref),
            "name": props.get("DES_TITLE") or props.get("des_title") or "",
            "source": "scotland",
            "designation_type": designation,
            "category": props.get("CATEGORY") or props.get("category"),
            "designated_date": props.get("DESIGNATED") or props.get("designated"),
            "local_authority": props.get("LOCAL_AUTH") or props.get("local_auth"),
            "url": props.get("LINK") or props.get("link"),
        }

        if easting is not None:
            result["easting"] = round(easting, 1)
            result["northing"] = round(northing, 1)
        if lat is not None:
            result["lat"] = round(lat, 6)
            result["lon"] = round(lon, 6)

        return result

    @staticmethod
    def _extract_coordinates(
        geom: dict[str, Any] | None,
        props: dict[str, Any],
    ) -> tuple[float | None, float | None, float | None, float | None]:
        """Extract easting/northing from geometry or properties.

        Returns (easting, northing, lat, lon).
        """
        easting = None
        northing = None
        lat = None
        lon = None

        # Try geometry first
        if geom and geom.get("coordinates"):
            coords = geom["coordinates"]
            if geom["type"] == "Point":
                easting, northing = coords[0], coords[1]
            elif geom["type"] == "MultiPoint" and coords:
                easting, northing = coords[0][0], coords[0][1]
            elif geom["type"] in ("Polygon", "MultiPolygon"):
                ring = coords[0] if geom["type"] == "Polygon" else coords[0][0] if coords[0] else []
                if ring:
                    easting = sum(c[0] for c in ring) / len(ring)
                    northing = sum(c[1] for c in ring) / len(ring)

        # Fallback to XCOORD/YCOORD in properties
        if easting is None:
            x = props.get("XCOORD") or props.get("xcoord") or props.get("X") or props.get("x")
            y = props.get("YCOORD") or props.get("ycoord") or props.get("Y") or props.get("y")
            if x is not None and y is not None:
                try:
                    easting, northing = float(x), float(y)
                except (ValueError, TypeError):
                    pass

        # Convert to WGS84
        if easting is not None and northing is not None:
            lat, lon = bng_to_wgs84(easting, northing)

        return easting, northing, lat, lon
