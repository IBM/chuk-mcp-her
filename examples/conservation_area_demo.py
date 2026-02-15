#!/usr/bin/env python3
"""
Conservation Area Demo -- chuk-mcp-her

Demonstrates the Conservation Area tools for searching
Historic England's 8,000+ conservation areas across England.

Demonstrates:
    her_count_conservation_areas
    her_search_conservation_areas
    her_get_conservation_area

NOTE: This demo makes live API calls to the Historic England
Conservation Areas ArcGIS Feature Service.

Usage:
    python examples/conservation_area_demo.py
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
    print("chuk-mcp-her -- Conservation Area Demo")
    print("=" * 60)

    # Maldon / Blackwater study area (BNG)
    bbox = "580000,200000,600000,215000"

    # ----- 1: Count conservation areas in the study area -----
    section("1. Count Conservation Areas: Maldon/Blackwater Area")

    result = await runner.run("her_count_conservation_areas", bbox=bbox)
    if "error" not in result:
        print(f"  {result['message']}")
        print(f"  Conservation areas in study area: {result['count']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 2: Search by name -----
    section("2. Search for 'Maldon' Conservation Areas")

    result = await runner.run(
        "her_search_conservation_areas",
        query="Maldon",
        max_results=10,
    )
    first_record_id = None
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for a in result.get("areas", []):
            lpa = f" [{a.get('lpa')}]" if a.get("lpa") else ""
            print(f"  {a.get('record_id', '?')}: {a.get('name')}{lpa}")
            if first_record_id is None and a.get("record_id"):
                first_record_id = a["record_id"]
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Search by LPA -----
    section("3. Search by Local Planning Authority")

    result = await runner.run(
        "her_search_conservation_areas",
        lpa="Maldon",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for a in result.get("areas", []):
            date = f" (designated {a['designation_date']})" if a.get("designation_date") else ""
            print(f"  {a.get('record_id', '?')}: {a.get('name')}{date}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 4: Spatial search near Maldon -----
    section("4. Conservation Areas near Maldon (5km)")

    result = await runner.run(
        "her_search_conservation_areas",
        lat=51.732,
        lon=0.677,
        radius_m=5000,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for a in result.get("areas", []):
            loc = ""
            if a.get("lat"):
                loc = f" [{a['lat']:.4f}, {a['lon']:.4f}]"
            print(f"  {a.get('record_id', '?')}: {a.get('name')}{loc}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 5: Get detail for a specific conservation area -----
    section("5. Conservation Area Detail")

    if first_record_id:
        result = await runner.run(
            "her_get_conservation_area",
            record_id=first_record_id,
        )
        if "error" not in result:
            m = result.get("monument", {})
            print(f"  Record ID: {m.get('record_id')}")
            print(f"  Name: {m.get('name')}")
            print(f"  LPA: {m.get('lpa')}")
            print(f"  Designation Date: {m.get('designation_date')}")
            if m.get("lat"):
                print(f"  Location: {m['lat']:.4f}, {m['lon']:.4f}")
            if m.get("easting"):
                print(f"  BNG: E={m['easting']:.0f}, N={m['northing']:.0f}")
            if m.get("area_sqm"):
                print(f"  Area: {m['area_sqm']:.0f} sqm")
        else:
            print(f"  Error: {result['error']}")
    else:
        print("  No conservation areas found for detail lookup")

    # ----- 6: Text output mode -----
    section("6. Text Output Mode")

    text = await runner.run_text(
        "her_search_conservation_areas",
        bbox=bbox,
        max_results=5,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
