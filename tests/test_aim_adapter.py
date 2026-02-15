"""Tests for chuk_mcp_her.core.adapters.aim — AIM adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chuk_mcp_her.core.adapters.aim import AIMAdapter
from chuk_mcp_her.core.adapters.base import PaginatedResult

from tests.conftest import SAMPLE_AIM_ARCGIS_GEOJSON


# ============================================================================
# Helpers
# ============================================================================


def _make_polygon_feature(
    he_uid: str = "AIM001",
    monument_type: str = "ENCLOSURE",
    period: str = "IRON AGE",
    coords: list | None = None,
) -> dict:
    """Build a minimal AIM ArcGIS GeoJSON feature."""
    if coords is None:
        coords = [
            [
                [594400.0, 209900.0],
                [594600.0, 209900.0],
                [594600.0, 210100.0],
                [594400.0, 210100.0],
                [594400.0, 209900.0],
            ]
        ]
    return {
        "type": "Feature",
        "properties": {
            "HE_UID": he_uid,
            "MONUMENT_TYPE": monument_type,
            "PERIOD": period,
            "FORM": "Cropmark",
            "EVIDENCE_1": "Cropmark",
            "PROJECT": "Essex NMP",
            "HER_NO": "HER001",
            "BROAD_TYPE": "ENCLOSURE",
            "NARROW_TYPE": "ENCLOSURE: OVAL",
        },
        "geometry": {"type": "Polygon", "coordinates": coords},
    }


def _make_count_response(count: int = 42) -> dict:
    return {"count": count}


def _make_query_response(features: list | None = None) -> dict:
    if features is None:
        features = SAMPLE_AIM_ARCGIS_GEOJSON["features"]
    return {"type": "FeatureCollection", "features": features}


# ============================================================================
# Properties
# ============================================================================


class TestAIMAdapterProperties:
    def test_source_id(self):
        with patch("chuk_mcp_her.core.adapters.aim.ArcGISClient"):
            adapter = AIMAdapter()
        assert adapter.source_id == "aim"

    def test_capabilities(self):
        with patch("chuk_mcp_her.core.adapters.aim.ArcGISClient"):
            adapter = AIMAdapter()
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
        assert AIMAdapter._build_where() == "1=1"

    def test_query_only(self):
        result = AIMAdapter._build_where(query="ENCLOSURE")
        assert "MONUMENT_TYPE LIKE '%ENCLOSURE%'" in result

    def test_monument_type_only(self):
        result = AIMAdapter._build_where(monument_type="MOUND")
        assert "MONUMENT_TYPE LIKE '%MOUND%'" in result

    def test_period_only(self):
        result = AIMAdapter._build_where(period="ROMAN")
        assert "PERIOD LIKE '%ROMAN%'" in result

    def test_combined_filters(self):
        result = AIMAdapter._build_where(monument_type="ENCLOSURE", period="IRON AGE")
        assert "MONUMENT_TYPE LIKE '%ENCLOSURE%'" in result
        assert "PERIOD LIKE '%IRON AGE%'" in result
        assert " AND " in result

    def test_escaping(self):
        result = AIMAdapter._build_where(query="O'Brien")
        assert "O''Brien" in result

    def test_query_and_monument_type_combined(self):
        result = AIMAdapter._build_where(query="MOUND", monument_type="SALTERN")
        # Both produce MONUMENT_TYPE LIKE clauses
        assert result.count("MONUMENT_TYPE LIKE") == 2


# ============================================================================
# Build Geometry
# ============================================================================


class TestBuildGeometry:
    def test_no_params(self):
        assert AIMAdapter._build_geometry() is None

    def test_bbox(self):
        result = AIMAdapter._build_geometry(bbox=(586000, 205000, 602500, 215000))
        assert result == {
            "xmin": 586000,
            "ymin": 205000,
            "xmax": 602500,
            "ymax": 215000,
        }

    def test_lat_lon_radius(self):
        result = AIMAdapter._build_geometry(lat=51.77, lon=0.87, radius_m=500)
        assert result is not None
        assert "xmin" in result
        assert "ymin" in result
        assert "xmax" in result
        assert "ymax" in result

    def test_lat_lon_without_radius(self):
        result = AIMAdapter._build_geometry(lat=51.77, lon=0.87)
        assert result is None


# ============================================================================
# Build Name
# ============================================================================


class TestBuildName:
    def test_both_fields(self):
        assert (
            AIMAdapter._build_name({"MONUMENT_TYPE": "ENCLOSURE", "PERIOD": "IRON AGE"})
            == "ENCLOSURE (IRON AGE)"
        )

    def test_monument_only(self):
        assert AIMAdapter._build_name({"MONUMENT_TYPE": "MOUND", "PERIOD": None}) == "MOUND"

    def test_period_only(self):
        assert AIMAdapter._build_name({"MONUMENT_TYPE": None, "PERIOD": "ROMAN"}) == "ROMAN"

    def test_empty(self):
        assert AIMAdapter._build_name({}) == "Unknown feature"


# ============================================================================
# Normalize Feature
# ============================================================================


class TestNormalizeFeature:
    def setup_method(self):
        with patch("chuk_mcp_her.core.adapters.aim.ArcGISClient"):
            self.adapter = AIMAdapter()

    def test_polygon_centroid(self):
        feature = _make_polygon_feature()
        result = self.adapter._normalize_feature(feature)
        assert result["easting"] is not None
        assert result["northing"] is not None
        assert result["lat"] is not None
        assert result["lon"] is not None
        # Ring average includes closing point (same as first) so centroid
        # is biased slightly — use loose tolerance
        assert abs(result["easting"] - 594500.0) < 50.0
        assert abs(result["northing"] - 210000.0) < 50.0

    def test_multipolygon(self):
        feature = {
            "type": "Feature",
            "properties": {
                "HE_UID": "AIM003",
                "MONUMENT_TYPE": "FIELD SYSTEM",
                "PERIOD": "MEDIEVAL",
            },
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [594400.0, 209900.0],
                            [594600.0, 209900.0],
                            [594600.0, 210100.0],
                            [594400.0, 210100.0],
                            [594400.0, 209900.0],
                        ]
                    ]
                ],
            },
        }
        result = self.adapter._normalize_feature(feature)
        assert result["easting"] is not None
        assert abs(result["easting"] - 594500.0) < 50.0

    def test_no_geometry(self):
        feature = {
            "type": "Feature",
            "properties": {
                "HE_UID": "AIM004",
                "MONUMENT_TYPE": "MOUND",
                "PERIOD": "UNKNOWN",
            },
            "geometry": None,
        }
        result = self.adapter._normalize_feature(feature)
        assert "easting" not in result
        assert "lat" not in result
        assert result["record_id"] == "aim:AIM004"

    def test_point_geometry(self):
        feature = {
            "type": "Feature",
            "properties": {
                "HE_UID": "AIM005",
                "MONUMENT_TYPE": "RING DITCH",
                "PERIOD": "BRONZE AGE",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [594500.0, 210000.0],
            },
        }
        result = self.adapter._normalize_feature(feature)
        assert abs(result["easting"] - 594500.0) < 1.0

    def test_he_uid_mapping(self):
        feature = _make_polygon_feature(he_uid="TEST123")
        result = self.adapter._normalize_feature(feature)
        assert result["record_id"] == "aim:TEST123"
        assert result["aim_id"] == "TEST123"

    def test_name_built(self):
        feature = _make_polygon_feature(monument_type="SALTERN MOUND", period="ROMAN")
        result = self.adapter._normalize_feature(feature)
        assert result["name"] == "SALTERN MOUND (ROMAN)"

    def test_fields_mapped(self):
        feature = _make_polygon_feature()
        result = self.adapter._normalize_feature(feature)
        assert result["source"] == "aim"
        assert result["monument_type"] == "ENCLOSURE"
        assert result["period"] == "IRON AGE"
        assert result["form"] == "Cropmark"
        assert result["evidence"] == "Cropmark"
        assert result["project"] == "Essex NMP"
        assert result["her_no"] == "HER001"

    def test_null_fields(self):
        feature = {
            "type": "Feature",
            "properties": {"OBJECTID": 999},
            "geometry": None,
        }
        result = self.adapter._normalize_feature(feature)
        assert result["record_id"] == "aim:999"
        assert result["monument_type"] is None
        assert result["period"] is None
        assert result["name"] == "Unknown feature"


# ============================================================================
# Search
# ============================================================================


class TestSearch:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.aim.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = AIMAdapter()

    async def test_search_basic(self):
        self.mock_client.count = AsyncMock(return_value=2)
        self.mock_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search()
        assert isinstance(result, PaginatedResult)
        assert len(result.features) == 2
        assert result.total_count == 2
        assert result.has_more is False

    async def test_search_with_bbox(self):
        self.mock_client.count = AsyncMock(return_value=2)
        self.mock_client.query = AsyncMock(return_value=_make_query_response())
        result = await self.adapter.search(bbox=(586000, 205000, 602500, 215000))
        assert len(result.features) == 2
        # Verify geometry was passed
        call_kwargs = self.mock_client.query.call_args[1]
        assert call_kwargs["geometry"] is not None

    async def test_search_with_monument_type(self):
        self.mock_client.count = AsyncMock(return_value=1)
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_AIM_ARCGIS_GEOJSON["features"][0]])
        )
        result = await self.adapter.search(monument_type="ENCLOSURE")
        assert len(result.features) == 1
        call_kwargs = self.mock_client.query.call_args[1]
        assert "ENCLOSURE" in call_kwargs["where"]

    async def test_search_with_period(self):
        self.mock_client.count = AsyncMock(return_value=1)
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_AIM_ARCGIS_GEOJSON["features"][1]])
        )
        result = await self.adapter.search(period="ROMAN")
        assert len(result.features) == 1
        call_kwargs = self.mock_client.query.call_args[1]
        assert "ROMAN" in call_kwargs["where"]

    async def test_search_empty(self):
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

    async def test_search_combined_filters(self):
        self.mock_client.count = AsyncMock(return_value=1)
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_AIM_ARCGIS_GEOJSON["features"][0]])
        )
        await self.adapter.search(
            bbox=(586000, 205000, 602500, 215000),
            monument_type="ENCLOSURE",
            period="IRON AGE",
        )
        call_kwargs = self.mock_client.query.call_args[1]
        assert "ENCLOSURE" in call_kwargs["where"]
        assert "IRON AGE" in call_kwargs["where"]
        assert call_kwargs["geometry"] is not None


# ============================================================================
# Get By ID
# ============================================================================


class TestGetById:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.aim.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = AIMAdapter()

    async def test_found_in_layer_1(self):
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_AIM_ARCGIS_GEOJSON["features"][0]])
        )
        result = await self.adapter.get_by_id("aim:AIM001")
        assert result is not None
        assert result["aim_id"] == "AIM001"

    async def test_prefix_stripping(self):
        self.mock_client.query = AsyncMock(
            return_value=_make_query_response([SAMPLE_AIM_ARCGIS_GEOJSON["features"][0]])
        )
        await self.adapter.get_by_id("aim:AIM001")
        call_kwargs = self.mock_client.query.call_args[1]
        assert "AIM001" in call_kwargs["where"]
        assert "aim:" not in call_kwargs["where"]

    async def test_not_found(self):
        self.mock_client.query = AsyncMock(return_value=_make_query_response([]))
        result = await self.adapter.get_by_id("aim:MISSING")
        assert result is None

    async def test_fallthrough_to_layer_2(self):
        # Layer 1 returns nothing, layer 2 has it
        call_count = 0

        async def mock_query(**kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_query_response([])
            return _make_query_response([SAMPLE_AIM_ARCGIS_GEOJSON["features"][0]])

        self.mock_client.query = AsyncMock(side_effect=mock_query)
        result = await self.adapter.get_by_id("aim:AIM001")
        assert result is not None
        assert call_count == 2


# ============================================================================
# Count
# ============================================================================


class TestCount:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.aim.ArcGISClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = AIMAdapter()

    async def test_count_basic(self):
        self.mock_client.count = AsyncMock(return_value=42)
        result = await self.adapter.count()
        assert result == 42

    async def test_count_with_bbox(self):
        self.mock_client.count = AsyncMock(return_value=10)
        result = await self.adapter.count(bbox=(586000, 205000, 602500, 215000))
        assert result == 10
        call_kwargs = self.mock_client.count.call_args[1]
        assert call_kwargs["geometry"] is not None

    async def test_count_with_filters(self):
        self.mock_client.count = AsyncMock(return_value=5)
        result = await self.adapter.count(monument_type="MOUND", period="ROMAN")
        assert result == 5
        call_kwargs = self.mock_client.count.call_args[1]
        assert "MOUND" in call_kwargs["where"]
        assert "ROMAN" in call_kwargs["where"]
