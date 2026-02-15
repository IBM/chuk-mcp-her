"""Cross-referencing and nearby search tools."""

from __future__ import annotations

import logging
from typing import Any

from ...constants import ErrorMessages, SuccessMessages
from ...core.coordinates import bearing_deg, distance_m, wgs84_to_bng
from ...core.spatial_index import GridSpatialIndex
from ...models.responses import (
    CrossReferenceMatch,
    CrossReferenceResponse,
    ErrorResponse,
    GatewayEnrichResponse,
    NearbyAssetInfo,
    NearbyResponse,
    format_response,
)

logger = logging.getLogger(__name__)


def _build_asset_dict(asset: dict[str, Any]) -> dict[str, Any]:
    """Build enriched asset dict for cross-reference output.

    Includes all available fields from any source (NHLE, AIM, Gateway).
    Fields that are None are excluded by format_response(exclude_none).
    """
    return {
        "record_id": asset.get("record_id"),
        "name": asset.get("name"),
        "source": asset.get("source"),
        "designation_type": asset.get("designation_type"),
        "grade": asset.get("grade"),
        "monument_type": asset.get("monument_type"),
        "period": asset.get("period"),
        "form": asset.get("form"),
        "evidence": asset.get("evidence"),
        "easting": asset.get("easting"),
        "northing": asset.get("northing"),
    }


def register_crossref_tools(mcp: object, registry: object) -> None:
    """Register cross-referencing and nearby search tools."""

    @mcp.tool  # type: ignore[union-attr]
    async def her_cross_reference(
        candidates: str = "[]",
        match_radius_m: float = 50.0,
        near_radius_m: float = 200.0,
        designation_types: str | None = None,
        include_aim: bool = False,
        gateway_sites: str = "[]",
        output_mode: str = "json",
    ) -> str:
        """Cross-reference candidate locations against known heritage assets.

        Takes a list of candidate locations (e.g. from LiDAR survey) and
        classifies each as match, near, or novel based on proximity to
        known NHLE records, AIM aerial mapping features, and optionally
        Heritage Gateway records.

        Args:
            candidates: JSON array of {"easting": x, "northing": y} dicts
            match_radius_m: Distance threshold for "match" (default 50m)
            near_radius_m: Distance threshold for "near" (default 200m)
            designation_types: Comma-separated NHLE designation types to match
                against (e.g. "scheduled_monument,listed_building")
            include_aim: Include AIM aerial mapping features in known assets
                (adds monument_type, period, form from aerial archaeology)
            gateway_sites: JSON array of Gateway records with easting/northing
                (output of her_enrich_gateway) to merge into known sites
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Classification of each candidate as match, near, or novel

        Tips for LLMs:
            - Input candidates as BNG easting/northing coordinates
            - "match" means the candidate is within match_radius_m of a known asset
            - "near" means within near_radius_m but not a match
            - "novel" means no known asset within near_radius_m
            - Set include_aim=true for LiDAR workflows to include aerial features
            - Use her_enrich_gateway first to resolve Gateway record coordinates,
              then pass the output as gateway_sites for richer cross-referencing
            - Use her_export_for_lidar to get known sites in the same area
        """
        import json as json_mod

        try:
            candidate_list = json_mod.loads(candidates)
            if not candidate_list:
                return format_response(
                    ErrorResponse(error="No candidates provided"),
                    output_mode,
                )

            # Get bounding box around all candidates
            eastings = [c.get("easting", 0) for c in candidate_list]
            northings = [c.get("northing", 0) for c in candidate_list]
            buffer = near_radius_m + 100
            bbox = (
                min(eastings) - buffer,
                min(northings) - buffer,
                max(eastings) + buffer,
                max(northings) + buffer,
            )

            # Parse designation type filter
            dtype_filter = None
            if designation_types:
                dtype_list = [dt.strip() for dt in designation_types.split(",")]
                dtype_filter = dtype_list[0] if len(dtype_list) == 1 else None

            # Fetch known NHLE assets in the area
            result = await registry.search_designations(  # type: ignore[union-attr]
                bbox=bbox,
                max_results=2000,
                designation_type=dtype_filter,
            )
            known = list(result.features)

            # Post-filter for multi-type designation filtering
            if designation_types and dtype_filter is None:
                dtype_set = {dt.strip() for dt in designation_types.split(",")}
                known = [f for f in known if f.get("designation_type") in dtype_set]

            # Merge AIM aerial mapping features if requested
            if include_aim:
                aim_result = await registry.search_aerial(  # type: ignore[union-attr]
                    bbox=bbox, max_results=2000
                )
                known.extend(aim_result.features)

            # Merge Gateway sites if provided
            gateway_list = json_mod.loads(gateway_sites)
            if gateway_list:
                known.extend(gateway_list)

            # Build spatial index for efficient matching
            index = GridSpatialIndex(cell_size_m=near_radius_m)
            index.build(known)

            # Classify each candidate
            matches = []
            near_misses = []
            novel_count = 0

            for candidate in candidate_list:
                ce = candidate.get("easting", 0)
                cn = candidate.get("northing", 0)

                best_asset, best_dist = index.nearest(ce, cn, near_radius_m)

                if best_asset is not None and best_dist <= match_radius_m:
                    matches.append(
                        CrossReferenceMatch(
                            candidate={"easting": ce, "northing": cn},
                            matched_asset=_build_asset_dict(best_asset),
                            distance_m=round(best_dist, 1),
                            classification="match",
                        )
                    )
                elif best_asset is not None and best_dist <= near_radius_m:
                    near_misses.append(
                        CrossReferenceMatch(
                            candidate={"easting": ce, "northing": cn},
                            nearest_asset=_build_asset_dict(best_asset),
                            distance_m=round(best_dist, 1),
                            classification="near",
                        )
                    )
                else:
                    novel_count += 1

            classification = {
                "match": len(matches),
                "near": len(near_misses),
                "novel": novel_count,
            }

            return format_response(
                CrossReferenceResponse(
                    candidates_submitted=len(candidate_list),
                    classification=classification,
                    matches=matches,
                    near_misses=near_misses,
                    novel_count=novel_count,
                    novel_summary=(
                        f"{novel_count} candidates have no known heritage asset "
                        f"within {near_radius_m}m. These are potential new discoveries."
                    )
                    if novel_count > 0
                    else None,
                    message=SuccessMessages.CROSS_REF_COMPLETE.format(
                        len(matches), len(near_misses), novel_count
                    ),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Cross-reference failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Cross-reference failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_nearby(
        lat: float | None = None,
        lon: float | None = None,
        easting: float | None = None,
        northing: float | None = None,
        radius_m: float = 500.0,
        max_results: int = 20,
        output_mode: str = "json",
    ) -> str:
        """Find heritage assets near a single point.

        Searches the NHLE for designated heritage assets within a
        radius of the given point. Returns assets sorted by distance.

        Args:
            lat: WGS84 latitude (use with lon)
            lon: WGS84 longitude (use with lat)
            easting: BNG easting (use with northing, alternative to lat/lon)
            northing: BNG northing (use with easting)
            radius_m: Search radius in metres (default 500)
            max_results: Maximum results (default 20)
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Nearby heritage assets with distance and bearing

        Tips for LLMs:
            - Use lat/lon OR easting/northing (not both)
            - Results are sorted by distance from the centre point
            - Each result includes distance_m and bearing_deg
        """
        try:
            # Resolve centre point to both coordinate systems
            if lat is not None and lon is not None:
                centre_lat, centre_lon = lat, lon
                centre_e, centre_n = wgs84_to_bng(lat, lon)
            elif easting is not None and northing is not None:
                from ...core.coordinates import bng_to_wgs84

                centre_e, centre_n = easting, northing
                centre_lat, centre_lon = bng_to_wgs84(easting, northing)
            else:
                return format_response(
                    ErrorResponse(
                        error=ErrorMessages.INVALID_COORDINATES.format(
                            "Provide lat/lon or easting/northing"
                        ),
                        error_type="validation_error",
                    ),
                    output_mode,
                )

            result = await registry.nearby(  # type: ignore[union-attr]
                lat=centre_lat,
                lon=centre_lon,
                radius_m=radius_m,
                max_results=max_results,
            )

            # Calculate distance and bearing for each result
            assets = []
            for f in result.features:
                fe = f.get("easting")
                fn = f.get("northing")
                dist = None
                bearing = None
                if fe is not None and fn is not None:
                    dist = round(distance_m(centre_e, centre_n, fe, fn), 1)
                    bearing = round(bearing_deg(centre_e, centre_n, fe, fn), 0)

                assets.append(
                    NearbyAssetInfo(
                        record_id=f.get("record_id", ""),
                        nhle_id=f.get("nhle_id"),
                        name=f.get("name", ""),
                        designation_type=f.get("designation_type"),
                        grade=f.get("grade"),
                        distance_m=dist,
                        bearing_deg=bearing,
                        lat=f.get("lat"),
                        lon=f.get("lon"),
                        easting=f.get("easting"),
                        northing=f.get("northing"),
                    )
                )

            # Sort by distance
            assets.sort(key=lambda a: a.distance_m if a.distance_m is not None else float("inf"))

            return format_response(
                NearbyResponse(
                    centre_lat=centre_lat,
                    centre_lon=centre_lon,
                    radius_m=radius_m,
                    count=len(assets),
                    assets=assets,
                    message=SuccessMessages.NEARBY_FOUND.format(len(assets), radius_m),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Nearby search failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Nearby search failed"),
                output_mode,
            )

    @mcp.tool  # type: ignore[union-attr]
    async def her_enrich_gateway(
        what: str | None = None,
        where: str | None = None,
        when: str | None = None,
        max_results: int = 100,
        fetch_details: bool = True,
        output_mode: str = "json",
    ) -> str:
        """Fetch Heritage Gateway records with resolved coordinates.

        Searches the Heritage Gateway for local HER records and resolves
        their BNG coordinates by parsing grid references and/or fetching
        detail pages. Returns only records with valid easting/northing,
        suitable for cross-referencing with her_cross_reference.

        Args:
            what: Monument type or keyword (e.g. "red hill", "saltern")
            where: Place name (e.g. "Blackwater", "Essex")
            when: Period (e.g. "Roman", "Iron Age")
            max_results: Maximum records to return (default 100)
            fetch_details: Fetch detail pages for coordinates (default true)
            output_mode: Response format — "json" (default) or "text"

        Returns:
            Gateway records with resolved BNG easting/northing coordinates

        Tips for LLMs:
            - This tool is SLOW (may take 1-2 minutes for 100 records)
            - Use it before her_cross_reference to enrich the known-sites pool
            - Pass the output records as gateway_sites to her_cross_reference
            - Set fetch_details=false for faster results (grid refs only)
            - Results include only records with successfully resolved coordinates
        """
        try:
            records, total_searched = await registry.enrich_gateway_records(  # type: ignore[union-attr]
                what=what,
                where=where,
                when=when,
                max_results=max_results,
                fetch_details=fetch_details,
            )

            resolved_count = len(records)
            unresolved_count = total_searched - resolved_count

            return format_response(
                GatewayEnrichResponse(
                    records=records,
                    count=resolved_count,
                    resolved_count=resolved_count,
                    unresolved_count=unresolved_count,
                    fetch_details_used=fetch_details,
                    message=SuccessMessages.GATEWAY_ENRICHED.format(resolved_count, total_searched),
                ),
                output_mode,
            )
        except Exception as e:
            logger.error("Gateway enrichment failed: %s", e)
            return format_response(
                ErrorResponse(error=str(e), message="Gateway enrichment failed"),
                output_mode,
            )
