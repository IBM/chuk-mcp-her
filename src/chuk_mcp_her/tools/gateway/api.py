"""Heritage Gateway tools — search local HERs via web scraper."""

from __future__ import annotations

import logging

from ...constants import ErrorMessages, SuccessMessages
from ...models.responses import (
    ErrorResponse,
    GatewayRecordInfo,
    GatewaySearchResponse,
    format_response,
)

logger = logging.getLogger(__name__)


def register_gateway_tools(mcp: object, registry: object) -> None:
    """Register Heritage Gateway tools."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_search_heritage_gateway(
        what: str | None = None,
        where: str | None = None,
        when: str | None = None,
        max_results: int = 50,
        output_mode: str = "json",
    ) -> str:
        """Search local Historic Environment Records via Heritage Gateway.

        Searches across 60+ local HERs for undesignated sites not in the
        NHLE — red hills, findspots, fieldwork records, HER monument
        entries. Best-effort access via web scraping; returns empty
        results gracefully when the Gateway is unavailable.

        Args:
            what: Monument type or keyword (e.g. "red hill", "saltern")
            where: Place name or area (e.g. "Goldhanger", "Blackwater")
            when: Period (e.g. "Iron Age", "Roman", "Medieval")
            max_results: Maximum results (default 50)
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Matching Heritage Gateway records from local HERs

        Tips for LLMs:
            This is the best source for undesignated sites and local HER data.
            Results may be empty if the Gateway is temporarily unavailable.
            IMPORTANT: Gateway results cover only local HER records. For
            comprehensive coverage, ALSO run her_search_monuments (NHLE) and
            her_search_aerial (AIM) in the same area and merge the results.
            For spatial filtering, use her_enrich_gateway to resolve BNG
            coordinates, then apply a bbox to filter precisely.
        """
        try:
            # Coerce numeric params (MCP may pass strings)
            max_results = int(max_results)

            result = await registry.search_heritage_gateway(  # type: ignore[union-attr]
                what=what,
                where=where,
                when=when,
                max_results=max_results,
            )

            records = [
                GatewayRecordInfo(
                    source_her=f.get("source_her"),
                    record_id=f.get("record_id"),
                    name=f.get("name"),
                    monument_type=f.get("monument_type"),
                    period=f.get("period"),
                    description=f.get("description"),
                    grid_reference=f.get("grid_reference"),
                    easting=f.get("easting"),
                    northing=f.get("northing"),
                    lat=f.get("lat"),
                    lon=f.get("lon"),
                    designation=f.get("designation"),
                    url=f.get("url"),
                )
                for f in result.features
            ]

            note = None
            if not records:
                note = (
                    "No results returned. The Heritage Gateway may be "
                    "temporarily unavailable. Try her_search_monuments "
                    "for NHLE data instead."
                )

            return format_response(
                GatewaySearchResponse(
                    count=len(records),
                    total_available=result.total_count,
                    records=records,
                    has_more=result.has_more,
                    note=note,
                    message=SuccessMessages.GATEWAY_FOUND.format(result.total_count),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Heritage Gateway search failed: %s", e)
            return format_response(
                ErrorResponse(
                    error=ErrorMessages.GATEWAY_SEARCH_FAILED.format(str(e)),
                    suggestion="Use her_search_monuments for NHLE data instead",
                ),
                output_mode,
            )
