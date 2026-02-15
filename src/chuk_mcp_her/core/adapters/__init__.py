"""Source adapters for heritage data providers."""

from .aim import AIMAdapter
from .base import BaseSourceAdapter, PaginatedResult, SourceCapabilities
from .conservation_area import ConservationAreaAdapter
from .heritage_at_risk import HeritageAtRiskAdapter
from .heritage_gateway import HeritageGatewayAdapter
from .nhle import NHLEAdapter

__all__ = [
    "AIMAdapter",
    "BaseSourceAdapter",
    "ConservationAreaAdapter",
    "HeritageAtRiskAdapter",
    "HeritageGatewayAdapter",
    "NHLEAdapter",
    "PaginatedResult",
    "SourceCapabilities",
]
