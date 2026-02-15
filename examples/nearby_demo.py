#!/usr/bin/env python3
"""
Nearby Search Demo -- chuk-mcp-her

Finds all heritage assets within a radius of a given point,
sorted by distance. Demonstrates both WGS84 (lat/lon) and
BNG (easting/northing) input modes.

Demonstrates:
    her_nearby (with lat/lon)
    her_nearby (with easting/northing)

NOTE: This demo makes live API calls to the Historic England
ArcGIS Feature Service.

Usage:
    python examples/nearby_demo.py
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from tool_runner import ToolRunner


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}\n")


def print_nearby(result: dict) -> None:
    """Print nearby search results."""
    if "error" in result:
        print(f"  Error: {result['error']}")
        return

    print(f"  Centre: {result['centre_lat']:.4f}, {result['centre_lon']:.4f}")
    print(f"  Radius: {result['radius_m']}m")
    print(f"  Found: {result['count']} assets")
    print()

    for asset in result.get("assets", []):
        dist = f" ({asset['distance_m']:.0f}m)" if asset.get("distance_m") is not None else ""
        dtype = f" [{asset['designation_type']}]" if asset.get("designation_type") else ""
        bearing = f" {asset['bearing_deg']:.0f}deg" if asset.get("bearing_deg") is not None else ""
        print(f"  {asset['record_id']}: {asset['name']}{dtype}{dist}{bearing}")


async def main() -> None:
    runner = ToolRunner()

    print("=" * 60)
    print("chuk-mcp-her -- Nearby Search Demo")
    print("=" * 60)

    # ----- 1: Colchester Castle (lat/lon) -----------------------------
    section("1. Colchester Castle (500m radius, lat/lon)")

    result = await runner.run(
        "her_nearby",
        lat=51.8895,
        lon=0.9020,
        radius_m=500,
        max_results=20,
    )
    print_nearby(result)

    # ----- 2: Stonehenge (lat/lon, wider radius) ----------------------
    section("2. Stonehenge (2km radius, lat/lon)")

    result = await runner.run(
        "her_nearby",
        lat=51.1789,
        lon=-1.8262,
        radius_m=2000,
        max_results=15,
    )
    print_nearby(result)

    # ----- 3: Tower of London (easting/northing) ----------------------
    section("3. Tower of London (500m radius, BNG coordinates)")

    result = await runner.run(
        "her_nearby",
        easting=533500,
        northing=180500,
        radius_m=500,
        max_results=20,
    )
    print_nearby(result)

    # ----- 4: Text output mode ----------------------------------------
    section("4. Text Output Mode (Bath, 1km)")

    text = await runner.run_text(
        "her_nearby",
        lat=51.3811,
        lon=-2.3590,
        radius_m=1000,
        max_results=10,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
