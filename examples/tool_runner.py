#!/usr/bin/env python3
"""
Tool Runner for chuk-mcp-her

Utility for running MCP tools standalone without a full MCP runtime.
Captures tools registered via @mcp.tool decorators and provides
a simple interface for testing and demos.

23 tools across 8 categories.

Usage:
    from tool_runner import ToolRunner

    async def main():
        runner = ToolRunner()
        result = await runner.run("her_search_monuments", name="red hill")
        print(result)
"""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from chuk_mcp_her.core.source_registry import SourceRegistry
from chuk_mcp_her.tools import (
    register_aerial_tools,
    register_conservation_area_tools,
    register_crossref_tools,
    register_discovery_tools,
    register_export_tools,
    register_gateway_tools,
    register_heritage_at_risk_tools,
    register_nhle_tools,
)


class _MiniMCP:
    """Minimal MCP server that captures tools registered via @mcp.tool."""

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def tool(self, fn: Any) -> Any:
        self._tools[fn.__name__] = fn
        return fn

    def get_tool(self, name: str) -> Any:
        return self._tools[name]

    def get_tools(self) -> list[Any]:
        return list(self._tools.values())

    @property
    def tool_names(self) -> list[str]:
        return sorted(self._tools.keys())


class ToolRunner:
    """Run chuk-mcp-her MCP tools directly from Python.

    All MCP tools are registered and callable via run(tool_name, **kwargs).
    Returns parsed JSON (dict/list) by default. Use run_text() for
    human-readable output.
    """

    def __init__(self) -> None:
        self._mcp = _MiniMCP()
        self.registry = SourceRegistry()
        register_discovery_tools(self._mcp, self.registry)
        register_nhle_tools(self._mcp, self.registry)
        register_aerial_tools(self._mcp, self.registry)
        register_conservation_area_tools(self._mcp, self.registry)
        register_heritage_at_risk_tools(self._mcp, self.registry)
        register_gateway_tools(self._mcp, self.registry)
        register_crossref_tools(self._mcp, self.registry)
        register_export_tools(self._mcp, self.registry)

    @property
    def tool_names(self) -> list[str]:
        """List all registered tool names."""
        return self._mcp.tool_names

    def list_tools(self) -> list[str]:
        """List all registered tool names."""
        return self._mcp.tool_names

    async def run(self, tool_name: str, **kwargs: Any) -> dict:
        """Call tool as plain async function, return parsed JSON."""
        fn = self._mcp.get_tool(tool_name)
        result = await fn(**kwargs)
        return json.loads(result)

    async def run_text(self, tool_name: str, **kwargs: Any) -> str:
        """Call tool, return text output."""
        fn = self._mcp.get_tool(tool_name)
        return await fn(output_mode="text", **kwargs)

    async def run_raw(self, tool_name: str, **kwargs: Any) -> str:
        """Call tool, return raw JSON string."""
        fn = self._mcp.get_tool(tool_name)
        return await fn(**kwargs)

    async def close(self) -> None:
        """Close the source registry."""
        await self.registry.close()


async def main() -> None:
    runner = ToolRunner()

    if len(sys.argv) < 2:
        print("Available tools:")
        for name in runner.list_tools():
            print(f"  {name}")
        return

    tool_name = sys.argv[1]
    result = await runner.run(tool_name)
    print(json.dumps(result, indent=2))

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
