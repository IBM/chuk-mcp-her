"""Tests for chuk_mcp_her.core.spatial_index."""

from __future__ import annotations

import math
import time

import pytest

from chuk_mcp_her.core.spatial_index import GridSpatialIndex


def _asset(e: float, n: float, **kwargs) -> dict:
    """Helper to create a test asset dict."""
    return {"easting": e, "northing": n, **kwargs}


class TestGridSpatialIndexBasics:
    def test_empty_index_returns_none(self):
        idx = GridSpatialIndex(200.0)
        asset, dist = idx.nearest(500000, 200000, 200)
        assert asset is None
        assert dist == float("inf")

    def test_insert_single_asset(self):
        idx = GridSpatialIndex(200.0)
        assert idx.insert(_asset(500000, 200000, name="A"))
        assert idx.count == 1

    def test_insert_returns_false_for_no_coords(self):
        idx = GridSpatialIndex(200.0)
        assert not idx.insert({"name": "no coords"})
        assert not idx.insert({"easting": 500000})
        assert not idx.insert({"northing": 200000})
        assert not idx.insert({"easting": None, "northing": None})
        assert idx.count == 0

    def test_build_bulk_insert(self):
        idx = GridSpatialIndex(200.0)
        assets = [_asset(500000 + i * 100, 200000) for i in range(10)]
        inserted = idx.build(assets)
        assert inserted == 10
        assert idx.count == 10

    def test_build_skips_invalid(self):
        idx = GridSpatialIndex(200.0)
        assets = [
            _asset(500000, 200000),
            {"name": "no coords"},
            _asset(500100, 200100),
        ]
        inserted = idx.build(assets)
        assert inserted == 2
        assert idx.count == 2

    def test_count_property(self):
        idx = GridSpatialIndex(200.0)
        assert idx.count == 0
        idx.insert(_asset(500000, 200000))
        assert idx.count == 1
        idx.insert(_asset(500100, 200100))
        assert idx.count == 2

    def test_cell_count_property(self):
        idx = GridSpatialIndex(200.0)
        assert idx.cell_count == 0
        # Two assets in same cell
        idx.insert(_asset(500000, 200000))
        idx.insert(_asset(500050, 200050))
        assert idx.cell_count == 1
        # Asset in different cell
        idx.insert(_asset(500500, 200500))
        assert idx.cell_count == 2

    def test_zero_cell_size_raises(self):
        with pytest.raises(ValueError, match="positive"):
            GridSpatialIndex(0)

    def test_negative_cell_size_raises(self):
        with pytest.raises(ValueError, match="positive"):
            GridSpatialIndex(-100)


class TestGridSpatialIndexNearest:
    def test_exact_match_distance_zero(self):
        idx = GridSpatialIndex(200.0)
        idx.insert(_asset(500000, 200000, name="A"))
        asset, dist = idx.nearest(500000, 200000, 200)
        assert asset is not None
        assert asset["name"] == "A"
        assert dist == 0.0

    def test_nearest_within_cell(self):
        idx = GridSpatialIndex(200.0)
        idx.insert(_asset(500000, 200000, name="far"))
        idx.insert(_asset(500050, 200050, name="close"))
        asset, dist = idx.nearest(500060, 200060, 200)
        assert asset is not None
        assert asset["name"] == "close"
        assert dist < 15  # ~14m

    def test_nearest_across_cells(self):
        idx = GridSpatialIndex(100.0)
        # Asset in adjacent cell
        idx.insert(_asset(500150, 200050, name="adjacent"))
        asset, dist = idx.nearest(500050, 200050, 200)
        assert asset is not None
        assert asset["name"] == "adjacent"
        assert abs(dist - 100.0) < 0.01

    def test_beyond_max_distance_returns_none(self):
        idx = GridSpatialIndex(200.0)
        idx.insert(_asset(500000, 200000, name="A"))
        asset, dist = idx.nearest(501000, 201000, 200)
        assert asset is None
        assert dist == float("inf")

    def test_multiple_assets_returns_closest(self):
        idx = GridSpatialIndex(200.0)
        idx.insert(_asset(500000, 200000, name="d=141"))
        idx.insert(_asset(500050, 200050, name="d=71"))
        idx.insert(_asset(500080, 200080, name="d=28"))
        idx.insert(_asset(500200, 200200, name="d=141_2"))
        idx.insert(_asset(500300, 200300, name="d=283"))
        asset, dist = idx.nearest(500100, 200100, 500)
        assert asset is not None
        assert asset["name"] == "d=28"
        expected = math.sqrt(20**2 + 20**2)
        assert abs(dist - expected) < 0.01

    def test_match_vs_near_threshold(self):
        """Asset at 45m is within 50m match but outside 40m match."""
        idx = GridSpatialIndex(200.0)
        idx.insert(_asset(500000, 200000))
        # Query 45m away
        asset_50, dist_50 = idx.nearest(500045, 200000, 50)
        assert asset_50 is not None
        assert dist_50 == 45.0

        asset_40, dist_40 = idx.nearest(500045, 200000, 40)
        assert asset_40 is None
        assert dist_40 == float("inf")

    def test_diagonal_distance(self):
        idx = GridSpatialIndex(200.0)
        idx.insert(_asset(500000, 200000, name="origin"))
        asset, dist = idx.nearest(500003, 200004, 200)
        assert asset is not None
        assert abs(dist - 5.0) < 0.01  # 3-4-5 triangle


class TestGridSpatialIndexEdgeCases:
    def test_asset_on_cell_boundary(self):
        idx = GridSpatialIndex(200.0)
        # Exactly on cell boundary (200.0, 200.0)
        idx.insert(_asset(200.0, 200.0, name="boundary"))
        asset, dist = idx.nearest(200.0, 200.0, 50)
        assert asset is not None
        assert dist == 0.0

    def test_custom_cell_size(self):
        idx = GridSpatialIndex(500.0)
        idx.insert(_asset(500000, 200000, name="A"))
        idx.insert(_asset(500400, 200400, name="B"))
        # Both should be in same cell at 500m resolution
        assert idx.cell_count == 1

    def test_large_cell_size(self):
        idx = GridSpatialIndex(1000.0)
        idx.insert(_asset(500000, 200000, name="A"))
        # Query 900m away — within cell neighbourhood
        asset, dist = idx.nearest(500900, 200000, 1000)
        assert asset is not None
        assert abs(dist - 900.0) < 0.01

    def test_large_dataset_performance(self):
        """10,000 assets and 100 queries should complete quickly."""
        idx = GridSpatialIndex(200.0)
        assets = [_asset(500000 + i, 200000 + (i * 7) % 10000) for i in range(10000)]
        idx.build(assets)
        assert idx.count == 10000

        start = time.monotonic()
        for i in range(100):
            idx.nearest(500000 + i * 50, 200000 + i * 30, 200)
        elapsed = time.monotonic() - start
        assert elapsed < 2.0  # Should be well under 1 second

    def test_assets_at_same_location(self):
        """Multiple assets at identical coordinates."""
        idx = GridSpatialIndex(200.0)
        idx.insert(_asset(500000, 200000, name="A"))
        idx.insert(_asset(500000, 200000, name="B"))
        assert idx.count == 2
        asset, dist = idx.nearest(500000, 200000, 200)
        assert asset is not None
        assert dist == 0.0
        # Should get one of them (first inserted, since it checks in order)
        assert asset["name"] in ("A", "B")

    def test_no_match_empty_neighbourhood(self):
        """Asset exists but far from query point — not in 3x3 cells."""
        idx = GridSpatialIndex(100.0)
        idx.insert(_asset(500000, 200000))
        # Query 500m away — outside 3x3 neighbourhood at 100m cell size
        asset, dist = idx.nearest(500500, 200500, 1000)
        # 3x3 at 100m cell = 300m coverage. 500m diagonal > 300m, so not found.
        assert asset is None
