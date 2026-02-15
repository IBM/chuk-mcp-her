"""Aerial investigation mapping tools — search, count, get feature."""

from __future__ import annotations

import logging

from ...constants import ErrorMessages, SuccessMessages
from ...models.responses import (
    AerialCountResponse,
    AerialFeatureInfo,
    AerialSearchResponse,
    ErrorResponse,
    MonumentDetailResponse,
    format_response,
)

logger = logging.getLogger(__name__)


def register_aerial_tools(mcp: object, registry: object) -> None:
    """Register aerial investigation mapping tools."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_aerial(
        monument_type: str | None = None,
        period: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        offset: int = 0,
        output_mode: str = "json",
    ) -> str:
        """Search aerial investigation mapping data for archaeological features.

        Queries Historic England AIM data for features identified from
        aerial photographs and LiDAR. Includes cropmarks, earthworks,
        enclosures, ring ditches, saltern mounds, and other features
        not in the NHLE.

        Args:
            monument_type: Monument type keyword (e.g. "SALTERN MOUND", "ENCLOSURE")
            period: Period filter (e.g. "IRON AGE", "ROMAN", "MEDIEVAL")
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres (requires lat/lon)
            max_results: Maximum results (1-2000, default 50)
            offset: Pagination offset
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching aerial mapping features with monument type, period, evidence

        Tips for LLMs:
            Use monument_type and period as uppercase keywords.
            Combine with bbox or lat/lon for spatial queries.
            These features are NOT in the NHLE — they complement her_search_monuments.
        """
        try:
            # Coerce numeric params (MCP may pass strings)
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
            radius_m = float(radius_m) if radius_m is not None else None
            max_results = int(max_results)
            offset = int(offset)

            bbox_tuple = None
            if bbox:
                parts = [float(x.strip()) for x in bbox.split(",")]
                if len(parts) != 4:
                    return format_response(
                        ErrorResponse(error=ErrorMessages.INVALID_BBOX),
                        output_mode,
                    )
                bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

            result = await registry.search_aerial(  # type: ignore[union-attr]
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                monument_type=monument_type,
                period=period,
                max_results=max_results,
                offset=offset,
            )

            features = [
                AerialFeatureInfo(
                    record_id=f.get("record_id"),
                    aim_id=f.get("aim_id"),
                    name=f.get("name"),
                    monument_type=f.get("monument_type"),
                    broad_type=f.get("broad_type"),
                    narrow_type=f.get("narrow_type"),
                    period=f.get("period"),
                    form=f.get("form"),
                    evidence=f.get("evidence"),
                    project=f.get("project"),
                    her_no=f.get("her_no"),
                    easting=f.get("easting"),
                    northing=f.get("northing"),
                    lat=f.get("lat"),
                    lon=f.get("lon"),
                )
                for f in result.features
            ]

            return format_response(
                AerialSearchResponse(
                    count=len(features),
                    total_available=result.total_count,
                    features=features,
                    has_more=result.has_more,
                    next_offset=result.next_offset,
                    message=SuccessMessages.AERIAL_FOUND.format(result.total_count),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Aerial search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Aerial search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_count_aerial(
        bbox: str | None = None,
        monument_type: str | None = None,
        period: str | None = None,
        output_mode: str = "json",
    ) -> str:
        """Count aerial mapping features in an area (fast, no geometry returned).

        Returns a quick count of AIM features matching spatial and attribute
        filters. Use before her_search_aerial to gauge result size.

        Args:
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            monument_type: Monument type keyword (e.g. "ENCLOSURE", "MOUND")
            period: Period filter (e.g. "IRON AGE", "ROMAN")
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Feature count

        Tips for LLMs:
            Call this before her_search_aerial to check how many features
            match before fetching full records.
        """
        try:
            bbox_tuple = None
            if bbox:
                parts = [float(x.strip()) for x in bbox.split(",")]
                if len(parts) != 4:
                    return format_response(
                        ErrorResponse(error=ErrorMessages.INVALID_BBOX),
                        output_mode,
                    )
                bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

            count = await registry.count_aerial(  # type: ignore[union-attr]
                bbox=bbox_tuple,
                monument_type=monument_type,
                period=period,
            )

            query_info: dict = {}
            if bbox:
                query_info["bbox"] = bbox
            if monument_type:
                query_info["monument_type"] = monument_type
            if period:
                query_info["period"] = period

            return format_response(
                AerialCountResponse(
                    query=query_info or None,
                    count=count,
                    message=SuccessMessages.AERIAL_COUNTED.format(count),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Aerial count failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Aerial count failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_get_aerial_feature(
        record_id: str = "",
        output_mode: str = "json",
    ) -> str:
        """Get full details of a specific aerial mapping feature.

        Retrieves a single AIM feature by its HE_UID. Accepts either
        "aim:HE_UID" or just the HE_UID.

        Args:
            record_id: AIM feature ID (e.g. "aim:12345" or "12345")
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Full feature details including monument type, period, evidence, location

        Tips for LLMs:
            Use record_id from her_search_aerial results.
        """
        try:
            if not record_id:
                return format_response(
                    ErrorResponse(
                        error="record_id is required",
                        suggestion="Provide an AIM HE_UID, e.g. 'aim:12345'",
                    ),
                    output_mode,
                )

            if not record_id.startswith("aim:"):
                record_id = f"aim:{record_id}"

            feature = await registry.get_aerial_feature(  # type: ignore[union-attr]
                record_id
            )

            if feature is None:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.MONUMENT_NOT_FOUND.format(record_id),
                        suggestion="Check the record_id from her_search_aerial results",
                    ),
                    output_mode,
                )

            return format_response(
                MonumentDetailResponse(
                    monument=feature,
                    message=SuccessMessages.AERIAL_FEATURE_RETRIEVED,
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Get aerial feature failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Get aerial feature failed"),
                output_mode,
            )
