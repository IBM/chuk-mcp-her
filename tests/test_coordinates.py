"""Tests for chuk_mcp_her.core.coordinates."""

from __future__ import annotations

import math

import pytest

from chuk_mcp_her.core.coordinates import (
    _bng_to_osgb36,
    _helmert_osgb36_to_wgs84,
    _osgb36_to_bng,
    _wgs84_to_osgb36_helmert,
    bearing_deg,
    bbox_bng_to_wgs84,
    bbox_wgs84_to_bng,
    bng_to_wgs84,
    distance_m,
    grid_ref_to_bng,
    point_buffer_bng,
    wgs84_to_bng,
)


class TestBngToWgs84:
    def test_tower_of_london(self):
        """Tower of London: E=533500 N=180500 -> ~51.508N, ~0.076W."""
        lat, lon = bng_to_wgs84(533500, 180500)
        assert abs(lat - 51.508) < 0.01, f"Expected lat ~51.508, got {lat}"
        assert abs(lon - (-0.076)) < 0.01, f"Expected lon ~-0.076, got {lon}"

    def test_stonehenge(self):
        """Stonehenge: E=412200 N=142400 -> ~51.179N, ~1.826W."""
        lat, lon = bng_to_wgs84(412200, 142400)
        assert abs(lat - 51.179) < 0.01, f"Expected lat ~51.179, got {lat}"
        assert abs(lon - (-1.826)) < 0.01, f"Expected lon ~-1.826, got {lon}"

    def test_edinburgh_castle(self):
        """Edinburgh Castle: E=325200 N=673500 -> ~55.949N, ~3.200W."""
        lat, lon = bng_to_wgs84(325200, 673500)
        assert abs(lat - 55.949) < 0.02, f"Expected lat ~55.949, got {lat}"
        assert abs(lon - (-3.200)) < 0.02, f"Expected lon ~-3.200, got {lon}"


class TestWgs84ToBng:
    def test_round_trip_tower_of_london(self):
        """BNG -> WGS84 -> BNG should round-trip within ~10m."""
        original_e, original_n = 533500.0, 180500.0
        lat, lon = bng_to_wgs84(original_e, original_n)
        e, n = wgs84_to_bng(lat, lon)
        assert abs(e - original_e) < 10, f"Easting diff {abs(e - original_e)}m"
        assert abs(n - original_n) < 10, f"Northing diff {abs(n - original_n)}m"

    def test_round_trip_stonehenge(self):
        """BNG -> WGS84 -> BNG should round-trip within ~10m."""
        original_e, original_n = 412200.0, 142400.0
        lat, lon = bng_to_wgs84(original_e, original_n)
        e, n = wgs84_to_bng(lat, lon)
        assert abs(e - original_e) < 10, f"Easting diff {abs(e - original_e)}m"
        assert abs(n - original_n) < 10, f"Northing diff {abs(n - original_n)}m"

    def test_wgs84_to_bng_known_point(self):
        """WGS84 51.508, -0.076 -> should give eastings near 533500."""
        e, n = wgs84_to_bng(51.508, -0.076)
        assert abs(e - 533500) < 200, f"Expected easting ~533500, got {e}"
        assert abs(n - 180500) < 200, f"Expected northing ~180500, got {n}"


class TestBboxWgs84ToBng:
    def test_bbox_conversion(self):
        """Convert WGS84 bbox to BNG and verify values are reasonable."""
        # London area: approx 51.4 to 51.6N, -0.2 to 0.1E
        xmin, ymin, xmax, ymax = bbox_wgs84_to_bng(-0.2, 51.4, 0.1, 51.6)
        # BNG eastings for London should be ~520000-545000
        assert 500000 < xmin < 560000, f"xmin out of range: {xmin}"
        assert 500000 < xmax < 560000, f"xmax out of range: {xmax}"
        # BNG northings for London should be ~168000-192000
        assert 150000 < ymin < 200000, f"ymin out of range: {ymin}"
        assert 150000 < ymax < 200000, f"ymax out of range: {ymax}"
        # xmax should be greater than xmin
        assert xmax > xmin
        assert ymax > ymin


class TestBboxBngToWgs84:
    def test_bbox_conversion(self):
        """Convert BNG bbox to WGS84 and verify values are reasonable."""
        min_lon, min_lat, max_lon, max_lat = bbox_bng_to_wgs84(520000, 168000, 545000, 192000)
        # Should be in London area
        assert 51.0 < min_lat < 52.0, f"min_lat out of range: {min_lat}"
        assert 51.0 < max_lat < 52.0, f"max_lat out of range: {max_lat}"
        assert -1.0 < min_lon < 1.0, f"min_lon out of range: {min_lon}"
        assert -1.0 < max_lon < 1.0, f"max_lon out of range: {max_lon}"
        assert max_lat > min_lat
        assert max_lon > min_lon

    def test_round_trip(self):
        """BNG bbox -> WGS84 bbox -> BNG bbox should round-trip."""
        original = (530000.0, 170000.0, 540000.0, 190000.0)
        min_lon, min_lat, max_lon, max_lat = bbox_bng_to_wgs84(*original)
        xmin, ymin, xmax, ymax = bbox_wgs84_to_bng(min_lon, min_lat, max_lon, max_lat)
        assert abs(xmin - original[0]) < 20, f"xmin diff: {abs(xmin - original[0])}"
        assert abs(ymin - original[1]) < 20, f"ymin diff: {abs(ymin - original[1])}"
        assert abs(xmax - original[2]) < 20, f"xmax diff: {abs(xmax - original[2])}"
        assert abs(ymax - original[3]) < 20, f"ymax diff: {abs(ymax - original[3])}"


class TestPointBufferBng:
    def test_point_buffer(self):
        """Buffer around a point should create correct bbox."""
        xmin, ymin, xmax, ymax = point_buffer_bng(533500, 180500, 500)
        assert xmin == 533000
        assert ymin == 180000
        assert xmax == 534000
        assert ymax == 181000

    def test_point_buffer_zero_radius(self):
        """Zero radius buffer should return the point itself."""
        xmin, ymin, xmax, ymax = point_buffer_bng(100000, 200000, 0)
        assert xmin == 100000
        assert ymin == 200000
        assert xmax == 100000
        assert ymax == 200000

    def test_point_buffer_symmetry(self):
        """Buffer should be symmetric around the point."""
        e, n, r = 500000, 300000, 250
        xmin, ymin, xmax, ymax = point_buffer_bng(e, n, r)
        assert (xmax - xmin) == 2 * r
        assert (ymax - ymin) == 2 * r
        assert (xmin + xmax) / 2 == e
        assert (ymin + ymax) / 2 == n


class TestDistanceM:
    def test_zero_distance(self):
        assert distance_m(100, 200, 100, 200) == 0.0

    def test_horizontal_distance(self):
        assert distance_m(0, 0, 100, 0) == 100.0

    def test_vertical_distance(self):
        assert distance_m(0, 0, 0, 100) == 100.0

    def test_diagonal_distance(self):
        d = distance_m(0, 0, 3, 4)
        assert abs(d - 5.0) < 1e-10

    def test_symmetry(self):
        d1 = distance_m(100, 200, 300, 400)
        d2 = distance_m(300, 400, 100, 200)
        assert abs(d1 - d2) < 1e-10


class TestBearingDeg:
    def test_north(self):
        """Due north should be 0 degrees."""
        b = bearing_deg(0, 0, 0, 100)
        assert abs(b - 0.0) < 1e-10 or abs(b - 360.0) < 1e-10

    def test_east(self):
        """Due east should be 90 degrees."""
        b = bearing_deg(0, 0, 100, 0)
        assert abs(b - 90.0) < 1e-10

    def test_south(self):
        """Due south should be 180 degrees."""
        b = bearing_deg(0, 100, 0, 0)
        assert abs(b - 180.0) < 1e-10

    def test_west(self):
        """Due west should be 270 degrees."""
        b = bearing_deg(100, 0, 0, 0)
        assert abs(b - 270.0) < 1e-10

    def test_northeast(self):
        """NE should be 45 degrees."""
        b = bearing_deg(0, 0, 100, 100)
        assert abs(b - 45.0) < 1e-10

    def test_result_is_0_to_360(self):
        """Bearing should always be in [0, 360)."""
        b = bearing_deg(100, 100, 0, 0)
        assert 0 <= b < 360


class TestGridRefToBng:
    """Tests for OS National Grid reference to BNG conversion."""

    def test_six_figure_with_spaces(self):
        """TL 905 085 -> E=590500, N=208500 (100m precision)."""
        e, n = grid_ref_to_bng("TL 905 085")
        assert e == 590500.0
        assert n == 208500.0

    def test_six_figure_no_spaces(self):
        """TL905085 -> same as with spaces."""
        e, n = grid_ref_to_bng("TL905085")
        assert e == 590500.0
        assert n == 208500.0

    def test_eight_figure(self):
        """TL 9050 0850 -> E=590500, N=208500 (10m precision)."""
        e, n = grid_ref_to_bng("TL 9050 0850")
        assert e == 590500.0
        assert n == 208500.0

    def test_ten_figure(self):
        """TL 90500 08500 -> E=590500, N=208500 (1m precision)."""
        e, n = grid_ref_to_bng("TL 90500 08500")
        assert e == 590500.0
        assert n == 208500.0

    def test_four_figure(self):
        """TL 90 08 -> E=590000, N=208000 (1km precision)."""
        e, n = grid_ref_to_bng("TL 90 08")
        assert e == 590000.0
        assert n == 208000.0

    def test_known_point_tower_of_london(self):
        """TQ 336 805 -> near E=533600, N=180500."""
        e, n = grid_ref_to_bng("TQ 336 805")
        assert abs(e - 533600) < 100
        assert abs(n - 180500) < 100

    def test_case_insensitive(self):
        """Lowercase input should work."""
        e, n = grid_ref_to_bng("tl 905 085")
        assert e == 590500.0
        assert n == 208500.0

    def test_invalid_prefix_raises(self):
        with pytest.raises(ValueError, match="Invalid grid reference prefix"):
            grid_ref_to_bng("XX 123 456")

    def test_odd_digits_raises(self):
        with pytest.raises(ValueError, match="even number of digits"):
            grid_ref_to_bng("TL 12345")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError, match="Invalid grid reference"):
            grid_ref_to_bng("")

    def test_two_figure(self):
        """TL 9 0 -> E=590000, N=200000 (10km precision)."""
        e, n = grid_ref_to_bng("TL 9 0")
        assert e == 590000.0
        assert n == 200000.0

    def test_prefix_only_raises(self):
        """Just 'TL' with no digits should raise."""
        with pytest.raises(ValueError, match="Invalid grid reference"):
            grid_ref_to_bng("TL")

    def test_non_digit_chars_raises(self):
        """Non-digit characters after prefix should raise."""
        with pytest.raises(ValueError, match="Invalid grid reference digits"):
            grid_ref_to_bng("TL AB")


class TestHelmertTransformations:
    """Test the private Helmert transformation functions directly."""

    def test_bng_to_osgb36_tower(self):
        """BNG -> OSGB36 for Tower of London area."""
        lat_rad, lon_rad = _bng_to_osgb36(533500, 180500)
        lat_deg = math.degrees(lat_rad)
        lon_deg = math.degrees(lon_rad)
        assert 51.4 < lat_deg < 51.6
        assert -0.2 < lon_deg < 0.1

    def test_bng_to_osgb36_stonehenge(self):
        """BNG -> OSGB36 for Stonehenge area."""
        lat_rad, lon_rad = _bng_to_osgb36(412200, 142400)
        lat_deg = math.degrees(lat_rad)
        assert 51.0 < lat_deg < 51.4

    def test_helmert_osgb36_to_wgs84(self):
        """OSGB36 -> WGS84 via Helmert for Tower of London."""
        lat_rad, lon_rad = _bng_to_osgb36(533500, 180500)
        lat, lon = _helmert_osgb36_to_wgs84(lat_rad, lon_rad)
        assert abs(lat - 51.508) < 0.01
        assert abs(lon - (-0.076)) < 0.01

    def test_wgs84_to_osgb36_helmert(self):
        """WGS84 -> OSGB36 via inverse Helmert."""
        lat_rad, lon_rad = _wgs84_to_osgb36_helmert(51.508, -0.076)
        lat_deg = math.degrees(lat_rad)
        lon_deg = math.degrees(lon_rad)
        assert 51.4 < lat_deg < 51.6
        assert -0.2 < lon_deg < 0.1

    def test_osgb36_to_bng_round_trip(self):
        """BNG -> OSGB36 -> BNG should round-trip precisely."""
        lat, lon = _bng_to_osgb36(533500, 180500)
        e, n = _osgb36_to_bng(lat, lon)
        assert abs(e - 533500) < 0.1
        assert abs(n - 180500) < 0.1

    def test_osgb36_to_bng_stonehenge(self):
        """Stonehenge BNG -> OSGB36 -> BNG round-trip."""
        lat, lon = _bng_to_osgb36(412200, 142400)
        e, n = _osgb36_to_bng(lat, lon)
        assert abs(e - 412200) < 0.1
        assert abs(n - 142400) < 0.1

    def test_full_helmert_round_trip(self):
        """Full BNG -> OSGB36 -> WGS84 -> OSGB36 -> BNG round-trip."""
        lat_rad, lon_rad = _bng_to_osgb36(412200, 142400)
        wgs_lat, wgs_lon = _helmert_osgb36_to_wgs84(lat_rad, lon_rad)
        osgb_lat, osgb_lon = _wgs84_to_osgb36_helmert(wgs_lat, wgs_lon)
        e, n = _osgb36_to_bng(osgb_lat, osgb_lon)
        assert abs(e - 412200) < 10
        assert abs(n - 142400) < 10


class TestHelmertFallbackPaths:
    """Test bng_to_wgs84 and wgs84_to_bng when pyproj is unavailable."""

    def test_bng_to_wgs84_helmert_fallback(self):
        """bng_to_wgs84 uses Helmert when pyproj transformer is None."""
        import chuk_mcp_her.core.coordinates as coords

        original = coords._transformer_to_wgs84
        try:
            coords._transformer_to_wgs84 = None
            lat, lon = coords.bng_to_wgs84(533500, 180500)
            assert abs(lat - 51.508) < 0.01
            assert abs(lon - (-0.076)) < 0.01
        finally:
            coords._transformer_to_wgs84 = original

    def test_wgs84_to_bng_helmert_fallback(self):
        """wgs84_to_bng uses Helmert when pyproj transformer is None."""
        import chuk_mcp_her.core.coordinates as coords

        original = coords._transformer_to_bng
        try:
            coords._transformer_to_bng = None
            e, n = coords.wgs84_to_bng(51.508, -0.076)
            assert abs(e - 533500) < 200
            assert abs(n - 180500) < 200
        finally:
            coords._transformer_to_bng = original

    def test_helmert_fallback_edinburgh(self):
        """Helmert fallback for Edinburgh Castle."""
        import chuk_mcp_her.core.coordinates as coords

        orig_wgs = coords._transformer_to_wgs84
        orig_bng = coords._transformer_to_bng
        try:
            coords._transformer_to_wgs84 = None
            coords._transformer_to_bng = None
            lat, lon = coords.bng_to_wgs84(325200, 673500)
            assert abs(lat - 55.949) < 0.02
            assert abs(lon - (-3.200)) < 0.02
            e, n = coords.wgs84_to_bng(lat, lon)
            assert abs(e - 325200) < 20
            assert abs(n - 673500) < 20
        finally:
            coords._transformer_to_wgs84 = orig_wgs
            coords._transformer_to_bng = orig_bng
