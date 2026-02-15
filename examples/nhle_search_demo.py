#!/usr/bin/env python3
"""
NHLE Search Demo -- chuk-mcp-her

Demonstrates the full range of NHLE query tools: monument search,
listed building search with grade filtering, generic designation
search, feature counting, and monument detail retrieval.

Demonstrates:
    her_search_monuments
    her_get_monument
    her_search_listed_buildings
    her_search_designations
    her_count_features

NOTE: This demo makes live API calls to the Historic England
ArcGIS Feature Service.

Usage:
    python examples/nhle_search_demo.py
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
    print("chuk-mcp-her -- NHLE Search Demo")
    print("=" * 60)

    # ----- 1: Count features in the Blackwater estuary area -----------
    section("1. Feature Counts: Blackwater Estuary")

    counts = await runner.run(
        "her_count_features",
        bbox="586000,205000,602500,215000",
    )
    if "error" not in counts:
        print(f"  {counts['message']}")
        for dtype, count in counts.get("counts", {}).items():
            print(f"    {dtype}: {count}")
    else:
        print(f"  Error: {counts['error']}")

    # ----- 2: Search for scheduled monuments by name ------------------
    section("2. Scheduled Monuments: 'red hill'")

    result = await runner.run(
        "her_search_monuments",
        name="red hill",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for m in result.get("monuments", []):
            print(f"  {m['record_id']}: {m['name']}")
            if m.get("lat"):
                print(f"    Location: {m['lat']:.4f}, {m['lon']:.4f}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Search with bounding box --------------------------------
    section("3. Monuments in Blackwater Estuary (bbox)")

    result = await runner.run(
        "her_search_monuments",
        bbox="586000,205000,602500,215000",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']}")
        for m in result.get("monuments", []):
            print(f"  {m['record_id']}: {m['name']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 4: Grade I listed buildings near Stonehenge ----------------
    section("4. Grade I Listed Buildings near Stonehenge (5km)")

    result = await runner.run(
        "her_search_listed_buildings",
        lat=51.1789,
        lon=-1.8262,
        radius_m=5000,
        grade="I",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']}")
        for m in result.get("monuments", []):
            grade = f" (Grade {m['grade']})" if m.get("grade") else ""
            print(f"  {m['record_id']}: {m['name']}{grade}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 5: Generic designation search ------------------------------
    section("5. All Designation Types near Tower of London (1km)")

    result = await runner.run(
        "her_search_designations",
        lat=51.508,
        lon=-0.076,
        radius_m=1000,
        max_results=15,
    )
    if "error" not in result:
        print(f"  Found: {result['count']}")
        for d in result.get("designations", []):
            dtype = f" [{d['designation_type']}]" if d.get("designation_type") else ""
            print(f"  {d['record_id']}: {d['name']}{dtype}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 6: Get details for a specific monument --------------------
    section("6. Monument Detail")

    if "error" not in result and result.get("designations"):
        first_id = result["designations"][0].get("nhle_id")
        if first_id:
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
            print("  No NHLE ID available for detail lookup")
    else:
        print("  No designations found for detail lookup")

    # ----- 7: Text output mode ----------------------------------------
    section("7. Text Output Mode")

    text = await runner.run_text(
        "her_search_monuments",
        name="castle",
        max_results=5,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
