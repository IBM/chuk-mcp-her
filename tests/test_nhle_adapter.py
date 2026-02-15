"""Tests for chuk_mcp_her.core.adapters.nhle."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from chuk_mcp_her.constants import (
    ALL_NHLE_POINT_LAYERS,
    NHLELayer,
)
from chuk_mcp_her.core.adapters.nhle import NHLEAdapter

# Sample ArcGIS GeoJSON response for search results
SAMPLE_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "ListEntry": "1000001",
                "Name": "Church of St Mary",
                "Grade": "I",
                "ListDate": "1967-01-01",
                "HyperLink": "https://historicengland.org.uk/listing/the-list/list-entry/1000001",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [533500.0, 180500.0],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "ListEntry": "1000002",
                "Name": "Red Hill 200m NE of Bounds Farm",
                "Grade": None,
                "ListDate": "1978-03-15",
                "AmendDate": "2002-11-01",
                "HyperLink": "https://historicengland.org.uk/listing/the-list/list-entry/1000002",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [590625.0, 208193.0],
            },
        },
    ],
}


@pytest.fixture
def mock_arcgis_client():
    """Create a mock ArcGISClient."""
    client = AsyncMock()
    client.query = AsyncMock(return_value=SAMPLE_GEOJSON)
    client.count = AsyncMock(return_value=2)
    client.close = AsyncMock()
    return client


@pytest.fixture
def adapter(mock_arcgis_client):
    """Create an NHLEAdapter with a mocked ArcGIS client."""
    adapter = NHLEAdapter.__new__(NHLEAdapter)
    adapter._client = mock_arcgis_client
    return adapter


class TestNHLEAdapterSearch:
    async def test_search_with_text_query(self, adapter, mock_arcgis_client):
        result = await adapter.search(query="Church", designation_type="scheduled_monument")
        assert len(result.features) == 2
        assert result.total_count == 2
        # Verify count and query were called
        assert mock_arcgis_client.count.called
        assert mock_arcgis_client.query.called

    async def test_search_with_designation_type(self, adapter, mock_arcgis_client):
        await adapter.search(designation_type="scheduled_monument")
        # Should query only scheduled monuments layer
        query_call = mock_arcgis_client.query.call_args
        assert query_call[1]["layer_id"] == NHLELayer.SCHEDULED_MONUMENTS

    async def test_search_with_bbox(self, adapter, mock_arcgis_client):
        bbox = (530000.0, 170000.0, 540000.0, 190000.0)
        await adapter.search(bbox=bbox)
        # Verify geometry was passed
        query_call = mock_arcgis_client.query.call_args
        assert query_call[1]["geometry"] is not None

    async def test_search_with_lat_lon_radius(self, adapter, mock_arcgis_client):
        await adapter.search(lat=51.508, lon=-0.076, radius_m=500)
        # Verify geometry was constructed from lat/lon
        query_call = mock_arcgis_client.query.call_args
        assert query_call[1]["geometry"] is not None

    async def test_search_returns_paginated_result(self, adapter):
        result = await adapter.search(query="Red Hill")
        assert hasattr(result, "features")
        assert hasattr(result, "total_count")
        assert hasattr(result, "has_more")
        assert hasattr(result, "next_offset")

    async def test_search_no_designation_queries_all_layers(self, adapter, mock_arcgis_client):
        """When no designation_type is given, all point layers should be queried."""
        # For multiple layers, count is called for each
        await adapter.search(query="test")
        # Should query count for ALL_NHLE_POINT_LAYERS
        assert mock_arcgis_client.count.call_count >= 1


class TestNHLEAdapterGetById:
    async def test_get_by_id_found(self, adapter, mock_arcgis_client):
        # Return a single feature
        mock_arcgis_client.query.return_value = {
            "type": "FeatureCollection",
            "features": [SAMPLE_GEOJSON["features"][0]],
        }
        result = await adapter.get_by_id("1000001")
        assert result is not None
        assert result["nhle_id"] == "1000001"
        assert result["name"] == "Church of St Mary"

    async def test_get_by_id_with_prefix(self, adapter, mock_arcgis_client):
        """get_by_id should strip the 'nhle:' prefix."""
        mock_arcgis_client.query.return_value = {
            "type": "FeatureCollection",
            "features": [SAMPLE_GEOJSON["features"][0]],
        }
        await adapter.get_by_id("nhle:1000001")
        # Verify the WHERE clause used the stripped ID
        first_call = mock_arcgis_client.query.call_args_list[0]
        assert "1000001" in first_call[1]["where"]
        assert "nhle:" not in first_call[1]["where"]

    async def test_get_by_id_not_found(self, adapter, mock_arcgis_client):
        mock_arcgis_client.query.return_value = {
            "type": "FeatureCollection",
            "features": [],
        }
        result = await adapter.get_by_id("9999999")
        assert result is None


class TestNHLEAdapterBuildWhere:
    @pytest.fixture
    def adapter_instance(self):
        """Create a minimal adapter for testing private methods."""
        adapter = NHLEAdapter.__new__(NHLEAdapter)
        adapter._client = MagicMock()
        return adapter

    def test_no_filters(self, adapter_instance):
        where = adapter_instance._build_where()
        assert where == "1=1"

    def test_query_only(self, adapter_instance):
        where = adapter_instance._build_where(query="red hill")
        assert "Name LIKE '%red hill%'" in where

    def test_grade_only(self, adapter_instance):
        where = adapter_instance._build_where(grade="I")
        assert "Grade = 'I'" in where

    def test_query_and_grade(self, adapter_instance):
        where = adapter_instance._build_where(query="Church", grade="II*")
        assert "Name LIKE '%Church%'" in where
        assert "Grade = 'II*'" in where
        assert " AND " in where

    def test_query_escapes_quotes(self, adapter_instance):
        where = adapter_instance._build_where(query="St Mary's")
        assert "St Mary''s" in where


class TestNHLEAdapterNormalizeFeature:
    @pytest.fixture
    def adapter_instance(self):
        adapter = NHLEAdapter.__new__(NHLEAdapter)
        adapter._client = MagicMock()
        return adapter

    def test_normalize_point_feature(self, adapter_instance):
        feature = {
            "properties": {
                "ListEntry": "1000001",
                "Name": "Test Building",
                "Grade": "II",
                "ListDate": "1987-01-01",
                "HyperLink": "https://example.com/1000001",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [533500.0, 180500.0],
            },
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.LISTED_BUILDING_POINTS)
        assert result["record_id"] == "nhle:1000001"
        assert result["nhle_id"] == "1000001"
        assert result["name"] == "Test Building"
        assert result["source"] == "nhle"
        assert result["designation_type"] == "listed_building"
        assert result["grade"] == "II"
        assert result["easting"] == 533500.0
        assert result["northing"] == 180500.0
        assert result["lat"] is not None
        assert result["lon"] is not None
        assert result["url"] == "https://example.com/1000001"

    def test_normalize_scheduled_monument(self, adapter_instance):
        feature = {
            "properties": {
                "ListEntry": "1000002",
                "Name": "Red Hill",
                "Grade": None,
                "ListDate": "1978-03-15",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [590625.0, 208193.0],
            },
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.SCHEDULED_MONUMENTS)
        assert result["designation_type"] == "scheduled_monument"
        assert result["grade"] is None

    def test_normalize_feature_without_geometry(self, adapter_instance):
        feature = {
            "properties": {
                "ListEntry": "1000003",
                "Name": "No Geometry Asset",
            },
            "geometry": None,
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.BATTLEFIELDS)
        assert result["record_id"] == "nhle:1000003"
        assert "easting" not in result
        assert "lat" not in result

    def test_normalize_feature_with_ngr(self, adapter_instance):
        feature = {
            "properties": {
                "ListEntry": "1000004",
                "Name": "With NGR",
                "NGR": "TQ 335 805",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [533500.0, 180500.0],
            },
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.LISTED_BUILDING_POINTS)
        assert result["ngr"] == "TQ 335 805"

    def test_normalize_feature_lowercase_keys(self, adapter_instance):
        """Adapter handles both uppercase and lowercase field names."""
        feature = {
            "properties": {
                "list_entry": "1000005",
                "name": "Lowercase Test",
                "grade": "I",
                "hyperlink": "https://example.com",
            },
            "geometry": {
                "type": "Point",
                "coordinates": [533500.0, 180500.0],
            },
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.LISTED_BUILDING_POINTS)
        assert result["nhle_id"] == "1000005"
        assert result["name"] == "Lowercase Test"
        assert result["grade"] == "I"


class TestNHLEAdapterCount:
    async def test_count_single_designation(self, adapter, mock_arcgis_client):
        mock_arcgis_client.count.return_value = 42
        result = await adapter.count(designation_type="scheduled_monument")
        assert result == 42

    async def test_count_with_bbox(self, adapter, mock_arcgis_client):
        mock_arcgis_client.count.return_value = 10
        result = await adapter.count(
            bbox=(530000, 170000, 540000, 190000),
            designation_type="listed_building",
        )
        assert result == 10


class TestNHLEAdapterProperties:
    def test_source_id(self, adapter):
        assert adapter.source_id == "nhle"

    def test_capabilities(self, adapter):
        caps = adapter.capabilities
        assert caps.supports_spatial_query is True
        assert caps.supports_text_search is True
        assert caps.supports_feature_count is True
        assert caps.supports_attribute_filter is True
        assert caps.supports_pagination is True
        assert "listed_building" in caps.supported_designation_types
        assert "scheduled_monument" in caps.supported_designation_types


class TestNHLEAdapterClose:
    async def test_close_delegates(self, adapter, mock_arcgis_client):
        await adapter.close()
        mock_arcgis_client.close.assert_called_once()


class TestNHLEEpochMsToDate:
    def test_epoch_ms_integer(self):
        """Numeric epoch-ms should be converted to ISO date."""
        # 2024-01-01 00:00:00 UTC = 1704067200000 ms
        result = NHLEAdapter._epoch_ms_to_date(1704067200000)
        assert result == "2024-01-01"

    def test_epoch_zero(self):
        """Epoch 0 = 1970-01-01."""
        result = NHLEAdapter._epoch_ms_to_date(0)
        assert result == "1970-01-01"

    def test_invalid_value_returns_string(self):
        """Non-convertible value should be returned as string."""
        result = NHLEAdapter._epoch_ms_to_date([1, 2, 3])
        assert result == "[1, 2, 3]"


class TestNHLEMultiLayerSearch:
    """Test the multi-layer search path (no designation_type)."""

    async def test_gather_exception_ignored_in_total_count(self):
        """Exceptions in parallel count gather should be skipped."""
        adapter = NHLEAdapter.__new__(NHLEAdapter)
        mock_client = AsyncMock()
        adapter._client = mock_client

        num_layers = len(ALL_NHLE_POINT_LAYERS)

        # side_effect: first num_layers calls for parallel gather,
        # then more calls for sequential per-layer counts and queries
        gather_effects = [5] * num_layers
        gather_effects[2] = Exception("simulated timeout")
        sequential_effects = [5] * (num_layers * 2)  # Extra for safety
        mock_client.count = AsyncMock(side_effect=gather_effects + sequential_effects)
        mock_client.query = AsyncMock(
            return_value={
                "features": [{"properties": {"ListEntry": "1", "Name": "Test"}, "geometry": None}]
            }
        )

        result = await adapter.search(query="test", max_results=1)
        # total_count = 5 * (num_layers - 1) = 25
        assert result.total_count == 5 * (num_layers - 1)

    async def test_offset_skips_layers(self):
        """Offset exceeding a layer's count should skip to next layer."""
        adapter = NHLEAdapter.__new__(NHLEAdapter)
        mock_client = AsyncMock()
        adapter._client = mock_client

        num_layers = len(ALL_NHLE_POINT_LAYERS)

        # Each layer has 3 features
        mock_client.count = AsyncMock(return_value=3)
        mock_client.query = AsyncMock(
            return_value={
                "features": [{"properties": {"ListEntry": "1", "Name": "A"}, "geometry": None}]
            }
        )

        # offset=5: skip layer 0 (3 features), start at offset 2 in layer 1
        result = await adapter.search(query="test", offset=5, max_results=1)
        assert result.total_count == 3 * num_layers
        assert len(result.features) == 1

    async def test_remaining_results_exhausted(self):
        """Search should stop once max_results features are collected."""
        adapter = NHLEAdapter.__new__(NHLEAdapter)
        mock_client = AsyncMock()
        adapter._client = mock_client

        mock_client.count = AsyncMock(return_value=10)
        mock_client.query = AsyncMock(
            return_value={
                "features": [
                    {"properties": {"ListEntry": "1", "Name": "A"}, "geometry": None},
                    {"properties": {"ListEntry": "2", "Name": "B"}, "geometry": None},
                ]
            }
        )

        result = await adapter.search(query="test", max_results=2)
        assert len(result.features) == 2


class TestNHLEMultiLayerCount:
    async def test_count_multi_layer_with_exception(self):
        """count() with no designation_type should sum across layers, skipping exceptions."""
        adapter = NHLEAdapter.__new__(NHLEAdapter)
        mock_client = AsyncMock()
        adapter._client = mock_client

        num_layers = len(ALL_NHLE_POINT_LAYERS)
        count_values = [10] * num_layers
        count_values[1] = Exception("fail")
        mock_client.count = AsyncMock(side_effect=count_values)

        result = await adapter.count()
        assert result == 10 * (num_layers - 1)


class TestNHLEGeometryNormalization:
    """Test Polygon and MultiPolygon geometry handling."""

    @pytest.fixture
    def adapter_instance(self):
        adapter = NHLEAdapter.__new__(NHLEAdapter)
        adapter._client = MagicMock()
        return adapter

    def test_polygon_geometry(self, adapter_instance):
        """Polygon geometry should use centroid of first ring."""
        feature = {
            "properties": {"ListEntry": "100", "Name": "Polygon Test"},
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [530000.0, 170000.0],
                        [540000.0, 170000.0],
                        [540000.0, 180000.0],
                        [530000.0, 180000.0],
                        [530000.0, 170000.0],
                    ]
                ],
            },
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.BATTLEFIELDS)
        assert result["easting"] == 534000.0
        assert result["northing"] == 174000.0
        assert result["lat"] is not None

    def test_multipolygon_geometry(self, adapter_instance):
        """MultiPolygon geometry should use centroid of first ring of first polygon."""
        feature = {
            "properties": {"ListEntry": "200", "Name": "MultiPolygon Test"},
            "geometry": {
                "type": "MultiPolygon",
                "coordinates": [
                    [
                        [
                            [520000.0, 160000.0],
                            [530000.0, 160000.0],
                            [530000.0, 170000.0],
                            [520000.0, 170000.0],
                            [520000.0, 160000.0],
                        ]
                    ]
                ],
            },
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.WORLD_HERITAGE_SITES)
        assert result["easting"] == 524000.0
        assert result["northing"] == 164000.0

    def test_multipoint_geometry(self, adapter_instance):
        """MultiPoint geometry should use first point."""
        feature = {
            "properties": {"ListEntry": "300", "Name": "MultiPoint Test"},
            "geometry": {
                "type": "MultiPoint",
                "coordinates": [[533500.0, 180500.0], [534000.0, 181000.0]],
            },
        }
        result = adapter_instance._normalize_feature(feature, NHLELayer.LISTED_BUILDING_POINTS)
        assert result["easting"] == 533500.0
        assert result["northing"] == 180500.0
