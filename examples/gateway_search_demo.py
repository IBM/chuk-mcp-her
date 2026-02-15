#!/usr/bin/env python3
"""
Heritage Gateway Demo -- chuk-mcp-her

Demonstrates searching local Historic Environment Records via
the Heritage Gateway web scraper. Finds undesignated sites,
findspots, and HER monument entries not in the NHLE.

Demonstrates:
    her_search_heritage_gateway

NOTE: This demo makes live requests to the Heritage Gateway
website (www.heritagegateway.org.uk). The Gateway uses ASP.NET
WebForms and may be slow or temporarily unavailable. The tool
returns empty results gracefully on failure.

Usage:
    python examples/gateway_search_demo.py
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
    print("chuk-mcp-her -- Heritage Gateway Demo")
    print("=" * 60)
    print()
    print("  The Heritage Gateway provides access to 60+ local")
    print("  Historic Environment Records across England.")
    print("  Results are best-effort — the Gateway may be slow")
    print("  or temporarily unavailable.")

    # ----- 1: Search by keyword (what) -----
    section("1. Search for 'red hill' (what)")

    result = await runner.run(
        "her_search_heritage_gateway",
        what="red hill",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for r in result.get("records", []):
            her = f" [{r.get('source_her')}]" if r.get("source_her") else ""
            print(f"  {r.get('record_id', '?')}: {r.get('name', '?')}{her}")
        if result.get("note"):
            print(f"\n  Note: {result['note']}")
    else:
        print(f"  Error: {result['error']}")
        if result.get("suggestion"):
            print(f"  Suggestion: {result['suggestion']}")

    # ----- 2: Search by keyword and place (what + where) -----
    section("2. Search for 'saltern' in Essex (what + where)")

    result = await runner.run(
        "her_search_heritage_gateway",
        what="saltern",
        where="Essex",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for r in result.get("records", []):
            period = f" ({r.get('period')})" if r.get("period") else ""
            her = f" [{r.get('source_her')}]" if r.get("source_her") else ""
            print(f"  {r.get('name', '?')}{period}{her}")
        if result.get("note"):
            print(f"\n  Note: {result['note']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Search by period (what + when) -----
    section("3. Search for 'barrow' in Roman period (what + when)")

    result = await runner.run(
        "her_search_heritage_gateway",
        what="barrow",
        when="Roman",
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} (total: {result.get('total_available', '?')})")
        for r in result.get("records", []):
            mtype = f" ({r.get('monument_type')})" if r.get("monument_type") else ""
            print(f"  {r.get('name', '?')}{mtype}")
        if result.get("note"):
            print(f"\n  Note: {result['note']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 4: Text output mode -----
    section("4. Text Output Mode")

    text = await runner.run_text(
        "her_search_heritage_gateway",
        what="hillfort",
        max_results=5,
    )
    print(text)

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
