#!/usr/bin/env python3
"""
Scenario: Blackwater Estuary Heritage Investigation

The Blackwater Estuary in Essex is one of the richest archaeological
landscapes in England. The intertidal zone contains hundreds of red
hills (Iron Age/Roman salt-making sites), medieval fish traps, and
WWII defensive structures -- many only visible via LiDAR and aerial
photography.

This scenario demonstrates a complete heritage investigation workflow
using all 5 data sources:

  1. Assess heritage density across the estuary (NHLE)
  2. Search for scheduled monuments — salt-making mounds (NHLE)
  3. Search for listed buildings near the coast (NHLE)
  4. Find all heritage assets near a specific point (NHLE)
  5. Export known sites for LiDAR cross-referencing (NHLE)
  5b. Search AIM aerial mapping features (AIM)
  6. Conservation areas in the study area (Conservation Areas)
  7. Heritage at risk in the study area (Heritage at Risk)
  8. Cross-reference hypothetical LiDAR anomalies (NHLE)
  9. Export findings as GeoJSON for GIS visualisation (NHLE)

NOTE: Makes live API calls to the Historic England ArcGIS
Feature Service.

Usage:
    python examples/blackwater_estuary_scenario.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from tool_runner import ToolRunner


# Blackwater Estuary study area (BNG)
BBOX = "586000,205000,602500,215000"

# Bradwell-on-Sea (centre of study area)
BRADWELL_LAT = 51.7309
BRADWELL_LON = 0.8897


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
    print("  Blackwater Estuary Heritage Investigation")
    print("  Study area: 586000,205000 to 602500,215000 (BNG)")
    print("=" * 60)

    narrative("""
        The Blackwater Estuary stretches from Maldon to the open
        sea at Bradwell-on-Sea. Its mudflats and saltmarshes are
        dotted with red hills -- mounds of burnt clay from Iron Age
        and Roman salt production. Many are scheduled monuments.

        This scenario simulates a systematic heritage investigation
        combining database queries with LiDAR cross-referencing.
    """)

    # ------------------------------------------------------------------
    # 1. Heritage density assessment
    # ------------------------------------------------------------------
    section("1. Heritage Density Assessment")

    narrative("""
        Before starting fieldwork, assess how many heritage assets
        are already recorded in the study area. This sets the
        baseline for evaluating LiDAR anomalies later.
    """)

    counts = await runner.run("her_count_features", bbox=BBOX)
    if "error" not in counts:
        print(f"  {counts['message']}")
        total = 0
        for dtype, count in counts.get("counts", {}).items():
            print(f"    {dtype}: {count}")
            if dtype != "total":
                total += count
        print(f"\n  Total heritage assets in study area: {counts['counts'].get('total', total)}")
    else:
        print(f"  Error: {counts['error']}")
        print("  (This demo requires network access to Historic England)")

    # ------------------------------------------------------------------
    # 2. Scheduled monuments — red hills / salt-making mounds
    # ------------------------------------------------------------------
    section("2. Scheduled Monuments: Salt-Making Mounds")

    narrative("""
        Red hills are the signature monuments of the Essex coast —
        mounds of burnt clay from Iron Age and Roman salt production.
        The NHLE records them as 'mound' rather than 'red hill';
        the local name appears in HER records (Heritage Gateway).
        Search for scheduled monuments containing 'mound' in
        the study area to find the salt-making sites.
    """)

    result = await runner.run(
        "her_search_monuments",
        name="mound",
        bbox=BBOX,
        max_results=20,
    )
    red_hill_count = 0
    if "error" not in result:
        red_hill_count = result["count"]
        print(f"  Found: {result['count']} mound monuments (potential red hills)")
        print(f"  Total available: {result.get('total_available', '?')}")
        for m in result.get("monuments", [])[:10]:
            loc = ""
            if m.get("lat"):
                loc = f" ({m['lat']:.4f}, {m['lon']:.4f})"
            print(f"    {m['record_id']}: {m['name']}{loc}")
        if result["count"] > 10:
            print(f"    ... and {result['count'] - 10} more")
        print()
        print("  Note: 'Red hill' is a local Essex name for these mounds.")
        print("  Use her_search_heritage_gateway for HER records that")
        print("  use the 'red hill' designation directly.")
    else:
        print(f"  Error: {result['error']}")

    # ------------------------------------------------------------------
    # 3. Listed buildings near the coast
    # ------------------------------------------------------------------
    section("3. Listed Buildings near Bradwell-on-Sea")

    narrative("""
        Bradwell-on-Sea is home to the Chapel of St Peter-on-the-Wall,
        one of the oldest largely intact churches in England (654 AD).
        What other listed buildings are nearby?
    """)

    result = await runner.run(
        "her_search_listed_buildings",
        lat=BRADWELL_LAT,
        lon=BRADWELL_LON,
        radius_m=2000,
        max_results=10,
    )
    if "error" not in result:
        print(f"  Found: {result['count']} listed buildings within 2km")
        for m in result.get("monuments", []):
            grade = f" (Grade {m['grade']})" if m.get("grade") else ""
            print(f"  {m['record_id']}: {m['name']}{grade}")
    else:
        print(f"  Error: {result['error']}")

    # ------------------------------------------------------------------
    # 4. Nearby heritage assets
    # ------------------------------------------------------------------
    section("4. All Heritage Assets near Bradwell (1km)")

    narrative("""
        Search across all designation types to get the full
        picture of the heritage landscape around Bradwell.
    """)

    result = await runner.run(
        "her_nearby",
        lat=BRADWELL_LAT,
        lon=BRADWELL_LON,
        radius_m=1000,
        max_results=15,
    )
    if "error" not in result:
        print(f"  Centre: {result['centre_lat']:.4f}, {result['centre_lon']:.4f}")
        print(f"  Radius: {result['radius_m']}m")
        print(f"  Found: {result['count']} assets")
        print()
        for asset in result.get("assets", []):
            dist = f" ({asset['distance_m']:.0f}m)" if asset.get("distance_m") is not None else ""
            dtype = f" [{asset['designation_type']}]" if asset.get("designation_type") else ""
            print(f"  {asset['record_id']}: {asset['name']}{dtype}{dist}")
    else:
        print(f"  Error: {result['error']}")

    # ------------------------------------------------------------------
    # 5. Export for LiDAR cross-referencing
    # ------------------------------------------------------------------
    section("5. Export Known Sites for LiDAR")

    narrative("""
        Before flying a LiDAR survey, export all known heritage sites
        in BNG coordinates. This becomes the baseline for classifying
        anomalies detected in the LiDAR data.
    """)

    result = await runner.run("her_export_for_lidar", bbox=BBOX)
    if "error" not in result:
        print(f"  Known sites exported: {result['count']}")
        print(f"  BBox: {result['bbox']}")

        # Count by type
        types: dict[str, int] = {}
        for site in result.get("known_sites", []):
            t = site.get("type", "unknown")
            types[t] = types.get(t, 0) + 1
        print("  By designation type:")
        for t, c in sorted(types.items()):
            print(f"    {t}: {c}")
    else:
        print(f"  Error: {result['error']}")

    # ------------------------------------------------------------------
    # 5b. Aerial Investigation & Mapping features
    # ------------------------------------------------------------------
    section("5b. AIM: Aerial Archaeology Features")

    narrative("""
        Historic England's AIM dataset contains 470,000+ features
        identified from aerial photographs and LiDAR — cropmarks,
        earthworks, enclosures, saltern mounds. These are NOT in the
        NHLE and represent a separate layer of archaeological knowledge.
    """)

    aim_count = await runner.run("her_count_aerial", bbox=BBOX)
    if "error" not in aim_count:
        print(f"  Total AIM features in study area: {aim_count['count']}")
    else:
        print(f"  Error: {aim_count['error']}")

    aim_result = await runner.run(
        "her_search_aerial",
        bbox=BBOX,
        monument_type="MOUND",
        max_results=10,
    )
    if "error" not in aim_result:
        print(f"  Mound features: {aim_result.get('total_available', aim_result['count'])}")
        for f in aim_result.get("features", [])[:5]:
            loc = ""
            if f.get("lat"):
                loc = f" [{f['lat']:.4f}, {f['lon']:.4f}]"
            print(f"  {f.get('aim_id', '?')}: {f.get('monument_type')} ({f.get('period')}){loc}")
        if aim_result["count"] > 5:
            print(f"  ... and {aim_result['count'] - 5} more")
    else:
        print(f"  Error: {aim_result['error']}")

    # ------------------------------------------------------------------
    # 6. Conservation areas
    # ------------------------------------------------------------------
    section("6. Conservation Areas in Study Area")

    narrative("""
        Conservation areas protect the character of historic places.
        Fieldwork in a conservation area may need additional consents.
        Check what's designated before planning a survey.
    """)

    ca_count = await runner.run("her_count_conservation_areas", bbox=BBOX)
    if "error" not in ca_count:
        print(f"  Conservation areas in study area: {ca_count['count']}")
    else:
        print(f"  Error: {ca_count['error']}")

    ca_result = await runner.run(
        "her_search_conservation_areas",
        bbox=BBOX,
        max_results=10,
    )
    if "error" not in ca_result:
        for a in ca_result.get("areas", [])[:5]:
            lpa = f" [{a.get('lpa')}]" if a.get("lpa") else ""
            print(f"  {a.get('record_id', '?')}: {a.get('name')}{lpa}")
        if ca_result["count"] > 5:
            print(f"  ... and {ca_result['count'] - 5} more")
    else:
        print(f"  Error: {ca_result['error']}")

    # ------------------------------------------------------------------
    # 7. Heritage at risk
    # ------------------------------------------------------------------
    section("7. Heritage at Risk in Study Area")

    narrative("""
        Heritage at risk assets are particularly vulnerable.
        Identifying them early helps prioritise field investigation
        and ensures any discoveries are recorded before loss.
    """)

    har_count = await runner.run("her_count_heritage_at_risk", bbox=BBOX)
    if "error" not in har_count:
        print(f"  At-risk entries in study area: {har_count['count']}")
    else:
        print(f"  Error: {har_count['error']}")

    har_result = await runner.run(
        "her_search_heritage_at_risk",
        bbox=BBOX,
        max_results=10,
    )
    if "error" not in har_result:
        for e in har_result.get("entries", [])[:5]:
            cat = f" [{e.get('heritage_category')}]" if e.get("heritage_category") else ""
            print(f"  {e.get('record_id', '?')}: {e.get('name')}{cat}")
        if har_result["count"] > 5:
            print(f"  ... and {har_result['count'] - 5} more")
    else:
        print(f"  Error: {har_result['error']}")

    # ------------------------------------------------------------------
    # 8. Cross-reference LiDAR anomalies
    # ------------------------------------------------------------------
    section("8. Cross-Reference LiDAR Anomalies")

    narrative("""
        A hypothetical LiDAR survey has detected 6 circular mound
        anomalies in the study area. Cross-reference each against
        the NHLE to classify them as match (known site), near
        (within 200m of known site), or novel (potential discovery).

        Candidate 1 is placed ~30m from Mound E of Basin Road
        (nhle:1002172) at Heybridge Basin. Candidate 2 is ~150m
        from the same mound. Candidates 3-6 are in open marshland
        with no known heritage assets nearby.
    """)

    # nhle:1002172 (Mound E of Basin Road) is at BNG ~587165, 207514
    candidates = [
        {"easting": 587180, "northing": 207540},  # ~30m from Mound E of Basin Road
        {"easting": 587300, "northing": 207400},  # ~150m from Mound E of Basin Road
        {"easting": 595000, "northing": 210000},  # Open saltmarsh
        {"easting": 588500, "northing": 206500},  # Near coast
        {"easting": 597000, "northing": 211500},  # Mid-estuary
        {"easting": 600000, "northing": 212000},  # Remote area
    ]

    result = await runner.run(
        "her_cross_reference",
        candidates=json.dumps(candidates),
        match_radius_m=50,
        near_radius_m=200,
    )
    if "error" not in result:
        cls = result.get("classification", {})
        print(f"  Candidates: {result['candidates_submitted']}")
        print(f"  Match (within 50m):  {cls.get('match', 0)}")
        print(f"  Near (within 200m):  {cls.get('near', 0)}")
        print(f"  Novel (no match):    {cls.get('novel', 0)}")

        # Show matched and near details
        for m in result.get("matches", []):
            cand = m.get("candidate", {})
            asset = m.get("matched_asset", {})
            dist = m.get("distance_m", 0)
            loc = f"E={cand.get('easting')}, N={cand.get('northing')}"
            print(
                f"    [match] {loc} -> {asset.get('record_id')} ({asset.get('name')}, {dist:.0f}m)"
            )
        for m in result.get("near_misses", []):
            cand = m.get("candidate", {})
            asset = m.get("nearest_asset", {})
            dist = m.get("distance_m", 0)
            loc = f"E={cand.get('easting')}, N={cand.get('northing')}"
            print(
                f"    [near ] {loc} -> {asset.get('record_id')} ({asset.get('name')}, {dist:.0f}m)"
            )

        print(f"\n  Novel candidates for field investigation: {result.get('novel_count', 0)}")
    else:
        print(f"  Error: {result['error']}")

    # ------------------------------------------------------------------
    # 9. Export findings as GeoJSON
    # ------------------------------------------------------------------
    section("9. Export Findings as GeoJSON")

    narrative("""
        Export the scheduled monuments in the study area as GeoJSON
        for overlay in QGIS or Leaflet alongside the LiDAR data.
    """)

    result = await runner.run(
        "her_export_geojson",
        bbox=BBOX,
        designation_type="scheduled_monument",
        max_results=100,
    )
    if "error" not in result:
        fc = result.get("geojson", {})
        features = fc.get("features", [])
        print(f"  Exported: {result['feature_count']} features as GeoJSON")
        print(f"  Type: {fc.get('type')}")
        if features:
            print(f"  First feature: {features[0]['properties'].get('name')}")
            geom = features[0].get("geometry")
            if geom and geom.get("coordinates"):
                coords = geom["coordinates"]
                print(f"  Coordinates: [{coords[0]:.4f}, {coords[1]:.4f}]")
    else:
        print(f"  Error: {result['error']}")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    section("Scenario Summary")

    narrative(f"""
        This scenario demonstrated a complete heritage investigation
        workflow for the Blackwater Estuary using all 5 data sources:

        1. Density assessment — counted all heritage assets (NHLE)
        2. Monument search — found {red_hill_count} mound monuments (NHLE)
        3. Listed buildings — historic buildings near Bradwell (NHLE)
        4. Nearby search — full heritage landscape around a point (NHLE)
        5. LiDAR export — baseline data for anomaly classification (NHLE)
        5b. AIM features — aerial archaeology (cropmarks, mounds)
        6. Conservation areas — designated areas in the study zone
        7. Heritage at risk — vulnerable assets for priority recording
        8. Cross-reference — classified 6 LiDAR anomalies (NHLE)
        9. GeoJSON export — map-ready output for GIS overlay (NHLE)

        An LLM agent would continue by:
        - Overlaying GeoJSON with LiDAR imagery in chuk-mcp-lidar
        - Checking tidal conditions for fieldwork (chuk-mcp-tides)
        - Searching Heritage Gateway for undesignated red hills
        - Cross-referencing protected wrecks with maritime archives
    """)

    print("=" * 60)
    print("  Scenario complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
