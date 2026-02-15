"""
Base class for heritage data source adapters.

Each jurisdiction/source implements a concrete adapter that declares
its capabilities and provides search/get methods.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class SourceCapabilities:
    """Declares what a source adapter can do."""

    supports_spatial_query: bool = False
    supports_text_search: bool = False
    supports_feature_count: bool = False
    supports_attribute_filter: bool = False
    supports_pagination: bool = False
    supported_designation_types: list[str] = field(default_factory=list)


@dataclass
class PaginatedResult:
    """Paginated search result from a source adapter."""

    features: list[dict[str, Any]]
    total_count: int | None = None
    has_more: bool = False
    next_offset: int | None = None


class BaseSourceAdapter(ABC):
    """Abstract base for heritage data source adapters.

    Each adapter wraps a specific data source (ArcGIS, web scraper, etc.)
    and provides a uniform interface for search and retrieval.
    """

    @property
    @abstractmethod
    def source_id(self) -> str:
        """Unique identifier for this source."""
        ...

    @property
    @abstractmethod
    def capabilities(self) -> SourceCapabilities:
        """Declare what this adapter supports."""
        ...

    @abstractmethod
    async def search(
        self,
        query: str | None = None,
        bbox: tuple[float, float, float, float] | None = None,
        lat: float | None = None,
        lon: float | None = None,
        radius_m: float | None = None,
        designation_type: str | None = None,
        grade: str | None = None,
        max_results: int = 100,
        offset: int = 0,
        **kwargs: Any,
    ) -> PaginatedResult:
        """Search for heritage features."""
        ...

    @abstractmethod
    async def get_by_id(self, record_id: str) -> dict[str, Any] | None:
        """Get a single record by its identifier."""
        ...

    async def count(
        self,
        bbox: tuple[float, float, float, float] | None = None,
        designation_type: str | None = None,
        **kwargs: Any,
    ) -> int:
        """Count features matching criteria.

        Default implementation searches with max_results=0 and reads
        total_count. Override for sources that support native counting.
        """
        result = await self.search(
            bbox=bbox,
            designation_type=designation_type,
            max_results=1,
            **kwargs,
        )
        return result.total_count or len(result.features)

    async def close(self) -> None:
        """Clean up resources. Override if the adapter holds connections."""
