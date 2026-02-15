#!/usr/bin/env python3
"""
Heritage at Risk Demo -- chuk-mcp-her

Demonstrates the Heritage at Risk tools for searching
Historic England's annual register of heritage assets at risk
of loss through neglect, decay, or inappropriate development.

Demonstrates:
    her_count_heritage_at_risk
    her_search_heritage_at_risk
    her_get_heritage_at_risk

NOTE: This demo makes live API calls to the Historic England
Heritage at Risk Register ArcGIS Feature Service.

Usage:
    python examples/heritage_at_risk_demo.py
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
    print("chuk-mcp-her -- Heritage at Risk Demo")
    print("=" * 60)

    # Greater London area (BNG)
    bbox = "520000,170000,540000,190000"

    # ----- 1: Count all at-risk assets in the area -----
    section("1. Count Heritage at Risk: London Area")

    result = await runner.run("her_count_heritage_at_risk", bbox=bbox)
    if "error" not in result:
        print(f"  {result['message']}")
        print(f"  At-risk entries in study area: {result['count']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 2: Count by heritage category -----
    section("2. Count At-Risk Listed Buildings")

    result = await runner.run(
        "her_count_heritage_at_risk",
        bbox=bbox,
        heritage_category="Listed Building",
    )
    if "error" not in result:
        print(f"  At-risk listed buildings: {result['count']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Search for at-risk entries -----
    section("3. Search Heritage at Risk (first 10)")

    result = await runner.run(
        "her_search_heritage_at_risk",
        bbox=bbox,
        max_results=10,
    )
    first_record_id = None
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for e in result.get("entries", []):
            cat = f" [{e.get('heritage_category')}]" if e.get("heritage_category") else ""
            print(f"  {e.get('record_id', '?')}: {e.get('name')}{cat}")
            if first_record_id is None and e.get("record_id"):
                first_record_id = e["record_id"]
    else:
        print(f"  Error: {result['error']}")

    # ----- 4: Search by name -----
    section("4. Search for 'church' At-Risk Entries")

    result = await runner.run(
        "her_search_heritage_at_risk",
        query="church",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for e in result.get("entries", []):
            risk = f" ({e['risk_methodology']})" if e.get("risk_methodology") else ""
            print(f"  {e.get('record_id', '?')}: {e.get('name')}{risk}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 5: Search near a point -----
    section("5. Heritage at Risk near Tower of London (2km)")

    result = await runner.run(
        "her_search_heritage_at_risk",
        lat=51.5081,
        lon=-0.0759,
        radius_m=2000,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for e in result.get("entries", []):
            loc = ""
            if e.get("lat"):
                loc = f" [{e['lat']:.4f}, {e['lon']:.4f}]"
            print(f"  {e.get('record_id', '?')}: {e.get('name')}{loc}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 6: Get detail for a specific entry -----
    section("6. Heritage at Risk Detail")

    if first_record_id:
        result = await runner.run(
            "her_get_heritage_at_risk",
            record_id=first_record_id,
        )
        if "error" not in result:
            m = result.get("monument", {})
            print(f"  Record ID: {m.get('record_id')}")
            print(f"  Name: {m.get('name')}")
            print(f"  Heritage Category: {m.get('heritage_category')}")
            print(f"  Risk Methodology: {m.get('risk_methodology')}")
            if m.get("lat"):
                print(f"  Location: {m['lat']:.4f}, {m['lon']:.4f}")
            if m.get("url"):
                print(f"  URL: {m['url']}")
        else:
            print(f"  Error: {result['error']}")
    else:
        print("  No entries found for detail lookup")

    # ----- 7: Text output mode -----
    section("7. Text Output Mode")

    text = await runner.run_text(
        "her_search_heritage_at_risk",
        heritage_category="Scheduled Monument",
        max_results=5,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
