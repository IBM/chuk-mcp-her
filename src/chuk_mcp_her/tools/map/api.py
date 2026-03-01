"""Map tools — multi-layer heritage map and cross-reference visualisation."""

from __future__ import annotations

import asyncio
import logging
import math
from collections import defaultdict
from typing import Any

from chuk_view_schemas import LayerStyle, MapContent, MapLayer, PopupTemplate
from chuk_view_schemas.chuk_mcp import map_tool
from chuk_view_schemas.map import ClusterConfig, MapCenter, MapControls

from ...constants import ErrorMessages
from ...core.coordinates import bbox_wgs84_to_bng, bng_to_wgs84

logger = logging.getLogger(__name__)


# ============================================================================
# Styling constants
# ============================================================================

_NHLE_STYLE: dict[str, LayerStyle] = {
    "listed_building": LayerStyle(
        color="#2563eb", fill_color="#2563eb", fill_opacity=0.85, radius=6
    ),
    "scheduled_monument": LayerStyle(
        color="#92400e", fill_color="#b45309", fill_opacity=0.85, radius=7
    ),
    "park_and_garden": LayerStyle(
        color="#15803d", fill_color="#16a34a", fill_opacity=0.8, radius=6
    ),
    "battlefield": LayerStyle(color="#991b1b", fill_color="#dc2626", fill_opacity=0.85, radius=6),
    "protected_wreck": LayerStyle(
        color="#1e3a5f", fill_color="#1d4ed8", fill_opacity=0.85, radius=6
    ),
    "world_heritage_site": LayerStyle(
        color="#92400e", fill_color="#fbbf24", fill_opacity=0.95, radius=10, weight=2
    ),
}
_DEFAULT_NHLE_STYLE = LayerStyle(color="#2563eb", fill_color="#2563eb", fill_opacity=0.8, radius=6)

_SOURCE_STYLE: dict[str, LayerStyle] = {
    "aim": LayerStyle(color="#7c3aed", fill_color="#a78bfa", fill_opacity=0.8, radius=5),
    "conservation_area": LayerStyle(
        color="#065f46", fill_color="#34d399", fill_opacity=0.8, radius=6
    ),
    "heritage_at_risk": LayerStyle(
        color="#b91c1c", fill_color="#f87171", fill_opacity=0.9, radius=7, weight=2
    ),
    "scotland": LayerStyle(color="#0e7490", fill_color="#22d3ee", fill_opacity=0.8, radius=6),
}

_CROSSREF_STYLE: dict[str, LayerStyle] = {
    "match": LayerStyle(
        color="#15803d", fill_color="#4ade80", fill_opacity=0.95, radius=8, weight=2
    ),
    "near": LayerStyle(color="#b45309", fill_color="#fb923c", fill_opacity=0.9, radius=7, weight=2),
    "novel": LayerStyle(
        color="#b91c1c", fill_color="#f87171", fill_opacity=0.9, radius=7, weight=2
    ),
    "known": LayerStyle(color="#475569", fill_color="#94a3b8", fill_opacity=0.6, radius=4),
}

_NHLE_LABELS: dict[str, str] = {
    "listed_building": "Listed Buildings (NHLE)",
    "scheduled_monument": "Scheduled Monuments (NHLE)",
    "park_and_garden": "Parks & Gardens (NHLE)",
    "battlefield": "Battlefields (NHLE)",
    "protected_wreck": "Protected Wrecks (NHLE)",
    "world_heritage_site": "World Heritage Sites (NHLE)",
}

_SOURCE_LABELS: dict[str, str] = {
    "aim": "Aerial Mapping (AIM)",
    "conservation_area": "Conservation Areas",
    "heritage_at_risk": "Heritage at Risk",
    "scotland": "Scottish Sites (NRHE)",
}


# ============================================================================
# Private helpers
# ============================================================================


def _zoom_from_radius_m(radius_m: float) -> int:
    """Compute a sensible zoom level from a search radius in metres."""
    return max(8, min(17, round(16 - math.log2(max(radius_m, 50) / 50))))


def _zoom_from_wgs84_extent(lat_extent: float, lon_extent: float) -> int:
    """Compute a sensible zoom level from a WGS84 bounding box extent."""
    extent = max(lat_extent, lon_extent, 0.001)
    return max(7, min(16, round(10 - math.log2(extent))))


def _to_geojson(features: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert normalised heritage dicts to a GeoJSON FeatureCollection.

    Features without lat/lon are silently skipped.
    """
    items = []
    for f in features:
        lat = f.get("lat")
        lon = f.get("lon")
        if lat is None or lon is None:
            continue
        props = {k: v for k, v in f.items() if k not in ("lat", "lon") and v is not None}
        items.append(
            {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [lon, lat]},
                "properties": props,
            }
        )
    return {"type": "FeatureCollection", "features": items}


# ============================================================================
# Tool registration
# ============================================================================


def register_map_tools(mcp: object, registry: object) -> None:
    """Register map visualisation tools with the MCP server."""

    @map_tool(  # type: ignore[arg-type]
        mcp,
        "her_map",
        description=(
            "Visualise heritage assets from multiple sources as a multi-layer interactive map. "
            "Returns a structured map view with colour-coded layers by designation type and source."
        ),
        read_only_hint=True,
    )
    async def her_map(
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float = 1000.0,
        sources: str | None = None,
        designation_type: str | None = None,
        basemap: str = "osm",
        max_results: int = 200,
    ) -> MapContent:
        """Visualise heritage assets from multiple sources as a multi-layer interactive map.

        Queries up to five heritage data sources in parallel and renders each as a
        distinctly styled map layer. NHLE results are split by designation type
        (listed buildings, scheduled monuments, etc.) for visual separation.

        Args:
            bbox: WGS84 bounding box "min_lon,min_lat,max_lon,max_lat"
                  (alternative to lat/lon/radius_m)
            lat: Centre latitude in WGS84 (use with lon and radius_m)
            lon: Centre longitude in WGS84 (use with lat and radius_m)
            radius_m: Search radius in metres (default 1000, max 50000)
            sources: Comma-separated source IDs to include — nhle, aim,
                     conservation_area, heritage_at_risk, scotland
                     (default: all five)
            designation_type: Filter NHLE results to one type
                              (e.g. "listed_building", "scheduled_monument")
            basemap: Map background — "osm" (default), "satellite", "terrain", "dark"
            max_results: Max results per source (default 200)

        Returns:
            Multi-layer heritage map with colour-coded layers

        Tips for LLMs:
            - Use bbox for a fixed area (e.g. a town boundary)
            - Use lat/lon/radius_m for a circular search around a point
            - Each NHLE designation type appears as a separate coloured layer
            - Toggle layers in the UI to focus on specific asset types
            - Heritage Gateway is excluded (no spatial API)
        """
        # Coerce numeric params (MCP may pass strings)
        lat = float(lat) if lat is not None else None
        lon = float(lon) if lon is not None else None
        radius_m = float(radius_m)
        max_results = int(max_results)

        # Parse enabled sources
        all_sources = {"nhle", "aim", "conservation_area", "heritage_at_risk", "scotland"}
        if sources:
            enabled = {s.strip() for s in sources.split(",") if s.strip() in all_sources}
            if not enabled:
                enabled = all_sources
        else:
            enabled = all_sources

        # Validate basemap
        valid_basemaps = ("osm", "satellite", "terrain", "dark")
        if basemap not in valid_basemaps:
            basemap = "osm"

        # Resolve spatial parameters
        bng_bbox: tuple[float, float, float, float] | None = None
        centre_lat: float
        centre_lon: float
        zoom: int

        if bbox:
            parts = [float(p.strip()) for p in bbox.split(",")]
            if len(parts) != 4:
                raise ValueError(ErrorMessages.INVALID_BBOX)
            min_lon, min_lat, max_lon, max_lat = parts
            centre_lat = (min_lat + max_lat) / 2
            centre_lon = (min_lon + max_lon) / 2
            zoom = _zoom_from_wgs84_extent(max_lat - min_lat, max_lon - min_lon)
            bng_bbox = bbox_wgs84_to_bng(min_lon, min_lat, max_lon, max_lat)
        elif lat is not None and lon is not None:
            centre_lat, centre_lon = lat, lon
            zoom = _zoom_from_radius_m(radius_m)
        else:
            raise ValueError(ErrorMessages.SPATIAL_REQUIRED)

        # Parallel fetch helpers
        _q_lat = lat if bng_bbox is None else None
        _q_lon = lon if bng_bbox is None else None
        _q_radius = radius_m if bng_bbox is None else None

        async def _fetch_nhle() -> list[dict[str, Any]]:
            if "nhle" not in enabled:
                return []
            result = await registry.search_designations(  # type: ignore[union-attr]
                bbox=bng_bbox,
                lat=_q_lat,
                lon=_q_lon,
                radius_m=_q_radius,
                designation_type=designation_type,
                max_results=max_results,
            )
            return list(result.features)

        async def _fetch_aim() -> list[dict[str, Any]]:
            if "aim" not in enabled:
                return []
            result = await registry.search_aerial(  # type: ignore[union-attr]
                bbox=bng_bbox,
                lat=_q_lat,
                lon=_q_lon,
                radius_m=_q_radius,
                max_results=max_results,
            )
            return list(result.features)

        async def _fetch_ca() -> list[dict[str, Any]]:
            if "conservation_area" not in enabled:
                return []
            result = await registry.search_conservation_areas(  # type: ignore[union-attr]
                bbox=bng_bbox,
                lat=_q_lat,
                lon=_q_lon,
                radius_m=_q_radius,
                max_results=max_results,
            )
            return list(result.features)

        async def _fetch_har() -> list[dict[str, Any]]:
            if "heritage_at_risk" not in enabled:
                return []
            result = await registry.search_heritage_at_risk(  # type: ignore[union-attr]
                bbox=bng_bbox,
                lat=_q_lat,
                lon=_q_lon,
                radius_m=_q_radius,
                max_results=max_results,
            )
            return list(result.features)

        async def _fetch_scotland() -> list[dict[str, Any]]:
            if "scotland" not in enabled:
                return []
            result = await registry.search_scotland(  # type: ignore[union-attr]
                bbox=bng_bbox,
                lat=_q_lat,
                lon=_q_lon,
                radius_m=_q_radius,
                max_results=max_results,
            )
            return list(result.features)

        nhle_fs, aim_fs, ca_fs, har_fs, scot_fs = await asyncio.gather(
            _fetch_nhle(), _fetch_aim(), _fetch_ca(), _fetch_har(), _fetch_scotland()
        )

        # Build map layers
        cluster = ClusterConfig(enabled=True, radius=40)
        layers: list[MapLayer] = []

        # NHLE — one layer per designation type
        if nhle_fs:
            by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for f in nhle_fs:
                by_type[f.get("designation_type", "other")].append(f)
            nhle_popup = PopupTemplate(
                title="{name}",
                fields=["designation_type", "grade", "list_date", "url", "record_id"],
            )
            for dt, feats in by_type.items():
                fc = _to_geojson(feats)
                if fc["features"]:
                    layers.append(
                        MapLayer(
                            id=f"nhle_{dt}",
                            label=_NHLE_LABELS.get(dt, f"NHLE: {dt}"),
                            features=fc,
                            style=_NHLE_STYLE.get(dt, _DEFAULT_NHLE_STYLE),
                            cluster=cluster,
                            popup=nhle_popup,
                        )
                    )

        # AIM
        if aim_fs:
            fc = _to_geojson(aim_fs)
            if fc["features"]:
                layers.append(
                    MapLayer(
                        id="aim",
                        label=_SOURCE_LABELS["aim"],
                        features=fc,
                        style=_SOURCE_STYLE["aim"],
                        cluster=cluster,
                        popup=PopupTemplate(
                            title="{name}",
                            fields=["monument_type", "period", "form", "evidence", "record_id"],
                        ),
                    )
                )

        # Conservation Areas
        if ca_fs:
            fc = _to_geojson(ca_fs)
            if fc["features"]:
                layers.append(
                    MapLayer(
                        id="conservation_area",
                        label=_SOURCE_LABELS["conservation_area"],
                        features=fc,
                        style=_SOURCE_STYLE["conservation_area"],
                        cluster=cluster,
                        popup=PopupTemplate(
                            title="{name}",
                            fields=["lpa", "designation_date", "area_sqm", "record_id"],
                        ),
                    )
                )

        # Heritage at Risk
        if har_fs:
            fc = _to_geojson(har_fs)
            if fc["features"]:
                layers.append(
                    MapLayer(
                        id="heritage_at_risk",
                        label=_SOURCE_LABELS["heritage_at_risk"],
                        features=fc,
                        style=_SOURCE_STYLE["heritage_at_risk"],
                        cluster=cluster,
                        popup=PopupTemplate(
                            title="{name}",
                            fields=["heritage_category", "risk_methodology", "url", "record_id"],
                        ),
                    )
                )

        # Scotland NRHE
        if scot_fs:
            fc = _to_geojson(scot_fs)
            if fc["features"]:
                layers.append(
                    MapLayer(
                        id="scotland",
                        label=_SOURCE_LABELS["scotland"],
                        features=fc,
                        style=_SOURCE_STYLE["scotland"],
                        cluster=cluster,
                        popup=PopupTemplate(
                            title="{name}",
                            fields=[
                                "site_type",
                                "broad_class",
                                "council",
                                "grid_reference",
                                "url",
                                "record_id",
                            ],
                        ),
                    )
                )

        return MapContent(
            center=MapCenter(lat=centre_lat, lon=centre_lon),
            zoom=zoom,
            basemap=basemap,  # type: ignore[arg-type]
            layers=layers,
            controls=MapControls(zoom=True, layers=True, scale=True, fullscreen=True),
        )

    @map_tool(  # type: ignore[arg-type]
        mcp,
        "her_crossref_map",
        description=(
            "Visualise cross-reference results as a colour-coded map: "
            "green (match), amber (near), red (novel), grey (known assets). "
            "Runs the same analysis as her_cross_reference."
        ),
        read_only_hint=True,
    )
    async def her_crossref_map(
        candidates: str = "[]",
        match_radius_m: float = 50.0,
        near_radius_m: float = 200.0,
        designation_types: str | None = None,
        include_aim: bool = False,
        basemap: str = "osm",
    ) -> MapContent:
        """Visualise LiDAR cross-reference results as a colour-coded heritage map.

        Runs the same cross-reference analysis as her_cross_reference, then renders
        candidates and known assets as four colour-coded map layers:
        - Green:  candidates that match a known heritage asset (within match_radius_m)
        - Amber:  candidates near a known asset (within near_radius_m)
        - Red:    novel candidates with no known asset in range
        - Grey:   known heritage assets in the survey area (NHLE, optionally AIM)

        Args:
            candidates: JSON array of {"easting": x, "northing": y, "name": "..."} dicts
                        (BNG coordinates). Name field is optional but recommended.
            match_radius_m: Distance threshold for "match" classification (default 50m)
            near_radius_m: Distance threshold for "near" classification (default 200m)
            designation_types: Comma-separated NHLE designation types to match against
                               (e.g. "scheduled_monument,listed_building")
            include_aim: Include AIM aerial mapping in the known asset set (default false)
            basemap: Map background — "osm" (default), "satellite", "terrain", "dark"

        Returns:
            Four-layer colour-coded cross-reference map

        Tips for LLMs:
            - Input candidates as BNG easting/northing (same format as her_cross_reference)
            - Red (novel) candidates are potential new discoveries — no known asset nearby
            - Pair with her_cross_reference for the same analysis as a text table
            - Toggle layers in the UI to focus on novel or matched candidates
        """
        import json as json_mod

        from ...core.spatial_index import GridSpatialIndex

        match_radius_m = float(match_radius_m)
        near_radius_m = float(near_radius_m)

        # Validate basemap
        if basemap not in ("osm", "satellite", "terrain", "dark"):
            basemap = "osm"

        candidate_list: list[dict[str, Any]] = json_mod.loads(candidates)
        if not candidate_list:
            return MapContent(
                center=MapCenter(lat=54.0, lon=-2.0),
                zoom=6,
                basemap=basemap,  # type: ignore[arg-type]
                layers=[],
            )

        # Bounding box around all candidates (in BNG)
        eastings = [float(c.get("easting", 0)) for c in candidate_list]
        northings = [float(c.get("northing", 0)) for c in candidate_list]
        buffer = near_radius_m + 100
        bng_bbox = (
            min(eastings) - buffer,
            min(northings) - buffer,
            max(eastings) + buffer,
            max(northings) + buffer,
        )

        # Centre point for the map
        centre_e = (min(eastings) + max(eastings)) / 2
        centre_n = (min(northings) + max(northings)) / 2
        centre_lat, centre_lon = bng_to_wgs84(centre_e, centre_n)
        e_extent = max(eastings) - min(eastings) + 2 * buffer
        zoom = _zoom_from_radius_m(e_extent / 2)

        # Parse designation type filter
        dtype_filter = None
        if designation_types:
            dtype_list = [dt.strip() for dt in designation_types.split(",")]
            dtype_filter = dtype_list[0] if len(dtype_list) == 1 else None

        # Fetch known assets
        result = await registry.search_designations(  # type: ignore[union-attr]
            bbox=bng_bbox,
            max_results=2000,
            designation_type=dtype_filter,
        )
        known = list(result.features)

        # Post-filter for multi-type designation filtering
        if designation_types and dtype_filter is None:
            dtype_set = {dt.strip() for dt in designation_types.split(",")}
            known = [f for f in known if f.get("designation_type") in dtype_set]

        # Merge AIM if requested
        if include_aim:
            aim_result = await registry.search_aerial(  # type: ignore[union-attr]
                bbox=bng_bbox, max_results=2000
            )
            known.extend(aim_result.features)

        # Build spatial index and classify candidates
        index = GridSpatialIndex(cell_size_m=near_radius_m)
        index.build(known)

        match_feats: list[dict[str, Any]] = []
        near_feats: list[dict[str, Any]] = []
        novel_feats: list[dict[str, Any]] = []

        for c in candidate_list:
            ce = float(c.get("easting", 0))
            cn = float(c.get("northing", 0))
            clat, clon = bng_to_wgs84(ce, cn)

            props: dict[str, Any] = {k: v for k, v in c.items() if v is not None}
            if "name" not in props:
                props["name"] = f"Candidate ({ce:.0f}, {cn:.0f})"
            props.setdefault("easting", ce)
            props.setdefault("northing", cn)

            best_asset, best_dist = index.nearest(ce, cn, near_radius_m)
            feat: dict[str, Any] = {
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [clon, clat]},
                "properties": props,
            }

            if best_asset is not None and best_dist <= match_radius_m:
                feat["properties"]["matched_asset"] = best_asset.get("name", "")
                feat["properties"]["distance_m"] = round(best_dist, 1)
                feat["properties"]["classification"] = "match"
                match_feats.append(feat)
            elif best_asset is not None and best_dist <= near_radius_m:
                feat["properties"]["nearest_asset"] = best_asset.get("name", "")
                feat["properties"]["distance_m"] = round(best_dist, 1)
                feat["properties"]["classification"] = "near"
                near_feats.append(feat)
            else:
                feat["properties"]["classification"] = "novel"
                novel_feats.append(feat)

        def _fc(feats: list[dict[str, Any]]) -> dict[str, Any]:
            return {"type": "FeatureCollection", "features": feats}

        cluster = ClusterConfig(enabled=True, radius=40)
        layers: list[MapLayer] = []

        # Known assets — grey layer (rendered first so candidates appear on top)
        known_fc = _to_geojson(known)
        if known_fc["features"]:
            layers.append(
                MapLayer(
                    id="known_assets",
                    label="Known Heritage Assets",
                    features=known_fc,
                    style=_CROSSREF_STYLE["known"],
                    cluster=cluster,
                    popup=PopupTemplate(
                        title="{name}",
                        fields=["designation_type", "source", "record_id"],
                    ),
                )
            )

        candidate_popup = PopupTemplate(
            title="{name}",
            fields=[
                "classification",
                "easting",
                "northing",
                "distance_m",
                "matched_asset",
                "nearest_asset",
            ],
        )

        if novel_feats:
            layers.append(
                MapLayer(
                    id="novel",
                    label=f"Novel Candidates ({len(novel_feats)})",
                    features=_fc(novel_feats),
                    style=_CROSSREF_STYLE["novel"],
                    cluster=cluster,
                    popup=candidate_popup,
                )
            )

        if near_feats:
            layers.append(
                MapLayer(
                    id="near",
                    label=f"Near Known Assets ({len(near_feats)})",
                    features=_fc(near_feats),
                    style=_CROSSREF_STYLE["near"],
                    cluster=cluster,
                    popup=candidate_popup,
                )
            )

        if match_feats:
            layers.append(
                MapLayer(
                    id="match",
                    label=f"Matches ({len(match_feats)})",
                    features=_fc(match_feats),
                    style=_CROSSREF_STYLE["match"],
                    cluster=cluster,
                    popup=candidate_popup,
                )
            )

        return MapContent(
            center=MapCenter(lat=centre_lat, lon=centre_lon),
            zoom=zoom,
            basemap=basemap,  # type: ignore[arg-type]
            layers=layers,
            controls=MapControls(zoom=True, layers=True, scale=True, fullscreen=True),
        )
