"""Tests for chuk_mcp_her.core.adapters.scotland — Scotland adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chuk_mcp_her.core.adapters.base import PaginatedResult
from chuk_mcp_her.core.adapters.scotland import ScotlandAdapter

from tests.conftest import (
    SAMPLE_SCOTLAND_DESIGNATION_ARCGIS_GEOJSON,
    SAMPLE_SCOTLAND_NRHE_ARCGIS_GEOJSON,
)


# ============================================================================
# Helpers
# ============================================================================


def _make_nrhe_point_feature(
    canmore_id: str = "12345",
    name: str = "Edinburgh Castle",
    site_type: str = "CASTLE",
    coords: list | None = None,
) -> dict:
    """Build a minimal Canmore Points GeoJSON feature."""
    if coords is None:
        coords = [325200.0, 673480.0]
    return {
        "type": "Feature",
        "properties": {
            "CANMOREID": canmore_id,
            "SITENUMBER": "NT27SE 1",
            "NMRSNAME": name,
            "ALTNAME": None,
            "BROADCLASS": "SECULAR",
            "SITETYPE": site_type,
            "FORM": "Building",
            "COUNTY": "Midlothian",
            "COUNCIL": "City of Edinburgh",
            "PARISH": "Edinburgh",
            "GRIDREF": "NT 2520 7348",
            "URL": "https://canmore.org.uk/site/12345",
            "XCOORD": coords[0],
            "YCOORD": coords[1],
        },
        "geometry": {"type": "Point", "coordinates": coords},
    }


def _make_designation_feature(
    des_ref: str = "LB12345",
    name: str = "St Giles Cathedral",
    category: str = "A",
    coords: list | None = None,
) -> dict:
    """Build a minimal HES Designation GeoJSON feature."""
    if coords is None:
        coords = [325700.0, 673600.0]
    return {
        "type": "Feature",
        "properties": {
            "DES_REF": des_ref,
            "DES_TITLE": name,
            "DES_TYPE": "Listed Building",
            "CATEGORY": category,
            "DESIGNATED": "1970-01-01",
            "LOCAL_AUTH": "City of Edinburgh",
            "LINK": "https://portal.historicenvironment.scot/designation/LB12345",
            "X": coords[0],
            "Y": coords[1],
        },
        "geometry": {"type": "Point", "coordinates": coords},
    }


def _make_query_response(features: list | None = None) -> dict:
    if features is None:
        features = SAMPLE_SCOTLAND_NRHE_ARCGIS_GEOJSON["features"]
    return {"type": "FeatureCollection", "features": features}


def _make_designation_query_response(features: list | None = None) -> dict:
    if features is None:
        features = SAMPLE_SCOTLAND_DESIGNATION_ARCGIS_GEOJSON["features"]
    return {"type": "FeatureCollection", "features": features}


# ============================================================================
# Properties
# ============================================================================


class TestScotlandAdapterProperties:
    def test_source_id(self):
        with patch("chuk_mcp_her.core.adapters.scotland.ArcGISClient"):
            adapter = ScotlandAdapter()
        assert adapter.source_id == "scotland"

    def test_capabilities(self):
        with patch("chuk_mcp_her.core.adapters.scotland.ArcGISClient"):
            adapter = ScotlandAdapter()
        cap = adapter.capabilities
        assert cap.supports_spatial_query is True
        assert cap.supports_text_search is True
        assert cap.supports_feature_count is False  # MapServer limitation
        assert cap.supports_attribute_filter is True
        assert cap.supports_pagination is False  # MapServer limitation
        assert "listed_building" in cap.supported_designation_types
        assert "scheduled_monument" in cap.supported_designation_types


# ============================================================================
# Build WHERE (NRHE)
# ============================================================================


class TestBuildNRHEWhere:
    def test_no_filters(self):
        assert ScotlandAdapter._build_nrhe_where() == "1=1"

    def test_query_only(self):
        result = ScotlandAdapter._build_nrhe_where(query="Castle")
        assert "NMRSNAME LIKE '%Castle%'" in result

    def test_site_type(self):
        result = ScotlandAdapter._build_nrhe_where(site_type="BROCH")
        assert "SITETYPE LIKE '%BROCH%'" in result

    def test_broad_class(self):
        result = ScotlandAdapter._build_nrhe_where(broad_class="DOMESTIC")
        assert "BROADCLASS LIKE '%DOMESTIC%'" in result

    def test_council(self):
        result = ScotlandAdapter._build_nrhe_where(council="Highland")
        assert "COUNCIL LIKE '%Highland%'" in result

    def test_combined(self):
        result = ScotlandAdapter._build_nrhe_where(
            query="Cairn", site_type="CAIRN", council="Highland"
        )
        assert "NMRSNAME LIKE '%Cairn%'" in result
        assert "SITETYPE LIKE '%CAIRN%'" in result
        assert "COUNCIL LIKE '%Highland%'" in result
        assert " AND " in result

    def test_escaping(self):
        result = ScotlandAdapter._build_nrhe_where(query="O'Brien")
        assert "O''Brien" in result


# ============================================================================
# Build WHERE (Designations)
# ============================================================================


class TestBuildDesignationWhere:
    def test_no_query(self):
        assert ScotlandAdapter._build_designation_where() == "1=1"

    def test_with_query(self):
        result = ScotlandAdapter._build_designation_where(query="Cathedral")
        assert "DES_TITLE LIKE '%Cathedral%'" in result


# ============================================================================
# Build Geometry
# ============================================================================


class TestBuildGeometry:
    def test_no_params(self):
        assert ScotlandAdapter._build_geometry() is None

    def test_bbox(self):
        result = ScotlandAdapter._build_geometry(bbox=(325000, 673000, 326000, 674000))
        assert result == {
            "xmin": 325000,
            "ymin": 673000,
            "xmax": 326000,
            "ymax": 674000,
        }

    def test_lat_lon_radius(self):
        result = ScotlandAdapter._build_geometry(lat=55.95, lon=-3.20, radius_m=500)
        assert result is not None
        assert "xmin" in result

    def test_lat_lon_without_radius(self):
        result = ScotlandAdapter._build_geometry(lat=55.95, lon=-3.20)
        assert result is None


# ============================================================================
# Normalize NRHE Feature
# ============================================================================


class TestNormalizeNRHEFeature:
    def setup_method(self):
        with patch("chuk_mcp_her.core.adapters.scotland.ArcGISClient"):
            self.adapter = ScotlandAdapter()

    def test_point_feature(self):
        feature = _make_nrhe_point_feature()
        result = self.adapter._normalize_nrhe_feature(feature)
        assert result["record_id"] == "scotland:12345"
        assert result["canmore_id"] == "12345"
        assert result["name"] == "Edinburgh Castle"
        assert result["source"] == "scotland"
        assert result["site_type"] == "CASTLE"
        assert result["easting"] is not None
        assert result["lat"] is not None

    def test_no_geometry_uses_xcoord(self):
        feature = {
            "type": "Feature",
            "properties": {
                "CANMOREID": "99999",
                "NMRSNAME": "Test Site",
                "XCOORD": 300000.0,
                "YCOORD": 700000.0,
            },
            "geometry": None,
        }
        result = self.adapter._normalize_nrhe_feature(feature)
        assert result["easting"] == 300000.0
        assert result["northing"] == 700000.0
        assert result["lat"] is not None

    def test_missing_all_coords(self):
        feature = {
            "type": "Feature",
            "properties": {"CANMOREID": "88888", "NMRSNAME": "No location"},
            "geometry": None,
        }
        result = self.adapter._normalize_nrhe_feature(feature)
        assert "easting" not in result
        assert "lat" not in result

    def test_fields_mapped(self):
        feature = _make_nrhe_point_feature()
        result = self.adapter._normalize_nrhe_feature(feature)
        assert result["broad_class"] == "SECULAR"
        assert result["county"] == "Midlothian"
        assert result["council"] == "City of Edinburgh"
        assert result["parish"] == "Edinburgh"
        assert result["grid_reference"] == "NT 2520 7348"
        assert result["url"] is not None


# ============================================================================
# Normalize Designation Feature
# ============================================================================


class TestNormalizeDesignationFeature:
    def setup_method(self):
        with patch("chuk_mcp_her.core.adapters.scotland.ArcGISClient"):
            self.adapter = ScotlandAdapter()

    def test_listed_building(self):
        feature = _make_designation_feature()
        result = self.adapter._normalize_designation_feature(feature, 0)
        assert result["record_id"] == "scotland_des:LB12345"
        assert result["designation_reference"] == "LB12345"
        assert result["name"] == "St Giles Cathedral"
        assert result["designation_type"] == "listed_building"
        assert result["category"] == "A"
        assert result["local_authority"] == "City of Edinburgh"
        assert result["easting"] is not None
        assert result["lat"] is not None

    def test_scheduled_monument_layer(self):
        feature = _make_designation_feature(des_ref="SM9999")
        result = self.adapter._normalize_designation_feature(feature, 5)
        assert result["designation_type"] == "scheduled_monument"

    def test_battlefield_layer(self):
        feature = _make_designation_feature(des_ref="BTL001")
        result = self.adapter._normalize_designation_feature(feature, 3)
        assert result["designation_type"] == "battlefield"


# ============================================================================
# Search (NRHE)
# ============================================================================


class TestSearch:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.scotland.ArcGISClient") as mock_cls:
            self.mock_nrhe_client = MagicMock()
            self.mock_des_client = MagicMock()
            mock_cls.side_effect = [self.mock_nrhe_client, self.mock_des_client]
            self.adapter = ScotlandAdapter()

    async def test_search_basic(self):
        self.mock_nrhe_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search()
        assert isinstance(result, PaginatedResult)
        assert len(result.features) == 2

    async def test_search_with_name(self):
        self.mock_nrhe_client.query = AsyncMock(return_value=_make_query_response())
        await self.adapter.search(query="Castle")
        call_kwargs = self.mock_nrhe_client.query.call_args[1]
        assert "Castle" in call_kwargs["where"]

    async def test_search_with_bbox(self):
        self.mock_nrhe_client.query = AsyncMock(return_value=_make_query_response())
        await self.adapter.search(bbox=(325000, 673000, 326000, 674000))
        call_kwargs = self.mock_nrhe_client.query.call_args[1]
        assert call_kwargs["geometry"] is not None

    async def test_search_with_site_type(self):
        self.mock_nrhe_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_SCOTLAND_NRHE_ARCGIS_GEOJSON["features"][0]])
        )
        await self.adapter.search(site_type="CASTLE")
        call_kwargs = self.mock_nrhe_client.query.call_args[1]
        assert "CASTLE" in call_kwargs["where"]

    async def test_search_empty(self):
        self.mock_nrhe_client.query = AsyncMock(return_value=_make_query_response([]))
        result = await self.adapter.search()
        assert len(result.features) == 0
        assert result.has_more is False

    async def test_search_has_more_when_full(self):
        # When returned features == max_results, has_more should be True
        self.mock_nrhe_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search(max_results=2)
        assert result.has_more is True

    async def test_search_no_pagination_offset(self):
        # MapServer doesn't support offset — next_offset should be None
        self.mock_nrhe_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search()
        assert result.next_offset is None


# ============================================================================
# Search Designations
# ============================================================================


class TestSearchDesignations:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.scotland.ArcGISClient") as mock_cls:
            self.mock_nrhe_client = MagicMock()
            self.mock_des_client = MagicMock()
            mock_cls.side_effect = [self.mock_nrhe_client, self.mock_des_client]
            self.adapter = ScotlandAdapter()

    async def test_search_all_types(self):
        self.mock_des_client.query = AsyncMock(return_value=_make_designation_query_response())
        result = await self.adapter.search_designations()
        assert isinstance(result, PaginatedResult)
        # Queries all 7 designation layers
        assert self.mock_des_client.query.call_count == 7

    async def test_search_single_type(self):
        self.mock_des_client.query = AsyncMock(return_value=_make_designation_query_response())
        await self.adapter.search_designations(designation_type="listed_building")
        # Only queries listed_building layer (layer 0)
        assert self.mock_des_client.query.call_count == 1
        call_kwargs = self.mock_des_client.query.call_args[1]
        assert call_kwargs["layer_id"] == 0

    async def test_search_with_name(self):
        self.mock_des_client.query = AsyncMock(return_value=_make_designation_query_response())
        await self.adapter.search_designations(query="Cathedral")
        call_kwargs = self.mock_des_client.query.call_args[1]
        assert "Cathedral" in call_kwargs["where"]

    async def test_search_with_bbox(self):
        self.mock_des_client.query = AsyncMock(return_value=_make_designation_query_response())
        await self.adapter.search_designations(bbox=(325000, 673000, 326000, 674000))
        call_kwargs = self.mock_des_client.query.call_args[1]
        assert call_kwargs["geometry"] is not None


# ============================================================================
# Get By ID
# ============================================================================


class TestGetById:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.scotland.ArcGISClient") as mock_cls:
            self.mock_nrhe_client = MagicMock()
            self.mock_des_client = MagicMock()
            mock_cls.side_effect = [self.mock_nrhe_client, self.mock_des_client]
            self.adapter = ScotlandAdapter()

    async def test_found_in_terrestrial(self):
        self.mock_nrhe_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_SCOTLAND_NRHE_ARCGIS_GEOJSON["features"][0]])
        )
        result = await self.adapter.get_by_id("scotland:12345")
        assert result is not None
        assert result["canmore_id"] == "12345"

    async def test_prefix_stripping(self):
        self.mock_nrhe_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_SCOTLAND_NRHE_ARCGIS_GEOJSON["features"][0]])
        )
        await self.adapter.get_by_id("scotland:12345")
        call_kwargs = self.mock_nrhe_client.query.call_args[1]
        assert "12345" in call_kwargs["where"]
        assert "scotland:" not in call_kwargs["where"]

    async def test_not_found(self):
        self.mock_nrhe_client.query = AsyncMock(return_value=_make_query_response([]))
        result = await self.adapter.get_by_id("scotland:MISSING")
        assert result is None

    async def test_fallthrough_to_maritime(self):
        call_count = 0

        async def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_query_response([])
            return _make_query_response([SAMPLE_SCOTLAND_NRHE_ARCGIS_GEOJSON["features"][0]])

        self.mock_nrhe_client.query = AsyncMock(side_effect=mock_query)
        result = await self.adapter.get_by_id("scotland:12345")
        assert result is not None
        assert call_count == 2


# ============================================================================
# Extract Coordinates
# ============================================================================


class TestExtractCoordinates:
    def test_point_geometry(self):
        geom = {"type": "Point", "coordinates": [325200.0, 673480.0]}
        e, n, lat, lon = ScotlandAdapter._extract_coordinates(geom, {})
        assert abs(e - 325200.0) < 1.0
        assert abs(n - 673480.0) < 1.0
        assert lat is not None
        assert lon is not None

    def test_xcoord_ycoord_fallback(self):
        e, n, lat, lon = ScotlandAdapter._extract_coordinates(
            None, {"XCOORD": 300000.0, "YCOORD": 700000.0}
        )
        assert e == 300000.0
        assert n == 700000.0
        assert lat is not None

    def test_no_coordinates(self):
        e, n, lat, lon = ScotlandAdapter._extract_coordinates(None, {})
        assert e is None
        assert n is None
        assert lat is None
        assert lon is None

    def test_polygon_centroid(self):
        geom = {
            "type": "Polygon",
            "coordinates": [
                [
                    [325000.0, 673000.0],
                    [326000.0, 673000.0],
                    [326000.0, 674000.0],
                    [325000.0, 674000.0],
                    [325000.0, 673000.0],
                ]
            ],
        }
        e, n, lat, lon = ScotlandAdapter._extract_coordinates(geom, {})
        assert abs(e - 325400.0) < 200.0  # Centroid of ring including closing point
        assert abs(n - 673400.0) < 200.0
