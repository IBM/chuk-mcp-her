#!/usr/bin/env python3
"""
Scotland Designations Demo -- chuk-mcp-her

Demonstrates the Scotland designation tools for searching HES
(Historic Environment Scotland) designated heritage assets:
listed buildings, scheduled monuments, gardens and designed landscapes,
battlefields, world heritage sites, conservation areas, and historic
marine protected areas.

Demonstrates:
    her_search_scotland_designations
    her_search_scotland (for comparison with NRHE)

NOTE: This demo makes live API calls to the Historic Environment
Scotland HES Designations ArcGIS MapServer at inspire.hes.scot.

Usage:
    python examples/scotland_designations_demo.py
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
    print("chuk-mcp-her -- Scotland Designations Demo")
    print("=" * 60)

    # ----- 1: Search all designation types -----
    section("1. All Designation Types (first 10)")

    result = await runner.run(
        "her_search_scotland_designations",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for d in result.get("designations", []):
            cat = f" ({d.get('category')})" if d.get("category") else ""
            print(
                f"  {d.get('record_id', '?')}: {d.get('name')} [{d.get('designation_type')}]{cat}"
            )
    else:
        print(f"  Error: {result['error']}")

    # ----- 2: Scottish listed buildings -----
    section("2. Scottish Listed Buildings")

    result = await runner.run(
        "her_search_scotland_designations",
        designation_type="listed_building",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for d in result.get("designations", []):
            cat = f" (Category {d.get('category')})" if d.get("category") else ""
            auth = f" [{d.get('local_authority')}]" if d.get("local_authority") else ""
            print(f"  {d.get('designation_reference', '?')}: {d.get('name')}{cat}{auth}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Scottish scheduled monuments -----
    section("3. Scottish Scheduled Monuments")

    result = await runner.run(
        "her_search_scotland_designations",
        designation_type="scheduled_monument",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for d in result.get("designations", []):
            loc = ""
            if d.get("lat"):
                loc = f" ({d['lat']:.4f}, {d['lon']:.4f})"
            print(f"  {d.get('designation_reference', '?')}: {d.get('name')}{loc}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 4: Battlefields -----
    section("4. Scottish Battlefields")

    result = await runner.run(
        "her_search_scotland_designations",
        designation_type="battlefield",
        max_results=20,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for d in result.get("designations", []):
            date = f" (designated {d.get('designated_date')})" if d.get("designated_date") else ""
            print(f"  {d.get('designation_reference', '?')}: {d.get('name')}{date}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 5: Gardens and Designed Landscapes -----
    section("5. Gardens and Designed Landscapes")

    result = await runner.run(
        "her_search_scotland_designations",
        designation_type="garden_designed_landscape",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for d in result.get("designations", []):
            auth = f" [{d.get('local_authority')}]" if d.get("local_authority") else ""
            print(f"  {d.get('designation_reference', '?')}: {d.get('name')}{auth}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 6: Search by name -----
    section("6. Search Designations by Name: 'Edinburgh'")

    result = await runner.run(
        "her_search_scotland_designations",
        name="Edinburgh",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for d in result.get("designations", []):
            cat = f" ({d.get('category')})" if d.get("category") else ""
            print(
                f"  {d.get('designation_reference', '?')}: {d.get('name')} "
                f"[{d.get('designation_type')}]{cat}"
            )
    else:
        print(f"  Error: {result['error']}")

    # ----- 7: Spatial search near Stirling -----
    section("7. Designations near Stirling (5km)")

    result = await runner.run(
        "her_search_scotland_designations",
        lat=56.1238,
        lon=-3.9468,
        radius_m=5000,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for d in result.get("designations", []):
            cat = f" ({d.get('category')})" if d.get("category") else ""
            print(
                f"  {d.get('designation_reference', '?')}: {d.get('name')} "
                f"[{d.get('designation_type')}]{cat}"
            )
    else:
        print(f"  Error: {result['error']}")

    # ----- 8: Multi-source comparison -----
    section("8. Multi-Source: NRHE vs Designations near Callanish")

    print("  Searching NRHE (all known sites)...")
    nrhe_result = await runner.run(
        "her_search_scotland",
        lat=58.1977,
        lon=-6.7456,
        radius_m=2000,
        max_results=10,
    )
    if "error" not in nrhe_result:
        print(f"  NRHE records: {nrhe_result['count']}")
        for r in nrhe_result.get("records", []):
            site_type = f" [{r.get('site_type')}]" if r.get("site_type") else ""
            print(f"    {r.get('record_id', '?')}: {r.get('name')}{site_type}")
    else:
        print(f"  NRHE error: {nrhe_result['error']}")

    print()
    print("  Searching Designations (designated assets only)...")
    des_result = await runner.run(
        "her_search_scotland_designations",
        lat=58.1977,
        lon=-6.7456,
        radius_m=2000,
        max_results=10,
    )
    if "error" not in des_result:
        print(f"  Designated assets: {des_result['count']}")
        for d in des_result.get("designations", []):
            cat = f" ({d.get('category')})" if d.get("category") else ""
            print(
                f"    {d.get('designation_reference', '?')}: {d.get('name')} "
                f"[{d.get('designation_type')}]{cat}"
            )
    else:
        print(f"  Designations error: {des_result['error']}")

    # ----- 9: Text output mode -----
    section("9. Text Output Mode")

    text = await runner.run_text(
        "her_search_scotland_designations",
        designation_type="world_heritage_site",
        max_results=10,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
