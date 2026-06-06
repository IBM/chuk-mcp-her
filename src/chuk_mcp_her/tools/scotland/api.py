"""Scotland (Historic Environment Scotland) tools — NRHE search, designations, get record."""

from __future__ import annotations

import logging

from ...constants import ErrorMessages, SuccessMessages
from ...models.responses import (
    ErrorResponse,
    MonumentDetailResponse,
    ScotlandDesignationInfo,
    ScotlandDesignationSearchResponse,
    ScotlandRecordInfo,
    ScotlandSearchResponse,
    format_response,
)

logger = logging.getLogger(__name__)


def register_scotland_tools(mcp: object, registry: object) -> None:
    """Register Scotland (Historic Environment Scotland) tools."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_scotland(
        name: str | None = None,
        site_type: str | None = None,
        broad_class: str | None = None,
        council: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        output_mode: str = "json",
    ) -> str:
        """Search Scottish NRHE records (320,000+ sites from Canmore).

        Queries the National Record of the Historic Environment for
        terrestrial archaeological sites, monuments, and buildings in
        Scotland. Covers 320,000+ records including castles, brochs,
        cairns, standing stones, churches, and industrial heritage.

        Args:
            name: Site name keyword (partial, case-insensitive)
            site_type: Site type keyword (e.g. "CASTLE", "BROCH", "CAIRN")
            broad_class: Broad classification (e.g. "DOMESTIC", "RELIGIOUS")
            council: Council area (e.g. "Highland", "Edinburgh")
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres (requires lat/lon)
            max_results: Maximum results (1-1000, default 50)
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching NRHE records with site type, classification, location

        Tips for LLMs:
            - This covers ALL known Scottish heritage sites, not just designated ones
            - For designated assets only, use her_search_scotland_designations
            - For cross-border queries near England/Scotland border, also run
              her_search_monuments (NHLE) and her_search_aerial (AIM) for English sites
            - site_type keywords: CASTLE, BROCH, CAIRN, STONE CIRCLE, CHURCH,
              FORT, CRANNOG, DUN, STANDING STONE, SOUTERRAIN
            - MapServer max is 1,000 records per request
        """
        try:
            # Coerce numeric params (MCP may pass strings)
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
            radius_m = float(radius_m) if radius_m is not None else None
            max_results = int(max_results)

            bbox_tuple = None
            if bbox:
                parts = [float(x.strip()) for x in bbox.split(",")]
                if len(parts) != 4:
                    return format_response(
                        ErrorResponse(error=ErrorMessages.INVALID_BBOX),
                        output_mode,
                    )
                bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

            result = await registry.search_scotland(  # type: ignore[union-attr]
                query=name,
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                site_type=site_type,
                broad_class=broad_class,
                council=council,
                max_results=max_results,
            )

            records = [
                ScotlandRecordInfo(
                    record_id=f.get("record_id"),
                    canmore_id=f.get("canmore_id"),
                    site_number=f.get("site_number"),
                    name=f.get("name"),
                    alt_name=f.get("alt_name"),
                    broad_class=f.get("broad_class"),
                    site_type=f.get("site_type"),
                    form=f.get("form"),
                    county=f.get("county"),
                    council=f.get("council"),
                    parish=f.get("parish"),
                    grid_reference=f.get("grid_reference"),
                    easting=f.get("easting"),
                    northing=f.get("northing"),
                    lat=f.get("lat"),
                    lon=f.get("lon"),
                    url=f.get("url"),
                )
                for f in result.features
            ]

            return format_response(
                ScotlandSearchResponse(
                    count=len(records),
                    total_available=result.total_count,
                    records=records,
                    has_more=result.has_more,
                    message=SuccessMessages.SCOTLAND_NRHE_FOUND.format(len(records)),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Scotland NRHE search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Scotland NRHE search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_get_scotland_record(
        record_id: str = "",
        output_mode: str = "json",
    ) -> str:
        """Get full details of a Scottish NRHE record by Canmore ID.

        Retrieves a single record from the National Record of the Historic
        Environment. Accepts either "scotland:CANMOREID" or just the ID.

        Args:
            record_id: Canmore ID (e.g. "scotland:12345" or "12345")
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Full record details including site type, form, location, grid reference

        Tips for LLMs:
            Use record_id from her_search_scotland results.
        """
        try:
            if not record_id:
                return format_response(
                    ErrorResponse(
                        error="record_id is required",
                        suggestion="Provide a Canmore ID, e.g. 'scotland:12345'",
                    ),
                    output_mode,
                )

            if not record_id.startswith("scotland:"):
                record_id = f"scotland:{record_id}"

            feature = await registry.get_scotland_record(  # type: ignore[union-attr]
                record_id
            )

            if feature is None:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.MONUMENT_NOT_FOUND.format(record_id),
                        suggestion="Check the record_id from her_search_scotland results",
                    ),
                    output_mode,
                )

            return format_response(
                MonumentDetailResponse(
                    monument=feature,
                    message=SuccessMessages.SCOTLAND_NRHE_RETRIEVED,
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Get Scotland record failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Get Scotland record failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_scotland_designations(
        designation_type: str | None = None,
        name: str | None = None,
        bbox: str | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 50,
        output_mode: str = "json",
    ) -> str:
        """Search Scottish designated heritage assets.

        Queries HES Designations for listed buildings, scheduled monuments,
        gardens and designed landscapes, battlefields, world heritage sites,
        conservation areas, and historic marine protected areas in Scotland.

        Args:
            designation_type: Filter by type — one of: listed_building,
                scheduled_monument, garden_designed_landscape, battlefield,
                world_heritage_site, conservation_area,
                historic_marine_protected_area
            name: Name keyword (partial, case-insensitive)
            bbox: Bounding box as "xmin,ymin,xmax,ymax" in BNG (EPSG:27700)
            lat: WGS84 latitude for radius search
            lon: WGS84 longitude for radius search
            radius_m: Search radius in metres (requires lat/lon)
            max_results: Maximum results (default 50)
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching designated heritage assets with type, category, location

        Tips for LLMs:
            - Use this for formally designated Scottish assets
            - For ALL known Scottish sites (not just designated), use her_search_scotland
            - Scottish designation types differ slightly from English NHLE types:
              Scotland has garden_designed_landscape and historic_marine_protected_area
            - For cross-border queries, also search English sources
              (her_search_designations for NHLE)
        """
        try:
            # Coerce numeric params (MCP may pass strings)
            lat = float(lat) if lat is not None else None
            lon = float(lon) if lon is not None else None
            radius_m = float(radius_m) if radius_m is not None else None
            max_results = int(max_results)

            bbox_tuple = None
            if bbox:
                parts = [float(x.strip()) for x in bbox.split(",")]
                if len(parts) != 4:
                    return format_response(
                        ErrorResponse(error=ErrorMessages.INVALID_BBOX),
                        output_mode,
                    )
                bbox_tuple = (parts[0], parts[1], parts[2], parts[3])

            result = await registry.search_scotland_designations(  # type: ignore[union-attr]
                designation_type=designation_type,
                query=name,
                bbox=bbox_tuple,
                lat=lat,
                lon=lon,
                radius_m=radius_m,
                max_results=max_results,
            )

            designations = [
                ScotlandDesignationInfo(
                    record_id=f.get("record_id"),
                    designation_reference=f.get("designation_reference"),
                    name=f.get("name"),
                    designation_type=f.get("designation_type"),
                    category=f.get("category"),
                    designated_date=f.get("designated_date"),
                    local_authority=f.get("local_authority"),
                    easting=f.get("easting"),
                    northing=f.get("northing"),
                    lat=f.get("lat"),
                    lon=f.get("lon"),
                    url=f.get("url"),
                )
                for f in result.features
            ]

            return format_response(
                ScotlandDesignationSearchResponse(
                    count=len(designations),
                    total_available=result.total_count,
                    designations=designations,
                    has_more=result.has_more,
                    message=SuccessMessages.SCOTLAND_DESIGNATIONS_FOUND.format(len(designations)),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Scotland designation search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Scotland designation search failed"),
                output_mode,
            )
