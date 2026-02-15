"""Tests for chuk_mcp_her.core.adapters.heritage_at_risk — Heritage at Risk adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chuk_mcp_her.core.adapters.heritage_at_risk import HeritageAtRiskAdapter
from chuk_mcp_her.core.adapters.base import PaginatedResult


# ============================================================================
# Sample data
# ============================================================================

SAMPLE_HAR_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "List_Entry": 1021506,
                "EntryName": "Church of All Saints, Maldon",
                "HeritageCa": "Listed Building",
                "Risk_Metho": "Priority Category A",
                "Shape_Area": None,
                "URL": "https://historicengland.org.uk/advice/heritage-at-risk/search-register/list-entry/1021506",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [585100.0, 207000.0],
                        [585300.0, 207000.0],
                        [585300.0, 207200.0],
                        [585100.0, 207200.0],
                        [585100.0, 207000.0],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "List_Entry": 1022344,
                "EntryName": "Beeleigh Abbey, Maldon",
                "HeritageCa": "Scheduled Monument",
                "Risk_Metho": "Priority Category B",
                "Shape_Area": 8500.0,
                "URL": "https://historicengland.org.uk/advice/heritage-at-risk/search-register/list-entry/1022344",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [584500.0, 206500.0],
                        [584700.0, 206500.0],
                        [584700.0, 206700.0],
                        [584500.0, 206700.0],
                        [584500.0, 206500.0],
                    ]
                ],
            },
        },
    ],
}


def _make_query_response(features: list | None = None) -> dict:
    if features is None:
        features = SAMPLE_HAR_GEOJSON["features"]
    return {"type": "FeatureCollection", "features": features}


def _make_count_response(count: int = 15) -> dict:
    return {"count": count}


# ============================================================================
# Properties
# ============================================================================


class TestHeritageAtRiskAdapterProperties:
    def test_source_id(self):
        with patch("chuk_mcp_her.core.adapters.heritage_at_risk.ArcGISClient"):
            adapter = HeritageAtRiskAdapter()
        assert adapter.source_id == "heritage_at_risk"

    def test_capabilities(self):
        with patch("chuk_mcp_her.core.adapters.heritage_at_risk.ArcGISClient"):
            adapter = HeritageAtRiskAdapter()
        cap = adapter.capabilities
        assert cap.supports_spatial_query is True
        assert cap.supports_text_search is True
        assert cap.supports_feature_count is True
        assert cap.supports_attribute_filter is True
        assert cap.supports_pagination is True


# ============================================================================
# Build WHERE
# ============================================================================


class TestBuildWhere:
    def test_no_filters(self):
        assert HeritageAtRiskAdapter._build_where() == "1=1"

    def test_query_only(self):
        result = HeritageAtRiskAdapter._build_where(query="Church")
        assert "EntryName LIKE '%Church%'" in result

    def test_heritage_category_only(self):
        result = HeritageAtRiskAdapter._build_where(heritage_category="Listed Building")
        assert "HeritageCa = 'Listed Building'" in result

    def test_combined_filters(self):
        result = HeritageAtRiskAdapter._build_where(
            query="Abbey", heritage_category="Scheduled Monument"
        )
        assert "EntryName LIKE '%Abbey%'" in result
        assert "HeritageCa = 'Scheduled Monument'" in result
        assert " AND " in result

    def test_escaping(self):
        result = HeritageAtRiskAdapter._build_where(query="St Mary's")
        assert "St Mary''s" in result

    def test_heritage_category_escaping(self):
        result = HeritageAtRiskAdapter._build_where(heritage_category="O'Brien's Category")
        assert "O''Brien''s Category" in result


# ============================================================================
# Build Geometry
# ============================================================================


class TestBuildGeometry:
    def test_no_params(self):
        assert HeritageAtRiskAdapter._build_geometry() is None

    def test_bbox(self):
        result = HeritageAtRiskAdapter._build_geometry(bbox=(585000, 207000, 587000, 208000))
        assert result == {
            "xmin": 585000,
            "ymin": 207000,
            "xmax": 587000,
            "ymax": 208000,
        }

    def test_lat_lon_radius(self):
        result = HeritageAtRiskAdapter._build_geometry(lat=51.73, lon=0.68, radius_m=1000)
        assert result is not None
        assert "xmin" in result
        assert "ymin" in result
        assert "xmax" in result
        assert "ymax" in result

    def test_lat_lon_without_radius(self):
        result = HeritageAtRiskAdapter._build_geometry(lat=51.73, lon=0.68)
        assert result is None


# ============================================================================
# Normalize Feature
# ============================================================================


class TestHeritageAtRiskAdapterNormalize:
    def test_normalize_feature_fields(self):
        feature = SAMPLE_HAR_GEOJSON["features"][0]
        result = HeritageAtRiskAdapter._normalize_feature(feature)

        assert result["record_id"] == "har:1021506"
        assert result["list_entry"] == 1021506
        assert result["name"] == "Church of All Saints, Maldon"
        assert result["source"] == "heritage_at_risk"
        assert result["heritage_category"] == "Listed Building"
        assert result["risk_methodology"] == "Priority Category A"
        assert result["url"] == (
            "https://historicengland.org.uk/advice/heritage-at-risk/"
            "search-register/list-entry/1021506"
        )
        assert result["area_sqm"] is None

    def test_normalize_computes_centroid(self):
        """Centroid is computed from polygon ring coordinates."""
        feature = SAMPLE_HAR_GEOJSON["features"][0]
        result = HeritageAtRiskAdapter._normalize_feature(feature)

        # The polygon ring has 5 points (closed ring); centroid of the
        # rectangle [585100,207000]-[585300,207200] averages to:
        #   easting ~ 585200, northing ~ 207100
        # (with slight bias from closing point)
        assert result["easting"] is not None
        assert result["northing"] is not None
        assert abs(result["easting"] - 585200.0) < 50.0
        assert abs(result["northing"] - 207100.0) < 50.0
        # WGS84 conversion should yield valid lat/lon
        assert result["lat"] is not None
        assert result["lon"] is not None
        assert isinstance(result["lat"], float)
        assert isinstance(result["lon"], float)

    def test_normalize_multipolygon(self):
        """Centroid computed from first ring of MultiPolygon."""
        feature = {
            "type": "Feature",
            "properties": {
                "List_Entry": 9999,
                "EntryName": "Multi Polygon Feature",
                "HeritageCa": "Conservation Area",
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [585100.0, 207000.0],
                            [585300.0, 207000.0],
                            [585300.0, 207200.0],
                            [585100.0, 207200.0],
                            [585100.0, 207000.0],
                        ]
                    ]
                ],
            },
        }
        result = HeritageAtRiskAdapter._normalize_feature(feature)
        assert result["easting"] is not None
        assert abs(result["easting"] - 585200.0) < 50.0

    def test_normalize_point_geometry(self):
        """Point geometry uses coordinates directly."""
        feature = {
            "type": "Feature",
            "properties": {
                "List_Entry": 8888,
                "EntryName": "Point Feature",
                "HeritageCa": "Protected Wreck Site",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [585200.0, 207100.0],
            },
        }
        result = HeritageAtRiskAdapter._normalize_feature(feature)
        assert abs(result["easting"] - 585200.0) < 1.0
        assert abs(result["northing"] - 207100.0) < 1.0

    def test_normalize_no_geometry(self):
        """Feature with no geometry produces no easting/lat fields."""
        feature = {
            "type": "Feature",
            "properties": {
                "List_Entry": 7777,
                "EntryName": "No Geometry Feature",
                "HeritageCa": "Listed Building",
            },
            "geometry": None,
        }
        result = HeritageAtRiskAdapter._normalize_feature(feature)
        assert result["record_id"] == "har:7777"
        assert result["name"] == "No Geometry Feature"
        assert "easting" not in result
        assert "lat" not in result

    def test_normalize_fallback_to_fid(self):
        """When List_Entry is missing, falls back to FID for record_id."""
        feature = {
            "type": "Feature",
            "properties": {
                "FID": 42,
                "EntryName": "FID-only Feature",
                "HeritageCa": "Scheduled Monument",
            },
            "geometry": None,
        }
        result = HeritageAtRiskAdapter._normalize_feature(feature)
        assert result["record_id"] == "har:42"
        assert result["list_entry"] is None

    def test_normalize_missing_name(self):
        """Missing EntryName falls back to 'Unknown'."""
        feature = {
            "type": "Feature",
            "properties": {
                "List_Entry": 5555,
            },
            "geometry": None,
        }
        result = HeritageAtRiskAdapter._normalize_feature(feature)
        assert result["name"] == "Unknown"


# ============================================================================
# Search
# ============================================================================


class TestHeritageAtRiskAdapterSearch:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.heritage_at_risk.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = HeritageAtRiskAdapter()

    async def test_search_basic(self):
        self.mock_client.count = AsyncMock(return_value=2)
        self.mock_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search()
        assert isinstance(result, PaginatedResult)
        assert len(result.features) == 2
        assert result.total_count == 2
        assert result.has_more is False

    async def test_search_with_query(self):
        self.mock_client.count = AsyncMock(return_value=1)
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_HAR_GEOJSON["features"][0]])
        )
        result = await self.adapter.search(query="Church")
        assert len(result.features) == 1
        call_kwargs = self.mock_client.query.call_args[1]
        assert "EntryName LIKE '%Church%'" in call_kwargs["where"]

    async def test_search_with_heritage_category(self):
        self.mock_client.count = AsyncMock(return_value=1)
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_HAR_GEOJSON["features"][0]])
        )
        result = await self.adapter.search(heritage_category="Listed Building")
        assert len(result.features) == 1
        call_kwargs = self.mock_client.query.call_args[1]
        assert "HeritageCa = 'Listed Building'" in call_kwargs["where"]

    async def test_search_with_bbox(self):
        self.mock_client.count = AsyncMock(return_value=2)
        self.mock_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search(bbox=(585000, 207000, 587000, 208000))
        assert len(result.features) == 2
        call_kwargs = self.mock_client.query.call_args[1]
        assert call_kwargs["geometry"] is not None
        assert call_kwargs["geometry"]["xmin"] == 585000
        # HAR adapter passes in_sr=27700 and out_sr=27700
        assert call_kwargs["in_sr"] == 27700
        assert call_kwargs["out_sr"] == 27700

    async def test_search_empty_results(self):
        self.mock_client.count = AsyncMock(return_value=0)
        self.mock_client.query = AsyncMock(return_value=_make_query_response([]))
        result = await self.adapter.search()
        assert len(result.features) == 0
        assert result.total_count == 0
        assert result.has_more is False

    async def test_search_pagination(self):
        self.mock_client.count = AsyncMock(return_value=100)
        self.mock_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search(max_results=2, offset=0)
        assert result.has_more is True
        assert result.next_offset == 2

    async def test_search_passes_in_sr_and_out_sr(self):
        """HAR service uses SRID 3857 natively; adapter passes in_sr/out_sr."""
        self.mock_client.count = AsyncMock(return_value=1)
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_HAR_GEOJSON["features"][0]])
        )
        await self.adapter.search()
        # Check query call
        query_kwargs = self.mock_client.query.call_args[1]
        assert query_kwargs["in_sr"] == 27700
        assert query_kwargs["out_sr"] == 27700
        # Check count call
        count_kwargs = self.mock_client.count.call_args[1]
        assert count_kwargs["in_sr"] == 27700


# ============================================================================
# Get By ID
# ============================================================================


class TestHeritageAtRiskAdapterGetById:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.heritage_at_risk.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = HeritageAtRiskAdapter()

    async def test_get_by_id_with_prefix(self):
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_HAR_GEOJSON["features"][0]])
        )
        result = await self.adapter.get_by_id("har:1021506")
        assert result is not None
        assert result["list_entry"] == 1021506
        # Verify prefix was stripped and List_Entry used in WHERE clause
        call_kwargs = self.mock_client.query.call_args[1]
        assert "List_Entry = 1021506" in call_kwargs["where"]
        assert "har:" not in call_kwargs["where"]

    async def test_get_by_id_not_found(self):
        self.mock_client.query = AsyncMock(return_value=_make_query_response([]))
        result = await self.adapter.get_by_id("har:9999999")
        assert result is None

    async def test_get_by_id_string_uid(self):
        """Non-numeric ID uses uid = 'value' query format."""
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_HAR_GEOJSON["features"][0]])
        )
        result = await self.adapter.get_by_id("har:some-uuid-string")
        assert result is not None
        call_kwargs = self.mock_client.query.call_args[1]
        assert "uid = 'some-uuid-string'" in call_kwargs["where"]

    async def test_get_by_id_passes_in_sr_out_sr(self):
        """get_by_id passes in_sr=27700, out_sr=27700."""
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_HAR_GEOJSON["features"][0]])
        )
        await self.adapter.get_by_id("har:1021506")
        call_kwargs = self.mock_client.query.call_args[1]
        assert call_kwargs["in_sr"] == 27700
        assert call_kwargs["out_sr"] == 27700


# ============================================================================
# Count
# ============================================================================


class TestHeritageAtRiskAdapterCount:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.heritage_at_risk.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = HeritageAtRiskAdapter()

    async def test_count_basic(self):
        self.mock_client.count = AsyncMock(return_value=15)
        result = await self.adapter.count()
        assert result == 15

    async def test_count_with_heritage_category(self):
        self.mock_client.count = AsyncMock(return_value=5)
        result = await self.adapter.count(heritage_category="Listed Building")
        assert result == 5
        call_kwargs = self.mock_client.count.call_args[1]
        assert "HeritageCa = 'Listed Building'" in call_kwargs["where"]

    async def test_count_with_bbox(self):
        self.mock_client.count = AsyncMock(return_value=10)
        result = await self.adapter.count(bbox=(585000, 207000, 587000, 208000))
        assert result == 10
        call_kwargs = self.mock_client.count.call_args[1]
        assert call_kwargs["geometry"] is not None

    async def test_count_passes_in_sr(self):
        """Count passes in_sr=27700 for HAR SRID 3857 service."""
        self.mock_client.count = AsyncMock(return_value=1)
        await self.adapter.count()
        call_kwargs = self.mock_client.count.call_args[1]
        assert call_kwargs["in_sr"] == 27700

    async def test_count_with_query(self):
        self.mock_client.count = AsyncMock(return_value=3)
        result = await self.adapter.count(query="Church")
        assert result == 3
        call_kwargs = self.mock_client.count.call_args[1]
        assert "EntryName LIKE '%Church%'" in call_kwargs["where"]
