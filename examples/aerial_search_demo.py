#!/usr/bin/env python3
"""
Aerial Search Demo -- chuk-mcp-her

Demonstrates the AIM (Aerial Investigation and Mapping) tools for
searching Historic England's 470,000+ aerial archaeology features:
cropmarks, earthworks, enclosures, ring ditches, saltern mounds.

Demonstrates:
    her_count_aerial
    her_search_aerial
    her_get_aerial_feature

NOTE: This demo makes live API calls to the Historic England
AIM ArcGIS Feature Service.

Usage:
    python examples/aerial_search_demo.py
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
    print("chuk-mcp-her -- Aerial Investigation & Mapping Demo")
    print("=" * 60)

    # Stonehenge / Salisbury Plain study area (BNG) — rich in aerial archaeology
    bbox = "410000,138000,420000,148000"

    # ----- 1: Count aerial features in the Stonehenge area -----
    section("1. Count Aerial Features: Stonehenge Area")

    result = await runner.run("her_count_aerial", bbox=bbox)
    if "error" not in result:
        print(f"  {result['message']}")
        print(f"  Total AIM features in study area: {result['count']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 2: Count enclosures specifically -----
    section("2. Count Enclosures in Stonehenge Area")

    result = await runner.run(
        "her_count_aerial",
        bbox=bbox,
        monument_type="ENCLOSURE",
    )
    if "error" not in result:
        print(f"  Enclosures: {result['count']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Search for enclosures with full detail -----
    section("3. Search Enclosures (first 10)")

    result = await runner.run(
        "her_search_aerial",
        bbox=bbox,
        monument_type="ENCLOSURE",
        max_results=10,
    )
    first_aim_id = None
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for f in result.get("features", []):
            loc = ""
            if f.get("lat"):
                loc = f" [{f['lat']:.4f}, {f['lon']:.4f}]"
            print(f"  {f.get('aim_id', '?')}: {f.get('monument_type')} ({f.get('period')}){loc}")
            if first_aim_id is None and f.get("aim_id"):
                first_aim_id = f["aim_id"]
    else:
        print(f"  Error: {result['error']}")

    # ----- 4: Search for Iron Age features -----
    section("4. Iron Age Features in Stonehenge Area")

    result = await runner.run(
        "her_search_aerial",
        bbox=bbox,
        period="IRON AGE",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for f in result.get("features", []):
            print(f"  {f.get('aim_id', '?')}: {f.get('monument_type')} ({f.get('period')})")
    else:
        print(f"  Error: {result['error']}")

    # ----- 5: Search near Stonehenge -----
    section("5. Aerial Features near Stonehenge (2km)")

    result = await runner.run(
        "her_search_aerial",
        lat=51.1789,
        lon=-1.8262,
        radius_m=2000,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for f in result.get("features", []):
            evidence = f" [{f.get('evidence')}]" if f.get("evidence") else ""
            print(
                f"  {f.get('aim_id', '?')}: {f.get('monument_type')} ({f.get('period')}){evidence}"
            )
    else:
        print(f"  Error: {result['error']}")

    # ----- 6: Get detail for a specific feature -----
    section("6. Feature Detail")

    if first_aim_id:
        result = await runner.run(
            "her_get_aerial_feature",
            record_id=first_aim_id,
        )
        if "error" not in result:
            m = result.get("monument", {})
            print(f"  Record ID: {m.get('record_id')}")
            print(f"  Name: {m.get('name')}")
            print(f"  Monument Type: {m.get('monument_type')}")
            print(f"  Period: {m.get('period')}")
            print(f"  Form: {m.get('form')}")
            print(f"  Evidence: {m.get('evidence')}")
            print(f"  Project: {m.get('project')}")
            print(f"  HER No: {m.get('her_no')}")
            if m.get("lat"):
                print(f"  Location: {m['lat']:.4f}, {m['lon']:.4f}")
            if m.get("easting"):
                print(f"  BNG: E={m['easting']:.0f}, N={m['northing']:.0f}")
        else:
            print(f"  Error: {result['error']}")
    else:
        print("  No features found for detail lookup")

    # ----- 7: Text output mode -----
    section("7. Text Output Mode")

    text = await runner.run_text(
        "her_search_aerial",
        bbox=bbox,
        monument_type="MOUND",
        max_results=5,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
