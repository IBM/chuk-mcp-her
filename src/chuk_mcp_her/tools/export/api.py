"""Export tools: GeoJSON and LiDAR format."""

from __future__ import annotations

import logging
from typing import Any

from ...constants import ErrorMessages, SuccessMessages
from ...models.responses import (
    ErrorResponse,
    GeoJSONExportResponse,
    LiDARExportResponse,
    format_response,
)

logger = logging.getLogger(__name__)


def _parse_bbox(bbox_str: str | None) -> tuple[float, float, float, float] | None:
    """Parse 'xmin,ymin,xmax,ymax' string to tuple."""
    if not bbox_str:
        return None
    parts = [float(p.strip()) for p in bbox_str.split(",")]
    if len(parts) != 4:
        raise ValueError(ErrorMessages.INVALID_BBOX)
    return (parts[0], parts[1], parts[2], parts[3])


def _features_to_geojson(features: list[dict[str, Any]]) -> dict[str, Any]:
    """Convert normalised features to GeoJSON FeatureCollection."""
    geojson_features = []
    for f in features:
        lat = f.get("lat")
        lon = f.get("lon")
        geom = None
        if lat is not None and lon is not None:
            geom = {"type": "Point", "coordinates": [lon, lat]}

        props = {k: v for k, v in f.items() if k not in ("lat", "lon", "easting", "northing")}
        geojson_features.append(
            {
                "type": "Feature",
                "geometry": geom,
                "properties": props,
            }
        )

    return {
        "type": "FeatureCollection",
        "features": geojson_features,
    }


def register_export_tools(mcp: object, registry: object) -> None:
    """Register export tools."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_export_geojson(
        bbox: str | None = None,
        designation_type: str | None = None,
        name: str | None = None,
        max_results: int = 500,
        output_mode: str = "json",
    ) -> str:
        """Export heritage assets as GeoJSON FeatureCollection.

        Exports query results in GeoJSON format suitable for use in
        QGIS, Leaflet, or other GIS tools.

        Args:
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG
            designation_type: Filter by designation type
            name: Name filter (partial match)
            max_results: Maximum features to export (default 500, max 2000)
            output_mode: Response format — "json" (default) or "text"

        Returns:
            GeoJSON FeatureCollection with matching heritage assets

        Tips for LLMs:
            - Use bbox to limit the export area
            - Output is a standard GeoJSON FeatureCollection
            - Coordinates are in WGS84 (EPSG:4326)
        """
        try:
            bbox_tuple = _parse_bbox(bbox)
            result = await registry.search_designations(  # type: ignore[union-attr]
                query=name,
                bbox=bbox_tuple,
                designation_type=designation_type,
                max_results=min(max_results, 2000),
            )

            geojson = _features_to_geojson(result.features)

            return format_response(
                GeoJSONExportResponse(
                    geojson=geojson,
                    feature_count=len(result.features),
                    message=SuccessMessages.EXPORT_COMPLETE.format(len(result.features)),
                ),
                output_mode,
            )
        except ValueError as e:
            return format_response(
                ErrorResponse(error=str(e), error_type="validation_error"),
                output_mode,
            )
        except Exception as e:
            logger.error("GeoJSON export failed: %s", e)
            return format_response(
                ErrorResponse(
                    error=ErrorMessages.EXPORT_FAILED.format(str(e)),
                    message="GeoJSON export failed",
                ),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_export_for_lidar(
        bbox: str = "",
        include_aim: bool = True,
        include_nhle: bool = True,
        gateway_sites: str = "[]",
        output_mode: str = "json",
    ) -> str:
        """Export heritage assets for LiDAR cross-referencing.

        Produces a list of known monument centroids with metadata in
        the format expected by chuk-mcp-lidar spatial matching.

        Args:
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (required)
            include_aim: Include aerial mapping features (when available)
            include_nhle: Include NHLE designations (default true)
            gateway_sites: JSON array of Gateway records with easting/northing
                (output of her_enrich_gateway) to include as known sites
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Known sites in LiDAR cross-reference format

        Tips for LLMs:
            - bbox is required for LiDAR export
            - Output includes easting/northing in BNG for spatial matching
            - Each site has id, source, name, type, monument_type, period
            - Use her_enrich_gateway first, then pass output as gateway_sites
        """
        try:
            if not bbox:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.SPATIAL_REQUIRED,
                        error_type="validation_error",
                    ),
                    output_mode,
                )

            bbox_tuple = _parse_bbox(bbox)
            known_sites: list[dict[str, Any]] = []

            if include_nhle and bbox_tuple:
                result = await registry.search_designations(  # type: ignore[union-attr]
                    bbox=bbox_tuple,
                    max_results=2000,
                )
                for f in result.features:
                    known_sites.append(
                        {
                            "id": f.get("record_id"),
                            "source": "nhle",
                            "name": f.get("name"),
                            "type": f.get("designation_type"),
                            "grade": f.get("grade"),
                            "easting": f.get("easting"),
                            "northing": f.get("northing"),
                        }
                    )

            # Merge AIM aerial mapping features if requested
            if include_aim and bbox_tuple:
                aim_result = await registry.search_aerial(  # type: ignore[union-attr]
                    bbox=bbox_tuple, max_results=2000
                )
                for f in aim_result.features:
                    known_sites.append(
                        {
                            "id": f.get("record_id"),
                            "source": "aim",
                            "name": f.get("name"),
                            "type": f.get("monument_type"),
                            "monument_type": f.get("monument_type"),
                            "period": f.get("period"),
                            "form": f.get("form"),
                            "evidence": f.get("evidence"),
                            "easting": f.get("easting"),
                            "northing": f.get("northing"),
                        }
                    )

            # Merge Gateway sites if provided
            import json as json_mod

            gateway_list = json_mod.loads(gateway_sites)
            for g in gateway_list:
                known_sites.append(
                    {
                        "id": g.get("record_id"),
                        "source": "heritage_gateway",
                        "name": g.get("name"),
                        "type": g.get("monument_type"),
                        "monument_type": g.get("monument_type"),
                        "period": g.get("period"),
                        "easting": g.get("easting"),
                        "northing": g.get("northing"),
                    }
                )

            bbox_list = list(bbox_tuple) if bbox_tuple else []

            return format_response(
                LiDARExportResponse(
                    bbox=bbox_list,
                    known_sites=known_sites,
                    count=len(known_sites),
                    message=SuccessMessages.LIDAR_EXPORT_COMPLETE.format(len(known_sites)),
                ),
                output_mode,
            )
        except ValueError as e:
            return format_response(
                ErrorResponse(error=str(e), error_type="validation_error"),
                output_mode,
            )
        except Exception as e:
            logger.error("LiDAR export failed: %s", e)
            return format_response(
                ErrorResponse(
                    error=ErrorMessages.EXPORT_FAILED.format(str(e)),
                    message="LiDAR export failed",
                ),
                output_mode,
            )
