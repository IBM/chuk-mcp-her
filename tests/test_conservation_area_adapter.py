"""Tests for chuk_mcp_her.core.adapters.conservation_area — Conservation Area adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chuk_mcp_her.core.adapters.conservation_area import ConservationAreaAdapter
from chuk_mcp_her.core.adapters.base import PaginatedResult


# ============================================================================
# Sample data
# ============================================================================

SAMPLE_CA_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "UID": 1001.0,
                "NAME": "Maldon Conservation Area",
                "LPA": "Maldon District Council",
                "DATE_OF_DE": "1969-01-01",
                "x": 585200.0,
                "y": 207100.0,
                "Shape__Area": 125000.0,
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
                "UID": 1002.0,
                "NAME": "Heybridge Basin Conservation Area",
                "LPA": "Maldon District Council",
                "DATE_OF_DE": "1984-06-15",
                "x": 586800.0,
                "y": 207300.0,
                "Shape__Area": 45000.0,
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [586700.0, 207200.0],
                        [586900.0, 207200.0],
                        [586900.0, 207400.0],
                        [586700.0, 207400.0],
                        [586700.0, 207200.0],
                    ]
                ],
            },
        },
    ],
}


def _make_query_response(features: list | None = None) -> dict:
    if features is None:
        features = SAMPLE_CA_GEOJSON["features"]
    return {"type": "FeatureCollection", "features": features}


def _make_count_response(count: int = 25) -> dict:
    return {"count": count}


# ============================================================================
# Properties
# ============================================================================


class TestConservationAreaAdapterProperties:
    def test_source_id(self):
        with patch("chuk_mcp_her.core.adapters.conservation_area.ArcGISClient"):
            adapter = ConservationAreaAdapter()
        assert adapter.source_id == "conservation_area"

    def test_capabilities(self):
        with patch("chuk_mcp_her.core.adapters.conservation_area.ArcGISClient"):
            adapter = ConservationAreaAdapter()
        cap = adapter.capabilities
        assert cap.supports_spatial_query is True
        assert cap.supports_text_search is True
        assert cap.supports_feature_count is True
        assert cap.supports_pagination is True
        assert cap.supports_attribute_filter is False


# ============================================================================
# Build WHERE
# ============================================================================


class TestBuildWhere:
    def test_no_filters(self):
        assert ConservationAreaAdapter._build_where() == "1=1"

    def test_query_only(self):
        result = ConservationAreaAdapter._build_where(query="Maldon")
        assert "NAME LIKE '%Maldon%'" in result

    def test_lpa_only(self):
        result = ConservationAreaAdapter._build_where(lpa="Maldon District")
        assert "LPA LIKE '%Maldon District%'" in result

    def test_query_and_lpa_combined(self):
        result = ConservationAreaAdapter._build_where(query="Basin", lpa="Maldon")
        assert "NAME LIKE '%Basin%'" in result
        assert "LPA LIKE '%Maldon%'" in result
        assert " AND " in result

    def test_escaping(self):
        result = ConservationAreaAdapter._build_where(query="Bishop's")
        assert "Bishop''s" in result


# ============================================================================
# Build Geometry
# ============================================================================


class TestBuildGeometry:
    def test_no_params(self):
        assert ConservationAreaAdapter._build_geometry() is None

    def test_bbox(self):
        result = ConservationAreaAdapter._build_geometry(bbox=(585000, 207000, 587000, 208000))
        assert result == {
            "xmin": 585000,
            "ymin": 207000,
            "xmax": 587000,
            "ymax": 208000,
        }

    def test_lat_lon_radius(self):
        result = ConservationAreaAdapter._build_geometry(lat=51.73, lon=0.68, radius_m=1000)
        assert result is not None
        assert "xmin" in result
        assert "ymin" in result
        assert "xmax" in result
        assert "ymax" in result

    def test_lat_lon_without_radius(self):
        result = ConservationAreaAdapter._build_geometry(lat=51.73, lon=0.68)
        assert result is None


# ============================================================================
# Normalize Feature
# ============================================================================


class TestConservationAreaAdapterNormalize:
    def test_normalize_feature_fields(self):
        feature = SAMPLE_CA_GEOJSON["features"][0]
        result = ConservationAreaAdapter._normalize_feature(feature)

        assert result["record_id"] == "ca:1001.0"
        assert result["uid"] == 1001.0
        assert result["name"] == "Maldon Conservation Area"
        assert result["source"] == "conservation_area"
        assert result["lpa"] == "Maldon District Council"
        assert result["designation_date"] == "1969-01-01"
        assert result["easting"] == 585200.0
        assert result["northing"] == 207100.0
        assert result["area_sqm"] == 125000.0
        # lat/lon should be converted from BNG via bng_to_wgs84
        assert result["lat"] is not None
        assert result["lon"] is not None
        assert isinstance(result["lat"], float)
        assert isinstance(result["lon"], float)

    def test_normalize_feature_missing_fields(self):
        """Handles missing optional fields gracefully."""
        feature = {
            "type": "Feature",
            "properties": {
                "OBJECTID": 9999,
            },
            "geometry": None,
        }
        result = ConservationAreaAdapter._normalize_feature(feature)

        assert result["record_id"] == "ca:9999"
        assert result["uid"] == 9999
        assert result["name"] == "Unknown conservation area"
        assert result["source"] == "conservation_area"
        assert result["lpa"] is None
        assert result["designation_date"] is None
        assert result["easting"] is None
        assert result["northing"] is None
        assert "lat" not in result
        assert "lon" not in result
        assert "area_sqm" not in result

    def test_normalize_feature_no_centroid_coords(self):
        """Feature with UID but no x/y centroid properties."""
        feature = {
            "type": "Feature",
            "properties": {
                "UID": 5555.0,
                "NAME": "Test Area",
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
        }
        result = ConservationAreaAdapter._normalize_feature(feature)
        assert result["record_id"] == "ca:5555.0"
        assert result["name"] == "Test Area"
        # No x/y in properties so no lat/lon conversion
        assert result["easting"] is None
        assert result["northing"] is None
        assert "lat" not in result


# ============================================================================
# Search
# ============================================================================


class TestConservationAreaAdapterSearch:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.conservation_area.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = ConservationAreaAdapter()

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
            return_value=_make_query_response([SAMPLE_CA_GEOJSON["features"][0]])
        )
        result = await self.adapter.search(query="Maldon")
        assert len(result.features) == 1
        call_kwargs = self.mock_client.query.call_args[1]
        assert "NAME LIKE '%Maldon%'" in call_kwargs["where"]

    async def test_search_with_lpa(self):
        self.mock_client.count = AsyncMock(return_value=2)
        self.mock_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search(lpa="Maldon District")
        assert len(result.features) == 2
        call_kwargs = self.mock_client.query.call_args[1]
        assert "LPA LIKE '%Maldon District%'" in call_kwargs["where"]

    async def test_search_with_bbox(self):
        self.mock_client.count = AsyncMock(return_value=2)
        self.mock_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search(bbox=(585000, 207000, 587000, 208000))
        assert len(result.features) == 2
        call_kwargs = self.mock_client.query.call_args[1]
        assert call_kwargs["geometry"] is not None
        assert call_kwargs["geometry"]["xmin"] == 585000

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

    async def test_search_passes_out_sr(self):
        """Verify search passes out_sr=27700 to the query call."""
        self.mock_client.count = AsyncMock(return_value=1)
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_CA_GEOJSON["features"][0]])
        )
        await self.adapter.search()
        call_kwargs = self.mock_client.query.call_args[1]
        assert call_kwargs["out_sr"] == 27700


# ============================================================================
# Get By ID
# ============================================================================


class TestConservationAreaAdapterGetById:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.conservation_area.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = ConservationAreaAdapter()

    async def test_get_by_id_with_prefix(self):
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_CA_GEOJSON["features"][0]])
        )
        result = await self.adapter.get_by_id("ca:1234")
        assert result is not None
        # Verify prefix was stripped and UID used in WHERE clause
        call_kwargs = self.mock_client.query.call_args[1]
        assert "UID = 1234" in call_kwargs["where"]
        assert "ca:" not in call_kwargs["where"]

    async def test_get_by_id_not_found(self):
        self.mock_client.query = AsyncMock(return_value=_make_query_response([]))
        result = await self.adapter.get_by_id("ca:9999")
        assert result is None

    async def test_get_by_id_without_prefix(self):
        """ID without 'ca:' prefix still works (replace is a no-op)."""
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_CA_GEOJSON["features"][0]])
        )
        result = await self.adapter.get_by_id("5678")
        assert result is not None
        call_kwargs = self.mock_client.query.call_args[1]
        assert "UID = 5678" in call_kwargs["where"]


# ============================================================================
# Count
# ============================================================================


class TestConservationAreaAdapterCount:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.conservation_area.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = ConservationAreaAdapter()

    async def test_count_basic(self):
        self.mock_client.count = AsyncMock(return_value=25)
        result = await self.adapter.count()
        assert result == 25

    async def test_count_with_lpa(self):
        self.mock_client.count = AsyncMock(return_value=3)
        result = await self.adapter.count(lpa="Maldon")
        assert result == 3
        call_kwargs = self.mock_client.count.call_args[1]
        assert "LPA LIKE '%Maldon%'" in call_kwargs["where"]

    async def test_count_with_bbox(self):
        self.mock_client.count = AsyncMock(return_value=10)
        result = await self.adapter.count(bbox=(585000, 207000, 587000, 208000))
        assert result == 10
        call_kwargs = self.mock_client.count.call_args[1]
        assert call_kwargs["geometry"] is not None

    async def test_count_with_query(self):
        self.mock_client.count = AsyncMock(return_value=1)
        result = await self.adapter.count(query="Maldon")
        assert result == 1
        call_kwargs = self.mock_client.count.call_args[1]
        assert "NAME LIKE '%Maldon%'" in call_kwargs["where"]
