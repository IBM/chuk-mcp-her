"""NHLE tools: monument search, building search, designation search, counts."""

from __future__ import annotations

import logging
from typing import Any

from ...constants import (
    DESIGNATION_TYPES,
    LISTING_GRADES,
    ErrorMessages,
    SuccessMessages,
)
from ...models.responses import (
    DesignationInfo,
    DesignationSearchResponse,
    ErrorResponse,
    FeatureCountResponse,
    MonumentDetailResponse,
    MonumentInfo,
    MonumentSearchResponse,
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


def _features_to_monuments(features: list[dict[str, Any]]) -> list[MonumentInfo]:
    """Convert normalised feature dicts to MonumentInfo models."""
    return [
        MonumentInfo(
            record_id=f.get("record_id", ""),
            nhle_id=f.get("nhle_id"),
            name=f.get("name", ""),
            source=f.get("source", "nhle"),
            designation_type=f.get("designation_type"),
            grade=f.get("grade"),
            list_date=f.get("list_date"),
            amendment_date=f.get("amendment_date"),
            easting=f.get("easting"),
            northing=f.get("northing"),
            lat=f.get("lat"),
            lon=f.get("lon"),
            ngr=f.get("ngr"),
            url=f.get("url"),
        )
        for f in features
    ]


def register_nhle_tools(mcp: object, registry: object) -> None:
    """Register NHLE query tools with the MCP server."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_monuments(
        name: str | None = None,
        description: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        offset: int = 0,
        output_mode: str = "json",
    ) -> str:
        """Search scheduled monuments by location, name, or description.

        Queries the National Heritage List for England for scheduled
        monuments. Supports spatial queries (bounding box or point+radius)
        and text search on monument names.

        Args:
            name: Monument name (partial match, case-insensitive)
            description: Full-text search on description field
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres (requires lat/lon)
            max_results: Maximum results (1-2000, default 50)
            offset: Pagination offset
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching scheduled monuments with location and metadata

        Tips for LLMs:
            - Use bbox for area searches (e.g. "586000,205000,602500,215000")
            - Use lat/lon + radius_m for point searches
            - Use name for text-based searches (e.g. "red hill")
            - Follow up with her_get_monument for full details
            - Use her_count_features first for quick totals
        """
        try:
            # Coerce numeric params (MCP may pass strings)
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
            radius_m = float(radius_m) if radius_m is not None else None
            max_results = int(max_results)
            offset = int(offset)

            bbox_tuple = _parse_bbox(bbox)
            query = name or description

            result = await registry.search_monuments(  # type: ignore[union-attr]
                query=query,
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                max_results=max_results,
                offset=offset,
            )

            if not result.features:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.NO_RESULTS,
                        error_type="no_data",
                        suggestion="Expand search radius or check coordinate system",
                    ),
                    output_mode,
                )

            monuments = _features_to_monuments(result.features)
            return format_response(
                MonumentSearchResponse(
                    query={"name": name, "bbox": bbox, "lat": lat, "lon": lon},
                    source="nhle",
                    count=len(monuments),
                    total_available=result.total_count,
                    monuments=monuments,
                    has_more=result.has_more,
                    next_offset=result.next_offset,
                    message=SuccessMessages.MONUMENTS_FOUND.format(len(monuments)),
                ),
                output_mode,
            )
        except ValueError as e:
            return format_response(
                ErrorResponse(error=str(e), error_type="validation_error"),
                output_mode,
            )
        except Exception as e:
            logger.error("Monument search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Monument search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_get_monument(
        nhle_id: str,
        output_mode: str = "json",
    ) -> str:
        """Get full details for a specific scheduled monument.

        Returns the complete record including name, designation, location,
        listing dates, and URL to the Historic England listing page.

        Args:
            nhle_id: NHLE list entry number (e.g. "1002345")
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Full monument record

        Tips for LLMs:
            - Use the nhle_id from search results
            - The URL links to the full Historic England listing page
        """
        try:
            record = await registry.get_monument(nhle_id)  # type: ignore[union-attr]
            if record is None:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.MONUMENT_NOT_FOUND.format(nhle_id),
                        error_type="not_found",
                    ),
                    output_mode,
                )

            return format_response(
                MonumentDetailResponse(
                    monument=record,
                    message=SuccessMessages.MONUMENT_RETRIEVED,
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Monument retrieval failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Monument retrieval failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_listed_buildings(
        name: str | None = None,
        grade: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        offset: int = 0,
        output_mode: str = "json",
    ) -> str:
        """Search listed buildings by location, name, or grade.

        Queries the NHLE for listed buildings. Filter by listing grade
        (I, II*, II) and location.

        Args:
            name: Building name (partial match, case-insensitive)
            grade: Listing grade filter: "I", "II*", or "II"
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres
            max_results: Maximum results (1-2000, default 50)
            offset: Pagination offset
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching listed buildings with grade and location

        Tips for LLMs:
            - Grade I is the highest (most significant)
            - Grade II* is between I and II
            - Grade II is the most common (~92% of all listed buildings)
            - Use bbox or lat/lon to limit by area
        """
        try:
            # Coerce numeric params (MCP may pass strings)
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
            radius_m = float(radius_m) if radius_m is not None else None
            max_results = int(max_results)
            offset = int(offset)

            if grade and grade not in LISTING_GRADES:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.INVALID_GRADE.format(grade),
                        error_type="validation_error",
                    ),
                    output_mode,
                )

            bbox_tuple = _parse_bbox(bbox)
            result = await registry.search_listed_buildings(  # type: ignore[union-attr]
                query=name,
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                grade=grade,
                max_results=max_results,
                offset=offset,
            )

            if not result.features:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.NO_RESULTS,
                        error_type="no_data",
                    ),
                    output_mode,
                )

            monuments = _features_to_monuments(result.features)
            return format_response(
                MonumentSearchResponse(
                    query={"name": name, "grade": grade, "bbox": bbox},
                    source="nhle",
                    count=len(monuments),
                    total_available=result.total_count,
                    monuments=monuments,
                    has_more=result.has_more,
                    next_offset=result.next_offset,
                    message=SuccessMessages.BUILDINGS_FOUND.format(len(monuments)),
                ),
                output_mode,
            )
        except ValueError as e:
            return format_response(
                ErrorResponse(error=str(e), error_type="validation_error"),
                output_mode,
            )
        except Exception as e:
            logger.error("Listed building search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Listed building search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_designations(
        designation_type: str | None = None,
        name: str | None = None,
        description: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        offset: int = 0,
        output_mode: str = "json",
    ) -> str:
        """Search across all designation types in the NHLE.

        Generic search covering listed buildings, scheduled monuments,
        registered parks and gardens, battlefields, protected wrecks,
        and World Heritage Sites.

        Args:
            designation_type: Filter by type — listed_building, scheduled_monument,
                park_and_garden, battlefield, protected_wreck, world_heritage_site
            name: Name search (partial match)
            description: Description search
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres
            max_results: Maximum results (1-2000, default 50)
            offset: Pagination offset
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching designations across all types

        Tips for LLMs:
            - Leave designation_type empty to search all types
            - Use her_count_features first for quick totals
            - Results include designation_type so you can see the mix
        """
        try:
            # Coerce numeric params (MCP may pass strings)
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
            radius_m = float(radius_m) if radius_m is not None else None
            max_results = int(max_results)
            offset = int(offset)

            if designation_type and designation_type not in DESIGNATION_TYPES:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.INVALID_DESIGNATION.format(
                            designation_type, ", ".join(DESIGNATION_TYPES)
                        ),
                        error_type="validation_error",
                    ),
                    output_mode,
                )

            bbox_tuple = _parse_bbox(bbox)
            query = name or description

            result = await registry.search_designations(  # type: ignore[union-attr]
                query=query,
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                designation_type=designation_type,
                max_results=max_results,
                offset=offset,
            )

            if not result.features:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.NO_RESULTS,
                        error_type="no_data",
                    ),
                    output_mode,
                )

            designations = [
                DesignationInfo(
                    record_id=f.get("record_id", ""),
                    nhle_id=f.get("nhle_id"),
                    name=f.get("name", ""),
                    designation_type=f.get("designation_type", "unknown"),
                    grade=f.get("grade"),
                    lat=f.get("lat"),
                    lon=f.get("lon"),
                    url=f.get("url"),
                )
                for f in result.features
            ]

            return format_response(
                DesignationSearchResponse(
                    query={"designation_type": designation_type, "name": name, "bbox": bbox},
                    source="nhle",
                    count=len(designations),
                    total_available=result.total_count,
                    designations=designations,
                    has_more=result.has_more,
                    next_offset=result.next_offset,
                    message=SuccessMessages.DESIGNATIONS_FOUND.format(
                        len(designations), result.total_count or len(designations)
                    ),
                ),
                output_mode,
            )
        except ValueError as e:
            return format_response(
                ErrorResponse(error=str(e), error_type="validation_error"),
                output_mode,
            )
        except Exception as e:
            logger.error("Designation search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Designation search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_count_features(
        designation_type: str | None = None,
        bbox: str | None = None,
        output_mode: str = "json",
    ) -> str:
        """Fast count of heritage features in an area.

        Returns counts by designation type without fetching full records.
        Use this before her_search_designations to estimate result sizes.

        Args:
            designation_type: Filter by type (None = count all types)
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Feature counts by designation type

        Tips for LLMs:
            - Much faster than a full search when you just need totals
            - Use this to decide whether to narrow your search area
            - Counts are broken down by designation type
        """
        try:
            bbox_tuple = _parse_bbox(bbox)
            counts = await registry.count_features(  # type: ignore[union-attr]
                bbox=bbox_tuple,
                designation_type=designation_type,
            )

            return format_response(
                FeatureCountResponse(
                    query={"designation_type": designation_type, "bbox": bbox},
                    counts=counts,
                    source="nhle",
                    message=SuccessMessages.FEATURES_COUNTED.format(counts.get("total", 0)),
                ),
                output_mode,
            )
        except ValueError as e:
            return format_response(
                ErrorResponse(error=str(e), error_type="validation_error"),
                output_mode,
            )
        except Exception as e:
            logger.error("Feature count failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Feature count failed"),
                output_mode,
            )
