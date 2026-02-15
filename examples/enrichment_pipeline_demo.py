#!/usr/bin/env python3
"""
Enrichment Pipeline Demo -- chuk-mcp-her

Demonstrates the full Gateway enrichment pipeline:

  1. Search Heritage Gateway for local HER records (no coordinates)
  2. Enrich records by fetching detail pages (resolves coordinates)
  3. Feed enriched records into cross-reference alongside NHLE
  4. Compare classification with and without Gateway enrichment

This is the key workflow for improving LiDAR anomaly classification.
Instead of matching against ~14 NHLE scheduled monuments, you match
against ~14 + N Gateway records with resolved coordinates.

Demonstrates:
    her_search_heritage_gateway  (search only — no coordinates)
    her_enrich_gateway           (resolve coordinates from detail pages)
    her_cross_reference          (with and without gateway_sites)
    her_count_features           (heritage density baseline)

NOTE: This demo makes live requests to the Heritage Gateway website
AND the Historic England ArcGIS Feature Service. The enrichment step
fetches individual detail pages at ~1 req/sec, so it may take 30-60
seconds depending on the number of records.

Usage:
    python examples/enrichment_pipeline_demo.py
"""

import asyncio
import json
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
from tool_runner import ToolRunner


# Blackwater Estuary study area (BNG)
BBOX = "586000,205000,602500,215000"


def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}\n")


def narrative(text: str) -> None:
    for line in text.strip().split("\n"):
        print(f"  {line.strip()}")
    print()


async def main() -> None:
    runner = ToolRunner()

    print("=" * 60)
    print("  Gateway Enrichment Pipeline Demo")
    print("  Resolving HER coordinates for cross-referencing")
    print("=" * 60)

    narrative("""
        The Heritage Gateway provides access to local HER records
        that are NOT in the NHLE. Search results include names and
        monument types but NO coordinates. The enrichment pipeline
        fetches detail pages to resolve BNG coordinates via grid
        references, enabling spatial cross-referencing.
    """)

    # ------------------------------------------------------------------
    # 1. Gateway search — shows what we get WITHOUT enrichment
    # ------------------------------------------------------------------
    section("1. Gateway Search (No Coordinates)")

    narrative("""
        Search for 'red hill' records. These are local HER entries
        for Iron Age/Roman salt-making mounds. The search results
        include names and record IDs but no spatial coordinates.
    """)

    search_result = await runner.run(
        "her_search_heritage_gateway",
        what="red hill",
        max_results=10,
    )
    if "error" not in search_result:
        total = search_result.get("total_available", "?")
        print(f"  Found: {search_result['count']} records (total: {total})")
        print()
        for r in search_result.get("records", [])[:5]:
            has_coords = "yes" if r.get("easting") else "no"
            grid = r.get("grid_reference", "-")
            print(f"  {r.get('record_id', '?')}: {r.get('name', '?')}")
            print(f"    coords: {has_coords}  grid_ref: {grid}")
        if search_result["count"] > 5:
            print(f"  ... and {search_result['count'] - 5} more")
        print()
        print("  Coordinates are not available from search results.")
        print("  The enrichment tool fetches detail pages to resolve them.")
    else:
        print(f"  Error: {search_result['error']}")
        print("  Gateway may be unavailable. Try again later.")
        await runner.close()
        return

    # ------------------------------------------------------------------
    # 2. Enrich Gateway records — resolve coordinates
    # ------------------------------------------------------------------
    section("2. Enrich Gateway Records (Resolve Coordinates)")

    narrative("""
        The enrichment tool searches the Gateway, then fetches each
        record's detail page to extract grid references and/or
        easting/northing coordinates. This is slow (~1 sec per record)
        but only needs to be done once per search.
    """)

    print("  Enriching records (fetching detail pages)...")
    print("  This may take 30-60 seconds...\n")

    enrich_result = await runner.run(
        "her_enrich_gateway",
        what="red hill",
        max_results=10,
        fetch_details=True,
    )
    if "error" not in enrich_result:
        resolved = enrich_result["resolved_count"]
        unresolved = enrich_result["unresolved_count"]
        total = resolved + unresolved
        print(f"  {enrich_result['message']}")
        print(f"    Total searched: {total}")
        print(f"    Resolved:       {resolved}")
        print(f"    Unresolved:     {unresolved}")
        print(f"    Fetch details:  {enrich_result['fetch_details_used']}")
        print()

        enriched_records = enrich_result.get("records", [])
        if enriched_records:
            print("  Resolved records with coordinates:")
            for r in enriched_records[:10]:
                e = r.get("easting", "?")
                n = r.get("northing", "?")
                grid = r.get("grid_reference", "-")
                print(f"    {r.get('record_id', '?')}: {r.get('name', '?')}")
                print(f"      E={e}, N={n}  grid_ref={grid}")
            if len(enriched_records) > 10:
                print(f"    ... and {len(enriched_records) - 10} more")
        else:
            print("  No records could be resolved with coordinates.")
            print("  Detail pages may not contain grid references.")
    else:
        print(f"  Error: {enrich_result['error']}")
        enriched_records = []

    # ------------------------------------------------------------------
    # 3. Cross-reference WITHOUT Gateway enrichment
    # ------------------------------------------------------------------
    section("3. Cross-Reference: NHLE Only (Baseline)")

    narrative("""
        Cross-reference 8 LiDAR candidate locations against NHLE
        scheduled monuments only. This is the baseline — matching
        against the ~14 designated monuments in the study area.

        Candidates 1-2 are in the western estuary (TL grid) near
        NHLE monuments. Candidates 3-4 are placed near enriched
        Gateway records (MCC8896 at Peldon, MCC8843 at Wick Marsh)
        — areas where the NHLE has no monuments but the local HER
        has documented red hills. Candidates 5-8 are open marshland.
    """)

    candidates = [
        {"easting": 590625, "northing": 208193},  # Near known NHLE red hill
        {"easting": 590500, "northing": 208500},  # Western estuary
        {"easting": 600550, "northing": 215700},  # ~40m from MCC8896 (Peldon)
        {"easting": 602800, "northing": 216600},  # ~120m from MCC8843 (Wick Marsh)
        {"easting": 591000, "northing": 208500},  # Mid-estuary
        {"easting": 595000, "northing": 210000},  # Open saltmarsh
        {"easting": 588000, "northing": 206000},  # Near coastline
        {"easting": 600000, "northing": 212000},  # Remote area
    ]

    result_nhle = await runner.run(
        "her_cross_reference",
        candidates=json.dumps(candidates),
        match_radius_m=50,
        near_radius_m=200,
    )
    if "error" not in result_nhle:
        cls = result_nhle.get("classification", {})
        print(f"  Candidates: {result_nhle['candidates_submitted']}")
        print(f"  Match (within 50m):  {cls.get('match', 0)}")
        print(f"  Near (within 200m):  {cls.get('near', 0)}")
        print(f"  Novel (no match):    {cls.get('novel', 0)}")

        for m in result_nhle.get("matches", []):
            cand = m.get("candidate", {})
            asset = m.get("matched_asset", {})
            dist = m.get("distance_m", 0)
            print(
                f"    [match] E={cand.get('easting')}, N={cand.get('northing')}"
                f" -> {asset.get('name', '?')} ({dist}m)"
            )
        for m in result_nhle.get("near_misses", []):
            cand = m.get("candidate", {})
            asset = m.get("nearest_asset", {})
            dist = m.get("distance_m", 0)
            print(
                f"    [near ] E={cand.get('easting')}, N={cand.get('northing')}"
                f" -> {asset.get('name', '?')} ({dist}m)"
            )
    else:
        print(f"  Error: {result_nhle['error']}")

    # ------------------------------------------------------------------
    # 4. Cross-reference WITH Gateway enrichment
    # ------------------------------------------------------------------
    section("4. Cross-Reference: NHLE + Gateway Combined")

    narrative("""
        Now cross-reference the same 8 candidates but with enriched
        Gateway records merged into the known-sites pool. Candidates
        near Bower Hall Farm and Wick Marsh should now be reclassified
        from 'novel' to 'match' or 'near' — they are documented in
        the Essex HER but not in the NHLE.
    """)

    if enriched_records:
        result_combined = await runner.run(
            "her_cross_reference",
            candidates=json.dumps(candidates),
            match_radius_m=50,
            near_radius_m=200,
            gateway_sites=json.dumps(enriched_records),
        )
        if "error" not in result_combined:
            cls = result_combined.get("classification", {})
            print(f"  Candidates: {result_combined['candidates_submitted']}")
            print(f"  Match (within 50m):  {cls.get('match', 0)}")
            print(f"  Near (within 200m):  {cls.get('near', 0)}")
            print(f"  Novel (no match):    {cls.get('novel', 0)}")

            for m in result_combined.get("matches", []):
                cand = m.get("candidate", {})
                asset = m.get("matched_asset", {})
                dist = m.get("distance_m", 0)
                source = asset.get("source", "?")
                mtype = asset.get("monument_type", "")
                grade = asset.get("grade", "")
                extra = f" grade={grade}" if grade else ""
                extra += f" type={mtype}" if mtype else ""
                print(
                    f"    [match] E={cand.get('easting')}, N={cand.get('northing')}"
                    f" -> {asset.get('name', '?')} ({dist}m) [{source}]{extra}"
                )
            for m in result_combined.get("near_misses", []):
                cand = m.get("candidate", {})
                asset = m.get("nearest_asset", {})
                dist = m.get("distance_m", 0)
                source = asset.get("source", "?")
                print(
                    f"    [near ] E={cand.get('easting')}, N={cand.get('northing')}"
                    f" -> {asset.get('name', '?')} ({dist}m) [{source}]"
                )

            # Compare
            nhle_cls = result_nhle.get("classification", {})
            print()
            print("  Comparison:")
            print(
                f"    NHLE only:     {nhle_cls.get('match', 0)} match, "
                f"{nhle_cls.get('near', 0)} near, "
                f"{nhle_cls.get('novel', 0)} novel"
            )
            print(
                f"    NHLE+Gateway:  {cls.get('match', 0)} match, "
                f"{cls.get('near', 0)} near, "
                f"{cls.get('novel', 0)} novel"
            )

            novel_reduction = nhle_cls.get("novel", 0) - cls.get("novel", 0)
            if novel_reduction > 0:
                print(
                    f"\n  Gateway enrichment reclassified {novel_reduction} "
                    f"candidate(s) from 'novel' to 'match' or 'near'."
                )
        else:
            print(f"  Error: {result_combined['error']}")
    else:
        print("  Skipped — no enriched records available.")

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    section("Summary")

    narrative("""
        The enrichment pipeline enables richer cross-referencing:

        1. Search Gateway — find local HER records (no coordinates)
        2. Enrich records — fetch detail pages for grid references
        3. Resolve coordinates — grid_ref_to_bng() or direct easting/northing
        4. Merge into cross-reference — gateway_sites parameter
        5. More matches — candidates near undesignated HER records
           are now classified as 'match' or 'near' instead of 'novel'

        Workflow for an LLM agent:
        a) her_enrich_gateway(what="red hill", where="Essex")
        b) her_cross_reference(candidates=..., gateway_sites=<enriched>)

        The enrichment step is slow but only needs to be done once
        per search area. Results can be reused across multiple
        cross-reference queries.
    """)

    print("=" * 60)
    print("  Demo complete!")
    print("=" * 60)

    await runner.close()


if __name__ == "__main__":
    asyncio.run(main())
