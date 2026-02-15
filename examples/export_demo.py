#!/usr/bin/env python3
"""
Export Demo -- chuk-mcp-her

Export heritage assets as GeoJSON FeatureCollection and in the
LiDAR cross-reference format. Shows filtering by designation type,
bounding box, and the full GeoJSON structure.

Demonstrates:
    her_export_geojson (multiple filter combinations)
    her_export_for_lidar

NOTE: This demo makes live API calls to the Historic England
ArcGIS Feature Service.

Usage:
    python examples/export_demo.py
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


async def main() -> None:
    runner = ToolRunner()

    print("=" * 60)
    print("chuk-mcp-her -- Export Demo")
    print("=" * 60)

    # ----- Export 1: Scheduled monuments as GeoJSON -------------------
    section("1. GeoJSON Export: Blackwater Estuary Scheduled Monuments")

    result = await runner.run(
        "her_export_geojson",
        bbox="586000,205000,602500,215000",
        designation_type="scheduled_monument",
        max_results=50,
    )
    if "error" not in result:
        fc = result.get("geojson", {})
        features = fc.get("features", [])
        print(f"  Exported: {result['feature_count']} features")
        print(f"  GeoJSON type: {fc.get('type')}")

        # Show first 3 features
        for feat in features[:3]:
            props = feat.get("properties", {})
            geom = feat.get("geometry")
            coords = geom.get("coordinates", []) if geom else []
            print(f"  {props.get('record_id')}: {props.get('name')}")
            if coords:
                print(f"    Coordinates: {coords[0]:.4f}, {coords[1]:.4f}")
        if len(features) > 3:
            print(f"  ... and {len(features) - 3} more")
    else:
        print(f"  Error: {result['error']}")

    # ----- Export 2: All types in an area -----------------------------
    section("2. GeoJSON Export: All Types near Tower of London")

    result = await runner.run(
        "her_export_geojson",
        bbox="532000,179000,535000,182000",
        max_results=20,
    )
    if "error" not in result:
        fc = result.get("geojson", {})
        features = fc.get("features", [])
        print(f"  Exported: {result['feature_count']} features")

        # Count by designation type
        types: dict[str, int] = {}
        for feat in features:
            dt = feat.get("properties", {}).get("designation_type", "unknown")
            types[dt] = types.get(dt, 0) + 1
        for dt, count in sorted(types.items()):
            print(f"    {dt}: {count}")
    else:
        print(f"  Error: {result['error']}")

    # ----- Export 3: GeoJSON property structure ------------------------
    section("3. GeoJSON Feature Structure")

    if "error" not in result and result.get("geojson", {}).get("features"):
        feat = result["geojson"]["features"][0]
        print(f"  Feature type: {feat['type']}")
        geom = feat.get("geometry")
        print(f"  Geometry type: {geom.get('type') if geom else 'None'}")
        print(f"  Property keys: {sorted(feat.get('properties', {}).keys())}")

    # ----- Export 4: LiDAR export format ------------------------------
    section("4. LiDAR Export: Blackwater Estuary")

    result = await runner.run(
        "her_export_for_lidar",
        bbox="586000,205000,602500,215000",
    )
    if "error" not in result:
        print(f"  Known sites: {result['count']}")
        print(f"  BBox: {result['bbox']}")

        # Count by source
        sources: dict[str, int] = {}
        for site in result.get("known_sites", []):
            src = site.get("source", "unknown")
            sources[src] = sources.get(src, 0) + 1
        for src, count in sorted(sources.items()):
            print(f"    {src}: {count} sites")

        # Show enriched fields per site
        for site in result.get("known_sites", [])[:5]:
            src = site.get("source", "?")
            grade = site.get("grade", "")
            mtype = site.get("monument_type", "")
            period = site.get("period", "")
            form = site.get("form", "")
            print(f"  [{src}] {site.get('id')}: {site.get('name')} [{site.get('type')}]")
            print(f"    E={site.get('easting')}, N={site.get('northing')}")
            extra = []
            if grade:
                extra.append(f"grade={grade}")
            if mtype:
                extra.append(f"type={mtype}")
            if period:
                extra.append(f"period={period}")
            if form:
                extra.append(f"form={form}")
            if extra:
                print(f"    {', '.join(extra)}")

        if result["count"] > 5:
            print(f"  ... and {result['count'] - 5} more")
    else:
        print(f"  Error: {result['error']}")

    # ----- Export 5: Text output mode ---------------------------------
    section("5. Text Output Mode (GeoJSON)")

    text = await runner.run_text(
        "her_export_geojson",
        bbox="586000,205000,602500,215000",
        designation_type="scheduled_monument",
        max_results=10,
    )
    print(text)

    # ----- Export 6: Full GeoJSON output (first 3 features) -----------
    section("6. Raw GeoJSON (first 3 features)")

    result = await runner.run(
        "her_export_geojson",
        bbox="586000,205000,602500,215000",
        designation_type="scheduled_monument",
        max_results=3,
    )
    if "error" not in result:
        print(json.dumps(result["geojson"], indent=2))

    print("\n" + "=" * 60)
    print("Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
