#!/usr/bin/env python3
"""
Quick Start -- chuk-mcp-her

Demonstrates the core workflow:
  1. Check server status
  2. Count heritage features in an area
  3. Search for scheduled monuments by name
  4. Get details for a specific monument
  5. Find nearby heritage assets

NOTE: Steps 2-5 make live API calls to the Historic England
ArcGIS Feature Service.

Usage:
    python examples/quick_start.py
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


async def main() -> None:
    runner = ToolRunner()

    print("=" * 60)
    print("  chuk-mcp-her -- Quick Start Demo")
    print("  Historic England NHLE (live API calls)")
    print("=" * 60)

    # ------------------------------------------------------------------
    # 1. Server status (offline)
    # ------------------------------------------------------------------
    section("1. Server Status")

    result = await runner.run("her_status")
    print(f"  Server: {result['server']} v{result['version']}")
    print(f"  Tools: {result['tool_count']}")
    for sid, info in result.get("sources", {}).items():
        print(f"  {sid}: {info['status']}")

    # ------------------------------------------------------------------
    # 2. Count features in the Blackwater Estuary area
    # ------------------------------------------------------------------
    section("2. Count Heritage Features (Blackwater Estuary)")

    result = await runner.run(
        "her_count_features",
        bbox="586000,205000,602500,215000",
    )
    if "error" not in result:
        print(f"  {result['message']}")
        for dtype, count in result.get("counts", {}).items():
            print(f"    {dtype}: {count}")
    else:
        print(f"  Error: {result['error']}")
        print("  (This demo requires network access to Historic England)")

    # ------------------------------------------------------------------
    # 3. Search for scheduled monuments by name
    # ------------------------------------------------------------------
    section("3. Search Scheduled Monuments: 'red hill'")

    result = await runner.run(
        "her_search_monuments",
        name="red hill",
        max_results=5,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for m in result.get("monuments", []):
            grade = f" (Grade {m['grade']})" if m.get("grade") else ""
            print(f"  {m['record_id']}: {m['name']}{grade}")
            if m.get("lat"):
                print(f"    Location: {m['lat']:.4f}, {m['lon']:.4f}")
    else:
        print(f"  Error: {result['error']}")

    # ------------------------------------------------------------------
    # 4. Get monument detail
    # ------------------------------------------------------------------
    section("4. Monument Detail")

    if "error" not in result and result.get("monuments"):
        first_id = result["monuments"][0]["nhle_id"]
        detail = await runner.run("her_get_monument", nhle_id=first_id)
        if "error" not in detail:
            monument = detail.get("monument", {})
            print(f"  Name: {monument.get('name')}")
            print(f"  Designation: {monument.get('designation_type')}")
            print(f"  Listed: {monument.get('list_date')}")
            print(f"  URL: {monument.get('url')}")
        else:
            print(f"  Error: {detail['error']}")
    else:
        print("  No monuments found to retrieve details for")

    # ------------------------------------------------------------------
    # 5. Find nearby heritage assets
    # ------------------------------------------------------------------
    section("5. Nearby Assets (Colchester Castle, 500m)")

    result = await runner.run(
        "her_nearby",
        lat=51.8895,
        lon=0.9020,
        radius_m=500,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Centre: {result['centre_lat']}, {result['centre_lon']}")
        print(f"  Radius: {result['radius_m']}m")
        print(f"  Found: {result['count']} assets")
        for asset in result.get("assets", [])[:5]:
            dist = f" ({asset['distance_m']}m)" if asset.get("distance_m") else ""
            dtype = f" [{asset['designation_type']}]" if asset.get("designation_type") else ""
            print(f"  {asset['record_id']}: {asset['name']}{dtype}{dist}")
        if result["count"] > 5:
            print(f"  ... and {result['count'] - 5} more")
    else:
        print(f"  Error: {result['error']}")

    print(f"\n{'=' * 60}")
    print("  Demo complete!")
    print(f"{'=' * 60}\n")

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
