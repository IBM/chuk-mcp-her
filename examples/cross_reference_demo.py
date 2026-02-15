#!/usr/bin/env python3
"""
Cross-Reference Demo -- chuk-mcp-her

Demonstrates classifying candidate locations (e.g. from LiDAR
anomaly detection) against known heritage assets. Candidates are
classified as "match" (within 50m of a known asset), "near"
(within 200m), or "novel" (no nearby match).

Shows three modes:
  1. NHLE-only cross-reference (baseline)
  2. NHLE + AIM aerial features (include_aim=True)
  3. Text output mode

Enriched match output includes source, grade, monument_type,
period, form, and evidence fields where available.

Demonstrates:
    her_cross_reference (with include_aim parameter)
    her_count_features (for context)

NOTE: This demo makes live API calls to the Historic England
ArcGIS Feature Service.

Usage:
    python examples/cross_reference_demo.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from tool_runner import ToolRunner


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}\n")


def narrative(text: str) -> None:
    """Print scenario narrative."""
    for line in text.strip().split("\n"):
        print(f"  {line.strip()}")
    print()


async def main() -> None:
    runner = ToolRunner()

    print("=" * 60)
    print("  chuk-mcp-her -- Cross-Reference Demo")
    print("  Classifying LiDAR anomalies against heritage records")
    print("=" * 60)

    narrative("""
        Imagine a LiDAR survey of the Blackwater Estuary in Essex
        has detected several anomalies. We want to classify each
        candidate location against the NHLE to determine which are
        known heritage assets, which are near known assets, and
        which are potentially novel discoveries.
    """)

    # ----- 1: Count features in the study area -----------------------
    section("1. Heritage Density in Study Area")

    narrative("""
        First, assess how dense the heritage record is in this area.
        This helps set expectations for the cross-reference results.
    """)

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

    # ----- 2: Cross-reference candidates ------------------------------
    section("2. Cross-Reference LiDAR Anomalies")

    narrative("""
        Submit 5 candidate locations from a hypothetical LiDAR survey.
        Some are near known red hills (saltern mounds), others are
        in open marshland with no known heritage assets.
    """)

    candidates = [
        {"easting": 590625, "northing": 208193},  # Near known red hill
        {"easting": 591000, "northing": 208500},  # Slightly further
        {"easting": 595000, "northing": 210000},  # Open marsh
        {"easting": 588000, "northing": 206000},  # Near coastline
        {"easting": 600000, "northing": 212000},  # Remote area
    ]

    result = await runner.run(
        "her_cross_reference",
        candidates=json.dumps(candidates),
        match_radius_m=50,
        near_radius_m=200,
    )
    if "error" not in result:
        print(f"  Candidates submitted: {result['candidates_submitted']}")
        print("  Classification:")
        cls = result.get("classification", {})
        print(f"    Match (within 50m):  {cls.get('match', 0)}")
        print(f"    Near (within 200m):  {cls.get('near', 0)}")
        print(f"    Novel (no match):    {cls.get('novel', 0)}")

        if result.get("matches"):
            print("\n  Matches:")
            for m in result["matches"]:
                c = m.get("candidate", {})
                asset = m.get("matched_asset", {})
                dist = m.get("distance_m", "?")
                print(f"    E={c.get('easting')}, N={c.get('northing')}")
                src = asset.get("source", "?")
                grade = asset.get("grade", "")
                mtype = asset.get("monument_type", "")
                extra = f" [grade={grade}]" if grade else ""
                extra += f" [type={mtype}]" if mtype else ""
                print(f"      -> {asset.get('name', '?')} ({dist}m) src={src}{extra}")

        if result.get("near_misses"):
            print("\n  Near misses:")
            for m in result["near_misses"]:
                c = m.get("candidate", {})
                asset = m.get("nearest_asset", {})
                dist = m.get("distance_m", "?")
                print(f"    E={c.get('easting')}, N={c.get('northing')}")
                print(f"      -> nearest: {asset.get('name', '?')} ({dist}m)")

        print(f"\n  Novel candidates: {result.get('novel_count', 0)}")
        if result.get("novel_summary"):
            print(f"  {result['novel_summary']}")
    else:
        print(f"  Error: {result['error']}")

    # ----- 3: Cross-reference with AIM aerial features -----------------
    section("3. Cross-Reference with AIM Aerial Features")

    narrative("""
        Phase 1.3 adds AIM (Aerial Investigation and Mapping) data
        to the cross-reference. With include_aim=True, aerial
        archaeology features — cropmarks, earthworks, and enclosures
        detected from aerial photographs and LiDAR — are merged
        into the known-site pool.
    """)

    result_aim = await runner.run(
        "her_cross_reference",
        candidates=json.dumps(candidates),
        match_radius_m=50,
        near_radius_m=200,
        include_aim=True,
    )
    if "error" not in result_aim:
        cls_aim = result_aim.get("classification", {})
        print(f"  Candidates: {result_aim['candidates_submitted']}")
        print(f"  Match (within 50m):  {cls_aim.get('match', 0)}")
        print(f"  Near (within 200m):  {cls_aim.get('near', 0)}")
        print(f"  Novel (no match):    {cls_aim.get('novel', 0)}")

        for m in result_aim.get("matches", []):
            asset = m.get("matched_asset", {})
            dist = m.get("distance_m", "?")
            src = asset.get("source", "?")
            mtype = asset.get("monument_type", "")
            period = asset.get("period", "")
            print(f"    -> {asset.get('name', '?')} ({dist}m) src={src}")
            if mtype or period:
                print(f"       type={mtype}, period={period}")

        # Compare with NHLE-only
        cls_nhle = result.get("classification", {}) if "error" not in result else {}
        if cls_nhle:
            print("\n  Comparison:")
            print(
                f"    NHLE only:     {cls_nhle.get('match', 0)} match, "
                f"{cls_nhle.get('near', 0)} near, "
                f"{cls_nhle.get('novel', 0)} novel"
            )
            print(
                f"    NHLE+AIM:      {cls_aim.get('match', 0)} match, "
                f"{cls_aim.get('near', 0)} near, "
                f"{cls_aim.get('novel', 0)} novel"
            )
    else:
        print(f"  Error: {result_aim['error']}")

    # ----- 4: Text output mode ----------------------------------------
    section("4. Text Output Mode")

    text = await runner.run_text(
        "her_cross_reference",
        candidates=json.dumps(candidates[:3]),
    )
    print(text)

    # ----- Summary ----------------------------------------------------
    section("Summary")

    narrative("""
        The cross-reference workflow enables systematic classification
        of LiDAR-detected anomalies against the heritage record:

        1. Count features — assess heritage density in the study area
        2. Submit candidates — classify each anomaly location
        3. Review results — match, near, or novel

        Novel candidates are the most interesting — they represent
        potential new discoveries not yet in the national record.

        An LLM agent would continue by:
        - Exporting known sites for QGIS overlay (her_export_for_lidar)
        - Getting details on matched assets (her_get_monument)
        - Searching for similar monument types nearby (her_search_designations)
    """)

    print("=" * 60)
    print("  Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
