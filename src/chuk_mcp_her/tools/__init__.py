"""MCP tool registration for chuk-mcp-her."""

from .aerial.api import register_aerial_tools
from .conservation_area.api import register_conservation_area_tools
from .crossref.api import register_crossref_tools
from .discovery.api import register_discovery_tools
from .export.api import register_export_tools
from .gateway.api import register_gateway_tools
from .heritage_at_risk.api import register_heritage_at_risk_tools
from .nhle.api import register_nhle_tools

__all__ = [
    "register_aerial_tools",
    "register_conservation_area_tools",
    "register_crossref_tools",
    "register_discovery_tools",
    "register_export_tools",
    "register_gateway_tools",
    "register_heritage_at_risk_tools",
    "register_nhle_tools",
]
