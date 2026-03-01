#!/usr/bin/env python3
"""
Scotland NRHE Search Demo -- chuk-mcp-her

Demonstrates the Scotland (Historic Environment Scotland) tools for
searching 320,000+ NRHE records from the Canmore database: castles,
brochs, cairns, standing stones, churches, and industrial heritage.

Demonstrates:
    her_search_scotland
    her_get_scotland_record

NOTE: This demo makes live API calls to the Historic Environment
Scotland Canmore Points ArcGIS MapServer at inspire.hes.scot.

Usage:
    python examples/scotland_search_demo.py
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
    print("chuk-mcp-her -- Scotland NRHE Search Demo")
    print("=" * 60)

    # Edinburgh / Lothian study area (BNG)
    bbox = "320000,670000,340000,690000"

    # ----- 1: Search by name -----
    section("1. Search for 'castle' in NRHE")

    result = await runner.run(
        "her_search_scotland",
        name="castle",
        max_results=10,
    )
    first_record_id = None
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for r in result.get("records", []):
            site_type = f" [{r.get('site_type')}]" if r.get("site_type") else ""
            loc = ""
            if r.get("lat"):
                loc = f" ({r['lat']:.4f}, {r['lon']:.4f})"
            print(f"  {r.get('record_id', '?')}: {r.get('name')}{site_type}{loc}")
            if first_record_id is None and r.get("record_id"):
                first_record_id = r["record_id"]
    else:
        print(f"  Error: {result['error']}")

    # ----- 2: Search by site type -----
    section("2. Search for Brochs")

    result = await runner.run(
        "her_search_scotland",
        site_type="BROCH",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for r in result.get("records", []):
            council = f" [{r.get('council')}]" if r.get("council") else ""
            print(f"  {r.get('record_id', '?')}: {r.get('name')}{council}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Search by broad class -----
    section("3. Search by Broad Class: RELIGIOUS")

    result = await runner.run(
        "her_search_scotland",
        broad_class="RELIGIOUS",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for r in result.get("records", []):
            site_type = f" [{r.get('site_type')}]" if r.get("site_type") else ""
            print(f"  {r.get('record_id', '?')}: {r.get('name')}{site_type}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 4: Search by council area -----
    section("4. Search by Council: Highland")

    result = await runner.run(
        "her_search_scotland",
        council="Highland",
        site_type="CAIRN",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for r in result.get("records", []):
            parish = f" [{r.get('parish')}]" if r.get("parish") else ""
            print(f"  {r.get('record_id', '?')}: {r.get('name')}{parish}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 5: Spatial search -- Edinburgh area -----
    section("5. NRHE Records in Edinburgh Area (BNG bbox)")

    result = await runner.run(
        "her_search_scotland",
        bbox=bbox,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for r in result.get("records", []):
            site_type = f" [{r.get('site_type')}]" if r.get("site_type") else ""
            print(f"  {r.get('record_id', '?')}: {r.get('name')}{site_type}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 6: Radius search near Stirling Castle -----
    section("6. NRHE Records near Stirling Castle (2km)")

    result = await runner.run(
        "her_search_scotland",
        lat=56.1238,
        lon=-3.9468,
        radius_m=2000,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (has_more: {result.get('has_more')})")
        for r in result.get("records", []):
            site_type = f" [{r.get('site_type')}]" if r.get("site_type") else ""
            form = f" ({r.get('form')})" if r.get("form") else ""
            print(f"  {r.get('record_id', '?')}: {r.get('name')}{site_type}{form}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 7: Get detail for a specific record -----
    section("7. Record Detail")

    if first_record_id:
        result = await runner.run(
            "her_get_scotland_record",
            record_id=first_record_id,
        )
        if "error" not in result:
            m = result.get("monument", {})
            print(f"  Record ID: {m.get('record_id')}")
            print(f"  Canmore ID: {m.get('canmore_id')}")
            print(f"  Name: {m.get('name')}")
            print(f"  Alt Name: {m.get('alt_name')}")
            print(f"  Site Type: {m.get('site_type')}")
            print(f"  Broad Class: {m.get('broad_class')}")
            print(f"  Form: {m.get('form')}")
            print(f"  County: {m.get('county')}")
            print(f"  Council: {m.get('council')}")
            print(f"  Parish: {m.get('parish')}")
            print(f"  Grid Ref: {m.get('grid_reference')}")
            if m.get("lat"):
                print(f"  Location: {m['lat']:.4f}, {m['lon']:.4f}")
            if m.get("easting"):
                print(f"  BNG: E={m['easting']:.0f}, N={m['northing']:.0f}")
            if m.get("url"):
                print(f"  URL: {m['url']}")
        else:
            print(f"  Error: {result['error']}")
    else:
        print("  No records found for detail lookup")

    # ----- 8: Text output mode -----
    section("8. Text Output Mode")

    text = await runner.run_text(
        "her_search_scotland",
        name="stone circle",
        max_results=5,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
