"""
Async server setup for chuk-mcp-her.

Creates the ChukMCPServer instance, instantiates the SourceRegistry,
and registers all tool groups.
"""

from chuk_mcp_server import ChukMCPServer

from .constants import ServerConfig
from .core.source_registry import SourceRegistry
from .tools import (
    register_aerial_tools,
    register_conservation_area_tools,
    register_crossref_tools,
    register_discovery_tools,
    register_export_tools,
    register_gateway_tools,
    register_heritage_at_risk_tools,
    register_map_tools,
    register_nhle_tools,
    register_scotland_tools,
)

mcp = ChukMCPServer(ServerConfig.NAME)
registry = SourceRegistry()

# Register all tool groups
register_discovery_tools(mcp, registry)
register_nhle_tools(mcp, registry)
register_aerial_tools(mcp, registry)
register_conservation_area_tools(mcp, registry)
register_heritage_at_risk_tools(mcp, registry)
register_gateway_tools(mcp, registry)
register_crossref_tools(mcp, registry)
register_scotland_tools(mcp, registry)
register_map_tools(mcp, registry)
register_export_tools(mcp, registry)
