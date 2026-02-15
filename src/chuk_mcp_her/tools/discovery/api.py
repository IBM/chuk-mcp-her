"""Discovery tools: server status, source listing, capabilities."""

from __future__ import annotations

import logging

from ...constants import SUPPORTED_SRIDS, ServerConfig, SuccessMessages
from ...models.responses import (
    CapabilitiesResponse,
    ErrorResponse,
    SourceInfo,
    SourceListResponse,
    StatusResponse,
    StatusSourceInfo,
    ToolInfo,
    format_response,
)

logger = logging.getLogger(__name__)


def register_discovery_tools(mcp: object, registry: object) -> None:
    """Register discovery tools with the MCP server."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_status(
        output_mode: str = "json",
    ) -> str:
        """Check server health and data source availability.

        Returns server version, registered source statuses, and tool count.

        Args:
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Server status including source availability

        Tips for LLMs:
            Call this first to check which sources are available.
        """
        try:
            sources_list = registry.list_sources()  # type: ignore[union-attr]
            source_statuses = {}
            for s in sources_list:
                source_statuses[s["id"]] = StatusSourceInfo(
                    status=s["status"],
                    note=s.get("note"),
                )

            jurisdictions = sorted(
                {s.get("coverage", "") for s in sources_list if s.get("coverage")}
            )
            return format_response(
                StatusResponse(
                    server=ServerConfig.NAME,
                    version=ServerConfig.VERSION,
                    sources=source_statuses,
                    tool_count=23,
                    message=SuccessMessages.SERVER_OK.format(
                        len(sources_list), ", ".join(jurisdictions)
                    ),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Failed to get status: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Failed to get status"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_list_sources(
        output_mode: str = "json",
    ) -> str:
        """List all registered heritage data sources and their capabilities.

        Returns metadata about each source including what query types
        it supports, its coverage area, and current status.

        Args:
            output_mode: Response format — "json" (default) or "text"

        Returns:
            List of sources with capabilities

        Tips for LLMs:
            Use this to discover which sources are available and what
            each one can do before running queries.
        """
        try:
            sources_list = registry.list_sources()  # type: ignore[union-attr]
            source_infos = [
                SourceInfo(
                    source_id=s["id"],
                    name=s["name"],
                    organisation=s.get("organisation"),
                    coverage=s.get("coverage"),
                    api_type=s.get("api_type"),
                    description=s.get("description"),
                    native_srid=s.get("native_srid"),
                    capabilities=s.get("capabilities", []),
                    designation_types=s.get("designation_types", []),
                    licence=s.get("licence"),
                    status=s.get("status", "available"),
                    note=s.get("note"),
                )
                for s in sources_list
            ]

            return format_response(
                SourceListResponse(
                    sources=source_infos,
                    count=len(source_infos),
                    message=SuccessMessages.SOURCES_LISTED.format(len(source_infos)),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Failed to list sources: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Failed to list sources"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_capabilities(
        output_mode: str = "json",
    ) -> str:
        """List full server capabilities: sources, tools, and supported queries.

        Provides complete information about the server including all
        available tools, registered sources, supported spatial references,
        and guidance for LLM query planning.

        Args:
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Complete capability listing with LLM guidance

        Tips for LLMs:
            Call this once at the start of a session to understand what
            tools are available and how to use them effectively.
        """
        try:
            sources_list = registry.list_sources()  # type: ignore[union-attr]
            source_infos = [
                SourceInfo(
                    source_id=s["id"],
                    name=s["name"],
                    organisation=s.get("organisation"),
                    coverage=s.get("coverage"),
                    api_type=s.get("api_type"),
                    description=s.get("description"),
                    native_srid=s.get("native_srid"),
                    capabilities=s.get("capabilities", []),
                    designation_types=s.get("designation_types", []),
                    licence=s.get("licence"),
                    status=s.get("status", "available"),
                    note=s.get("note"),
                )
                for s in sources_list
            ]

            # Hardcoded tool list — update when adding tools
            tools = [
                ToolInfo(
                    name="her_status",
                    category="discovery",
                    description="Server health and source availability",
                ),
                ToolInfo(
                    name="her_list_sources",
                    category="discovery",
                    description="List registered data sources",
                ),
                ToolInfo(
                    name="her_capabilities",
                    category="discovery",
                    description="Full server capability listing",
                ),
                ToolInfo(
                    name="her_search_monuments",
                    category="nhle",
                    description="Search scheduled monuments by location or name",
                ),
                ToolInfo(
                    name="her_get_monument",
                    category="nhle",
                    description="Get full details for a specific monument",
                ),
                ToolInfo(
                    name="her_search_listed_buildings",
                    category="nhle",
                    description="Search listed buildings with grade filter",
                ),
                ToolInfo(
                    name="her_search_designations",
                    category="nhle",
                    description="Search across all designation types",
                ),
                ToolInfo(
                    name="her_count_features",
                    category="nhle",
                    description="Fast count of features in an area",
                ),
                ToolInfo(
                    name="her_search_aerial",
                    category="aerial",
                    description="Search aerial investigation mapping data",
                ),
                ToolInfo(
                    name="her_count_aerial",
                    category="aerial",
                    description="Count aerial mapping features in an area",
                ),
                ToolInfo(
                    name="her_get_aerial_feature",
                    category="aerial",
                    description="Get full details of an aerial mapping feature",
                ),
                ToolInfo(
                    name="her_search_conservation_areas",
                    category="conservation_area",
                    description="Search conservation areas by name, LPA, or location",
                ),
                ToolInfo(
                    name="her_count_conservation_areas",
                    category="conservation_area",
                    description="Count conservation areas in an area",
                ),
                ToolInfo(
                    name="her_get_conservation_area",
                    category="conservation_area",
                    description="Get full details of a conservation area",
                ),
                ToolInfo(
                    name="her_search_heritage_at_risk",
                    category="heritage_at_risk",
                    description="Search heritage at risk register entries",
                ),
                ToolInfo(
                    name="her_count_heritage_at_risk",
                    category="heritage_at_risk",
                    description="Count heritage at risk entries in an area",
                ),
                ToolInfo(
                    name="her_get_heritage_at_risk",
                    category="heritage_at_risk",
                    description="Get full details of a heritage at risk entry",
                ),
                ToolInfo(
                    name="her_search_heritage_gateway",
                    category="gateway",
                    description="Search local HER data via Heritage Gateway",
                ),
                ToolInfo(
                    name="her_cross_reference",
                    category="crossref",
                    description="Cross-reference candidates against known assets",
                ),
                ToolInfo(
                    name="her_enrich_gateway",
                    category="crossref",
                    description="Resolve Gateway record coordinates for cross-referencing",
                ),
                ToolInfo(
                    name="her_nearby",
                    category="crossref",
                    description="Find heritage assets near a point",
                ),
                ToolInfo(
                    name="her_export_geojson",
                    category="export",
                    description="Export results as GeoJSON",
                ),
                ToolInfo(
                    name="her_export_for_lidar",
                    category="export",
                    description="Export for LiDAR cross-referencing",
                ),
            ]

            jurisdictions = sorted(
                {s.get("coverage", "") for s in sources_list if s.get("coverage")}
            )

            return format_response(
                CapabilitiesResponse(
                    server=ServerConfig.NAME,
                    version=ServerConfig.VERSION,
                    sources=source_infos,
                    tools=tools,
                    jurisdictions_available=jurisdictions,
                    jurisdictions_roadmap=[
                        "Scotland",
                        "Wales",
                        "Ireland",
                        "Netherlands",
                        "France",
                    ],
                    spatial_references=list(SUPPORTED_SRIDS.keys()),
                    max_results_per_query=2000,
                    tool_count=len(tools),
                    llm_guidance=(
                        "MULTI-SOURCE QUERIES: No single source has everything. "
                        "For comprehensive area surveys, ALWAYS search multiple "
                        "sources and merge results: "
                        "(1) her_search_monuments — NHLE designated assets "
                        "(scheduled monuments, listed buildings). "
                        "(2) her_search_aerial — AIM cropmarks, earthworks, "
                        "saltern mounds from aerial photos/LiDAR (not in NHLE). "
                        "(3) her_search_heritage_gateway — local HER records "
                        "for undesignated sites (red hills, findspots, fieldwork). "
                        "WORKFLOW: For a location query, run all relevant sources "
                        "in parallel, then combine and present unified results. "
                        "Use her_enrich_gateway to resolve Gateway coordinates, "
                        "then her_cross_reference to deduplicate across sources. "
                        "Use her_search_conservation_areas for conservation areas "
                        "and her_search_heritage_at_risk for at-risk assets. "
                        "Use count tools before fetching large result sets."
                    ),
                    message=f"{len(tools)} tools across {len(source_infos)} sources",
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Failed to get capabilities: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Failed to get capabilities"),
                output_mode,
            )
