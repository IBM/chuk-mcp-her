"""
Heritage Gateway adapter — best-effort scraper for local HERs.

Searches the Heritage Gateway website to access local Historic
Environment Records across England. Returns empty results
gracefully when the Gateway is unavailable.
"""

from __future__ import annotations

import logging
from typing import Any

from ..cache import ResponseCache
from ..gateway_client import GatewayClient
from .base import BaseSourceAdapter, PaginatedResult, SourceCapabilities

logger = logging.getLogger(__name__)


class HeritageGatewayAdapter(BaseSourceAdapter):
    """Adapter for Heritage Gateway local HER search.

    Best-effort access to 60+ local HERs via web scraping.
    Returns empty results gracefully on failure.
    """

    @property
    def source_id(self) -> str:
        return "heritage_gateway"

    @property
    def capabilities(self) -> SourceCapabilities:
        return SourceCapabilities(
            supports_text_search=True,
        )

    def __init__(self, cache: ResponseCache | None = None) -> None:
        self._client = GatewayClient(cache=cache)

    async def search(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        designation_type: str | None = None,
        grade: str | None = None,
        max_results: int = 50,
        offset: int = 0,
        **kwargs: Any,
    ) -> PaginatedResult:
        """Search Heritage Gateway for local HER records.

        Args:
            query: Text search — maps to 'what' field.
            bbox: Unused (spatial search not supported via scraper).
            lat, lon, radius_m: Unused.
            designation_type, grade: Unused.
            max_results: Max records to return.
            offset: Pagination offset.
            **kwargs: what, where, when — Heritage Gateway search fields.
        """
        what = kwargs.get("what") or query
        where = kwargs.get("where")
        when = kwargs.get("when")

        result = await self._client.search(
            what=what, where=where, when=when, max_results=max_results
        )

        records = result.get("records", [])
        normalized = [self._normalize_record(r) for r in records]

        # Apply offset for pagination
        if offset > 0:
            normalized = normalized[offset:]

        total_count = result.get("total_count", len(normalized))
        has_more = result.get("has_more", False)

        return PaginatedResult(
            features=normalized[:max_results],
            total_count=total_count,
            has_more=has_more,
        )

    async def get_by_id(self, record_id: str) -> dict[str, Any] | None:
        """Get a single record by URL or record ID.

        The record_id should be a Heritage Gateway detail page URL
        or a record UID.
        """
        if record_id.startswith("http"):
            url = record_id
        else:
            url = f"{self._client._client and ''}{record_id}"
            # Can't look up by ID without a URL — return None
            logger.debug("Gateway get_by_id requires a URL, got: %s", record_id)
            return None

        record = await self._client.get_record(url)
        if record is None:
            return None
        return self._normalize_record(record)

    async def close(self) -> None:
        await self._client.close()

    @staticmethod
    def _normalize_record(raw: dict[str, Any]) -> dict[str, Any]:
        """Normalize a scraped Gateway record to standard schema."""
        return {
            "record_id": raw.get("record_id"),
            "name": raw.get("name"),
            "source": "heritage_gateway",
            "source_her": raw.get("source_her"),
            "monument_type": raw.get("monument_type"),
            "period": raw.get("period"),
            "description": raw.get("description"),
            "grid_reference": raw.get("grid_reference"),
            "easting": raw.get("easting"),
            "northing": raw.get("northing"),
            "designation": raw.get("designation"),
            "url": raw.get("url"),
        }
