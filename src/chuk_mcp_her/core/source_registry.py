"""
Source registry — central orchestrator for heritage data access.

Manages source adapters and provides unified query interface.
Analogous to ArchiveManager in chuk-mcp-maritime-archives.
"""

from __future__ import annotations

import logging
from typing import Any

from ..constants import SOURCE_METADATA, SourceId
from .adapters.aim import AIMAdapter
from .adapters.base import BaseSourceAdapter, PaginatedResult
from .adapters.conservation_area import ConservationAreaAdapter
from .adapters.heritage_at_risk import HeritageAtRiskAdapter
from .adapters.heritage_gateway import HeritageGatewayAdapter
from .adapters.nhle import NHLEAdapter
from .adapters.scotland import ScotlandAdapter
from .cache import ResponseCache

logger = logging.getLogger(__name__)


class SourceRegistry:
    """Central orchestrator for heritage data source access.

    Manages source adapters and routes queries to the appropriate
    source(s). All tool functions delegate to this registry.
    """

    def __init__(self, cache_dir: str | None = None) -> None:
        self._cache = ResponseCache(cache_dir)
        self._adapters: dict[str, BaseSourceAdapter] = {}
        self._register_default_adapters()

    def _register_default_adapters(self) -> None:
        """Register all built-in source adapters."""
        self._adapters[SourceId.NHLE] = NHLEAdapter(cache=self._cache)
        self._adapters[SourceId.AIM] = AIMAdapter(cache=self._cache)
        self._adapters[SourceId.CONSERVATION_AREA] = ConservationAreaAdapter(cache=self._cache)
        self._adapters[SourceId.HERITAGE_AT_RISK] = HeritageAtRiskAdapter(cache=self._cache)
        self._adapters[SourceId.HERITAGE_GATEWAY] = HeritageGatewayAdapter(cache=self._cache)
        self._adapters[SourceId.SCOTLAND] = ScotlandAdapter(cache=self._cache)

    def list_sources(self) -> list[dict[str, Any]]:
        """Return summary list of all registered sources."""
        sources = []
        for sid, adapter in self._adapters.items():
            meta = SOURCE_METADATA.get(sid, {})
            cap = adapter.capabilities
            status = "available"
            try:
                if not cap.supports_spatial_query and not cap.supports_text_search:
                    status = "stub"
            except Exception:
                status = "unavailable"

            sources.append(
                {
                    "id": sid,
                    "name": meta.get("name", sid),
                    "organisation": meta.get("organisation"),
                    "coverage": meta.get("coverage"),
                    "api_type": meta.get("api_type"),
                    "description": meta.get("description"),
                    "native_srid": meta.get("native_srid"),
                    "capabilities": [
                        k
                        for k, v in {
                            "spatial_query": cap.supports_spatial_query,
                            "text_search": cap.supports_text_search,
                            "feature_count": cap.supports_feature_count,
                            "attribute_filter": cap.supports_attribute_filter,
                            "pagination": cap.supports_pagination,
                        }.items()
                        if v
                    ],
                    "designation_types": cap.supported_designation_types,
                    "licence": meta.get("licence"),
                    "status": status,
                    "note": meta.get("note"),
                }
            )
        return sources

    def get_adapter(self, source_id: str) -> BaseSourceAdapter | None:
        """Get a specific source adapter by ID."""
        return self._adapters.get(source_id)

    # ================================================================
    # NHLE convenience methods
    # ================================================================

    async def search_monuments(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Search scheduled monuments via NHLE."""
        adapter = self._adapters[SourceId.NHLE]
        return await adapter.search(
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            designation_type="scheduled_monument",
            max_results=max_results,
            offset=offset,
        )

    async def get_monument(self, record_id: str) -> dict[str, Any] | None:
        """Get a single monument by NHLE ID."""
        adapter = self._adapters[SourceId.NHLE]
        return await adapter.get_by_id(record_id)

    async def search_listed_buildings(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        grade: str | None = None,
        max_results: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Search listed buildings via NHLE."""
        adapter = self._adapters[SourceId.NHLE]
        return await adapter.search(
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            designation_type="listed_building",
            grade=grade,
            max_results=max_results,
            offset=offset,
        )

    async def search_designations(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        designation_type: str | None = None,
        max_results: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Search all designation types via NHLE."""
        adapter = self._adapters[SourceId.NHLE]
        return await adapter.search(
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            designation_type=designation_type,
            max_results=max_results,
            offset=offset,
        )

    async def count_features(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        designation_type: str | None = None,
    ) -> dict[str, int]:
        """Count features by designation type."""
        from ..constants import DESIGNATION_TYPES

        adapter = self._adapters[SourceId.NHLE]
        counts: dict[str, int] = {}
        total = 0

        if designation_type:
            c = await adapter.count(bbox=bbox, designation_type=designation_type)
            counts[designation_type] = c
            total = c
        else:
            for dt in DESIGNATION_TYPES:
                c = await adapter.count(bbox=bbox, designation_type=dt)
                counts[dt] = c
                total += c

        counts["total"] = total
        return counts

    # ================================================================
    # AIM convenience methods
    # ================================================================

    async def search_aerial(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        monument_type: str | None = None,
        period: str | None = None,
        max_results: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Search aerial investigation mapping features via AIM."""
        adapter = self._adapters[SourceId.AIM]
        return await adapter.search(
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            max_results=max_results,
            offset=offset,
            monument_type=monument_type,
            period=period,
        )

    async def get_aerial_feature(self, record_id: str) -> dict[str, Any] | None:
        """Get a single AIM feature by HE_UID."""
        adapter = self._adapters[SourceId.AIM]
        return await adapter.get_by_id(record_id)

    async def count_aerial(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        monument_type: str | None = None,
        period: str | None = None,
    ) -> int:
        """Count aerial mapping features."""
        adapter = self._adapters[SourceId.AIM]
        return await adapter.count(
            bbox=bbox,
            monument_type=monument_type,
            period=period,
        )

    # ================================================================
    # Conservation Area convenience methods
    # ================================================================

    async def search_conservation_areas(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        lpa: str | None = None,
        max_results: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Search conservation areas."""
        adapter = self._adapters[SourceId.CONSERVATION_AREA]
        return await adapter.search(
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            max_results=max_results,
            offset=offset,
            lpa=lpa,
        )

    async def get_conservation_area(self, record_id: str) -> dict[str, Any] | None:
        """Get a single conservation area by UID."""
        adapter = self._adapters[SourceId.CONSERVATION_AREA]
        return await adapter.get_by_id(record_id)

    async def count_conservation_areas(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        query: str | None = None,
        lpa: str | None = None,
    ) -> int:
        """Count conservation areas."""
        adapter = self._adapters[SourceId.CONSERVATION_AREA]
        return await adapter.count(bbox=bbox, query=query, lpa=lpa)

    # ================================================================
    # Heritage at Risk convenience methods
    # ================================================================

    async def search_heritage_at_risk(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        heritage_category: str | None = None,
        max_results: int = 100,
        offset: int = 0,
    ) -> PaginatedResult:
        """Search heritage at risk entries."""
        adapter = self._adapters[SourceId.HERITAGE_AT_RISK]
        return await adapter.search(
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            max_results=max_results,
            offset=offset,
            heritage_category=heritage_category,
        )

    async def get_heritage_at_risk(self, record_id: str) -> dict[str, Any] | None:
        """Get a single heritage at risk entry."""
        adapter = self._adapters[SourceId.HERITAGE_AT_RISK]
        return await adapter.get_by_id(record_id)

    async def count_heritage_at_risk(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        heritage_category: str | None = None,
    ) -> int:
        """Count heritage at risk entries."""
        adapter = self._adapters[SourceId.HERITAGE_AT_RISK]
        return await adapter.count(bbox=bbox, heritage_category=heritage_category)

    # ================================================================
    # Heritage Gateway convenience methods
    # ================================================================

    async def search_heritage_gateway(
        self,
        what: str | None = None,
        where: str | None = None,
        when: str | None = None,
        max_results: int = 50,
    ) -> PaginatedResult:
        """Search local HER records via Heritage Gateway."""
        adapter = self._adapters[SourceId.HERITAGE_GATEWAY]
        return await adapter.search(
            query=what,
            max_results=max_results,
            what=what,
            where=where,
            when=when,
        )

    async def enrich_gateway_records(
        self,
        what: str | None = None,
        where: str | None = None,
        when: str | None = None,
        max_results: int = 100,
        fetch_details: bool = True,
    ) -> tuple[list[dict[str, Any]], int]:
        """Search Heritage Gateway and resolve coordinates for each record.

        Workflow:
        1. Search Heritage Gateway for records
        2. For each record missing coordinates:
           a. Try parsing grid_reference if present
           b. If fetch_details and still no coords, fetch detail page
        3. Return only records with valid easting/northing

        This method is slow (~1 sec per detail page fetch). Intended
        for enrichment workflows, not interactive queries.

        Returns:
            Tuple of (enriched_records, total_searched).
        """
        from .coordinates import grid_ref_to_bng

        result = await self.search_heritage_gateway(
            what=what, where=where, when=when, max_results=max_results
        )

        adapter = self._adapters[SourceId.HERITAGE_GATEWAY]
        enriched: list[dict[str, Any]] = []
        total_searched = len(result.features)

        for feature in result.features:
            record = dict(feature)

            # Already has coordinates?
            if record.get("easting") is not None and record.get("northing") is not None:
                enriched.append(record)
                continue

            # Try grid reference parsing
            grid_ref = record.get("grid_reference")
            if grid_ref:
                try:
                    e, n = grid_ref_to_bng(grid_ref)
                    record["easting"] = e
                    record["northing"] = n
                    enriched.append(record)
                    continue
                except ValueError:
                    pass

            # Fetch detail page for coordinates
            if fetch_details and record.get("url"):
                detail = await adapter.get_by_id(record["url"])
                if detail:
                    if detail.get("easting") is not None and detail.get("northing") is not None:
                        record["easting"] = detail["easting"]
                        record["northing"] = detail["northing"]
                        if detail.get("grid_reference"):
                            record["grid_reference"] = detail["grid_reference"]
                        enriched.append(record)
                        continue

                    # Try grid ref from detail page
                    detail_ref = detail.get("grid_reference")
                    if detail_ref:
                        try:
                            e, n = grid_ref_to_bng(detail_ref)
                            record["easting"] = e
                            record["northing"] = n
                            record["grid_reference"] = detail_ref
                            enriched.append(record)
                            continue
                        except ValueError:
                            pass

        return enriched, total_searched

    # ================================================================
    # Scotland convenience methods
    # ================================================================

    async def search_scotland(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        site_type: str | None = None,
        broad_class: str | None = None,
        council: str | None = None,
        max_results: int = 100,
    ) -> PaginatedResult:
        """Search Scottish NRHE records (Canmore Points)."""
        adapter = self._adapters[SourceId.SCOTLAND]
        return await adapter.search(
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            max_results=max_results,
            site_type=site_type,
            broad_class=broad_class,
            council=council,
        )

    async def get_scotland_record(self, record_id: str) -> dict[str, Any] | None:
        """Get a single Scottish NRHE record by Canmore ID."""
        adapter = self._adapters[SourceId.SCOTLAND]
        return await adapter.get_by_id(record_id)

    async def search_scotland_designations(
        self,
        designation_type: str | None = None,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        max_results: int = 100,
    ) -> PaginatedResult:
        """Search Scottish designated heritage assets."""
        adapter = self._adapters[SourceId.SCOTLAND]
        return await adapter.search_designations(
            designation_type=designation_type,
            query=query,
            bbox=bbox,
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            max_results=max_results,
        )

    # ================================================================
    # Cross-cutting convenience methods
    # ================================================================

    async def nearby(
        self,
        lat: float,
        lon: float,
        radius_m: float = 500.0,
        designation_types: list[str] | None = None,
        max_results: int = 20,
    ) -> PaginatedResult:
        """Find NHLE heritage assets near a point.

        Searches NHLE only. For Scottish or aerial results callers must
        query ScotlandAdapter.search() or AIMAdapter.search() separately.
        """
        adapter = self._adapters[SourceId.NHLE]
        dtype = designation_types[0] if designation_types and len(designation_types) == 1 else None
        return await adapter.search(
            lat=lat,
            lon=lon,
            radius_m=radius_m,
            designation_type=dtype,
            max_results=max_results,
        )

    async def close(self) -> None:
        """Close all adapters."""
        for adapter in self._adapters.values():
            await adapter.close()
