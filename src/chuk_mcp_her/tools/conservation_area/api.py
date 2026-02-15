"""Conservation area tools — search, count, get."""

from __future__ import annotations

import logging

from ...constants import ErrorMessages, SuccessMessages
from ...models.responses import (
    ConservationAreaCountResponse,
    ConservationAreaInfo,
    ConservationAreaSearchResponse,
    ErrorResponse,
    MonumentDetailResponse,
    format_response,
)

logger = logging.getLogger(__name__)


def register_conservation_area_tools(mcp: object, registry: object) -> None:
    """Register conservation area tools."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_conservation_areas(
        query: str | None = None,
        lpa: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        offset: int = 0,
        output_mode: str = "json",
    ) -> str:
        """Search conservation areas across England.

        Queries Historic England's Conservation Areas dataset for areas
        of special architectural or historic interest designated by
        Local Planning Authorities.

        Args:
            query: Name search (e.g. "Maldon", "Bath")
            lpa: Local Planning Authority filter (e.g. "Maldon District")
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres (requires lat/lon)
            max_results: Maximum results (1-2000, default 50)
            offset: Pagination offset
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching conservation areas with name, LPA, designation date

        Tips for LLMs:
            Use lpa to filter by local authority.
            Combine with bbox or lat/lon for spatial queries.
            Use her_count_conservation_areas first to gauge result size.
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

            result = await registry.search_conservation_areas(  # type: ignore[union-attr]
                query=query,
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                lpa=lpa,
                max_results=max_results,
                offset=offset,
            )

            areas = [
                ConservationAreaInfo(
                    record_id=f.get("record_id"),
                    uid=f.get("uid"),
                    name=f.get("name"),
                    lpa=f.get("lpa"),
                    designation_date=f.get("designation_date"),
                    easting=f.get("easting"),
                    northing=f.get("northing"),
                    lat=f.get("lat"),
                    lon=f.get("lon"),
                    area_sqm=f.get("area_sqm"),
                )
                for f in result.features
            ]

            return format_response(
                ConservationAreaSearchResponse(
                    count=len(areas),
                    total_available=result.total_count,
                    areas=areas,
                    has_more=result.has_more,
                    next_offset=result.next_offset,
                    message=SuccessMessages.CONSERVATION_AREAS_FOUND.format(result.total_count),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Conservation area search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Conservation area search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_count_conservation_areas(
        bbox: str | None = None,
        query: str | None = None,
        lpa: str | None = None,
        output_mode: str = "json",
    ) -> str:
        """Count conservation areas in an area (fast, no geometry returned).

        Returns a quick count of conservation areas matching filters.
        Use before her_search_conservation_areas to gauge result size.

        Args:
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            query: Name filter (e.g. "Maldon")
            lpa: Local Planning Authority filter
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Conservation area count

        Tips for LLMs:
            Call this before her_search_conservation_areas to check how
            many areas match before fetching full records.
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

            count = await registry.count_conservation_areas(  # type: ignore[union-attr]
                bbox=bbox_tuple,
                query=query,
                lpa=lpa,
            )

            query_info: dict = {}
            if bbox:
                query_info["bbox"] = bbox
            if query:
                query_info["query"] = query
            if lpa:
                query_info["lpa"] = lpa

            return format_response(
                ConservationAreaCountResponse(
                    query=query_info or None,
                    count=count,
                    message=SuccessMessages.CONSERVATION_AREA_COUNTED.format(count),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Conservation area count failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Conservation area count failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_get_conservation_area(
        record_id: str = "",
        output_mode: str = "json",
    ) -> str:
        """Get full details of a specific conservation area.

        Retrieves a single conservation area by its UID. Accepts either
        "ca:UID" or just the UID number.

        Args:
            record_id: Conservation area ID (e.g. "ca:1234" or "1234")
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Full conservation area details including name, LPA, location

        Tips for LLMs:
            Use record_id from her_search_conservation_areas results.
        """
        try:
            if not record_id:
                return format_response(
                    ErrorResponse(
                        error="record_id is required",
                        suggestion="Provide a conservation area UID, e.g. 'ca:1234'",
                    ),
                    output_mode,
                )

            if not record_id.startswith("ca:"):
                record_id = f"ca:{record_id}"

            feature = await registry.get_conservation_area(  # type: ignore[union-attr]
                record_id
            )

            if feature is None:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.MONUMENT_NOT_FOUND.format(record_id),
                        suggestion="Check the record_id from her_search_conservation_areas results",
                    ),
                    output_mode,
                )

            return format_response(
                MonumentDetailResponse(
                    monument=feature,
                    message=SuccessMessages.CONSERVATION_AREA_RETRIEVED,
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Get conservation area failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Get conservation area failed"),
                output_mode,
            )
