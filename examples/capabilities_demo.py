#!/usr/bin/env python3
"""
Capabilities Demo -- chuk-mcp-her

Quick-start script showing what the server can do. Lists sources,
tools, designation types, and demonstrates dual output mode
(JSON vs text). No network access required -- discovery tools
run entirely offline.

Demonstrates:
    her_status
    her_list_sources
    her_capabilities

Usage:
    python examples/capabilities_demo.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from tool_runner import ToolRunner


async def main() -> None:
    runner = ToolRunner()

    print("=" * 60)
    print("chuk-mcp-her -- Server Capabilities")
    print("=" * 60)

    # List all registered tools
    print(f"\nRegistered tools ({len(runner.tool_names)}):")
    for name in runner.tool_names:
        print(f"  - {name}")

    # Server capabilities (JSON mode)
    caps = await runner.run("her_capabilities")
    print(f"\nServer: {caps['server']} v{caps['version']}")
    print(f"Tools: {caps['tool_count']}")

    # Sources
    print(f"\nData Sources ({len(caps['sources'])}):")
    for source in caps["sources"]:
        status = source.get("status", "?")
        print(f"  {source['source_id']:20s}  {source['name']}  [{status}]")
        if source.get("coverage"):
            print(f"  {'':<20}  Coverage: {source['coverage']}")
        if source.get("capabilities"):
            print(f"  {'':<20}  Capabilities: {', '.join(source['capabilities'])}")

    # Tools
    print(f"\nTools ({len(caps['tools'])}):")
    for tool in caps["tools"]:
        print(f"  {tool['name']:35s} [{tool['category']:12s}] {tool['description']}")

    # Jurisdictions
    print(f"\nActive jurisdictions: {', '.join(caps.get('jurisdictions_available', []))}")
    print(f"Roadmap jurisdictions: {', '.join(caps.get('jurisdictions_roadmap', []))}")

    # Spatial references
    print(f"Spatial references: {caps.get('spatial_references', [])}")
    print(f"Max results per query: {caps.get('max_results_per_query', '?')}")

    # ---------------------------------------------------------------
    # Source detail
    # ---------------------------------------------------------------
    print("\n" + "-" * 60)
    print("Source Details (her_list_sources)")
    print("-" * 60)

    sources = await runner.run("her_list_sources")
    for source in sources["sources"]:
        print(f"\n  {source['source_id']}: {source['name']}")
        print(f"    Organisation: {source.get('organisation', 'N/A')}")
        print(f"    API type: {source.get('api_type', 'N/A')}")
        print(f"    Status: {source['status']}")
        if source.get("designation_types"):
            print(f"    Designation types: {', '.join(source['designation_types'])}")
        if source.get("note"):
            print(f"    Note: {source['note']}")

    # ---------------------------------------------------------------
    # Server status
    # ---------------------------------------------------------------
    print("\n" + "-" * 60)
    print("Server Status (her_status)")
    print("-" * 60)

    status = await runner.run("her_status")
    print(f"\n  Server: {status['server']} v{status['version']}")
    print(f"  Tools: {status['tool_count']}")
    for sid, info in status.get("sources", {}).items():
        print(f"  {sid}: {info['status']}")

    # ---------------------------------------------------------------
    # Dual output mode
    # ---------------------------------------------------------------
    print("\n" + "-" * 60)
    print("Dual Output Mode Demo")
    print("-" * 60)

    # Status in text mode
    print("\nher_status (output_mode='text'):")
    text = await runner.run_text("her_status")
    print(text)

    # Capabilities in text mode
    print("\nher_capabilities (output_mode='text'):")
    text = await runner.run_text("her_capabilities")
    print(text)

    print("\n" + "=" * 60)
    print("All capabilities shown above require no network access.")
    print("Run other demos to see search, cross-referencing, and")
    print("export features in action.")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
