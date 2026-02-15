"""Heritage at Risk tools — search, count, get."""

from __future__ import annotations

import logging

from ...constants import ErrorMessages, HAR_CATEGORIES, SuccessMessages
from ...models.responses import (
    ErrorResponse,
    HeritageAtRiskCountResponse,
    HeritageAtRiskInfo,
    HeritageAtRiskSearchResponse,
    MonumentDetailResponse,
    format_response,
)

logger = logging.getLogger(__name__)


def register_heritage_at_risk_tools(mcp: object, registry: object) -> None:
    """Register heritage at risk tools."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_heritage_at_risk(
        query: str | None = None,
        heritage_category: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        offset: int = 0,
        output_mode: str = "json",
    ) -> str:
        """Search the Heritage at Risk Register for endangered heritage assets.

        Queries Historic England's annual register of heritage assets at
        risk of loss through neglect, decay, or inappropriate development.

        Args:
            query: Name search (e.g. "church", "castle")
            heritage_category: Filter by category — one of:
                "Scheduled Monument", "Listed Building", "Conservation Area",
                "Registered Park and Garden", "Registered Battlefield",
                "Protected Wreck Site"
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres (requires lat/lon)
            max_results: Maximum results (1-2000, default 50)
            offset: Pagination offset
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching heritage at risk entries with category, risk methodology

        Tips for LLMs:
            Use heritage_category to filter by asset type.
            Combine with bbox or lat/lon for spatial queries.
            These entries are designated assets that are at risk — they
            will also appear in NHLE searches.
        """
        try:
            if heritage_category and heritage_category not in HAR_CATEGORIES:
                return format_response(
                    ErrorResponse(
                        error=f"Invalid heritage_category '{heritage_category}'",
                        suggestion=f"Use one of: {', '.join(HAR_CATEGORIES)}",
                    ),
                    output_mode,
                )

            bbox_tuple = None
            if bbox:
                parts = [float(x.strip()) for x in bbox.split(",")]
                if len(parts) != 4:
                    return format_response(
                        ErrorResponse(error=ErrorMessages.INVALID_BBOX),
                        output_mode,
                    )
                bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

            result = await registry.search_heritage_at_risk(  # type: ignore[union-attr]
                query=query,
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                heritage_category=heritage_category,
                max_results=max_results,
                offset=offset,
            )

            entries = [
                HeritageAtRiskInfo(
                    record_id=f.get("record_id"),
                    list_entry=f.get("list_entry"),
                    name=f.get("name"),
                    heritage_category=f.get("heritage_category"),
                    risk_methodology=f.get("risk_methodology"),
                    lat=f.get("lat"),
                    lon=f.get("lon"),
                    area_sqm=f.get("area_sqm"),
                    url=f.get("url"),
                )
                for f in result.features
            ]

            return format_response(
                HeritageAtRiskSearchResponse(
                    count=len(entries),
                    total_available=result.total_count,
                    entries=entries,
                    has_more=result.has_more,
                    next_offset=result.next_offset,
                    message=SuccessMessages.HAR_FOUND.format(result.total_count),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Heritage at Risk search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Heritage at Risk search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_count_heritage_at_risk(
        bbox: str | None = None,
        heritage_category: str | None = None,
        output_mode: str = "json",
    ) -> str:
        """Count heritage at risk entries in an area (fast, no geometry returned).

        Returns a quick count of at-risk heritage assets matching filters.
        Use before her_search_heritage_at_risk to gauge result size.

        Args:
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            heritage_category: Filter by category (e.g. "Listed Building")
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Heritage at risk count

        Tips for LLMs:
            Call this before her_search_heritage_at_risk to check how
            many entries match before fetching full records.
        """
        try:
            if heritage_category and heritage_category not in HAR_CATEGORIES:
                return format_response(
                    ErrorResponse(
                        error=f"Invalid heritage_category '{heritage_category}'",
                        suggestion=f"Use one of: {', '.join(HAR_CATEGORIES)}",
                    ),
                    output_mode,
                )

            bbox_tuple = None
            if bbox:
                parts = [float(x.strip()) for x in bbox.split(",")]
                if len(parts) != 4:
                    return format_response(
                        ErrorResponse(error=ErrorMessages.INVALID_BBOX),
                        output_mode,
                    )
                bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

            count = await registry.count_heritage_at_risk(  # type: ignore[union-attr]
                bbox=bbox_tuple,
                heritage_category=heritage_category,
            )

            query_info: dict = {}
            if bbox:
                query_info["bbox"] = bbox
            if heritage_category:
                query_info["heritage_category"] = heritage_category

            return format_response(
                HeritageAtRiskCountResponse(
                    query=query_info or None,
                    count=count,
                    message=SuccessMessages.HAR_COUNTED.format(count),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Heritage at Risk count failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Heritage at Risk count failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_get_heritage_at_risk(
        record_id: str = "",
        output_mode: str = "json",
    ) -> str:
        """Get full details of a specific heritage at risk entry.

        Retrieves a single at-risk entry by its List Entry number.
        Accepts either "har:LIST_ENTRY" or just the number.

        Args:
            record_id: Heritage at Risk ID (e.g. "har:1021506" or "1021506")
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Full heritage at risk details including category, risk methodology

        Tips for LLMs:
            Use record_id from her_search_heritage_at_risk results.
        """
        try:
            if not record_id:
                return format_response(
                    ErrorResponse(
                        error="record_id is required",
                        suggestion="Provide a List Entry number, e.g. 'har:1021506'",
                    ),
                    output_mode,
                )

            if not record_id.startswith("har:"):
                record_id = f"har:{record_id}"

            feature = await registry.get_heritage_at_risk(  # type: ignore[union-attr]
                record_id
            )

            if feature is None:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.MONUMENT_NOT_FOUND.format(record_id),
                        suggestion="Check the record_id from her_search_heritage_at_risk results",
                    ),
                    output_mode,
                )

            return format_response(
                MonumentDetailResponse(
                    monument=feature,
                    message=SuccessMessages.HAR_RETRIEVED,
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Get heritage at risk failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Get heritage at risk failed"),
                output_mode,
            )
