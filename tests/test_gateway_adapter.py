"""Tests for chuk_mcp_her.core.adapters.heritage_gateway — Heritage Gateway adapter."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chuk_mcp_her.core.adapters.base import PaginatedResult
from chuk_mcp_her.core.adapters.heritage_gateway import HeritageGatewayAdapter


# ============================================================================
# Sample data
# ============================================================================

SAMPLE_CLIENT_SEARCH_RESULT = {
    "records": [
        {
            "name": "Red Hill, Goldhanger",
            "record_id": "MEX1001",
            "monument_type": "Red Hill",
            "period": "Roman",
            "description": "A red hill mound indicating salt production",
            "grid_reference": "TL 9050 0850",
            "easting": 590500.0,
            "northing": 208500.0,
            "source_her": "Essex HER",
            "designation": None,
            "url": "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001",
        },
        {
            "name": "Saltern mound, Tollesbury",
            "record_id": "MEX1002",
            "monument_type": "Saltern",
            "period": "Iron Age",
            "description": "Remains of salt production site",
            "grid_reference": "TL 9610 1185",
            "easting": 596100.0,
            "northing": 211850.0,
            "source_her": "Essex HER",
            "designation": None,
            "url": "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1002",
        },
    ],
    "total_count": 2,
    "has_more": False,
}

SAMPLE_CLIENT_DETAIL_RESULT = {
    "name": "Red Hill, Goldhanger",
    "record_id": "MEX1001",
    "monument_type": "Red Hill",
    "period": "Roman",
    "description": "A red hill mound indicating salt production",
    "grid_reference": "TL 9050 0850",
    "easting": 590500.0,
    "northing": 208500.0,
    "source_her": "Essex HER",
    "designation": None,
    "url": "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001",
}


# ============================================================================
# TestHeritageGatewayAdapterProperties
# ============================================================================


class TestHeritageGatewayAdapterProperties:
    def test_source_id(self):
        with patch("chuk_mcp_her.core.adapters.heritage_gateway.GatewayClient"):
            adapter = HeritageGatewayAdapter()
        assert adapter.source_id == "heritage_gateway"

    def test_capabilities_text_search(self):
        with patch("chuk_mcp_her.core.adapters.heritage_gateway.GatewayClient"):
            adapter = HeritageGatewayAdapter()
        cap = adapter.capabilities
        assert cap.supports_text_search is True

    def test_capabilities_no_spatial(self):
        with patch("chuk_mcp_her.core.adapters.heritage_gateway.GatewayClient"):
            adapter = HeritageGatewayAdapter()
        cap = adapter.capabilities
        assert cap.supports_spatial_query is False
        assert cap.supports_feature_count is False
        assert cap.supports_attribute_filter is False
        assert cap.supports_pagination is False


# ============================================================================
# TestHeritageGatewayAdapterSearch
# ============================================================================


class TestHeritageGatewayAdapterSearch:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.heritage_gateway.GatewayClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = HeritageGatewayAdapter()

    async def test_search_delegates_to_client(self):
        self.mock_client.search = AsyncMock(return_value=SAMPLE_CLIENT_SEARCH_RESULT)

        await self.adapter.search(query="red hill")

        self.mock_client.search.assert_called_once_with(
            what="red hill",
            where=None,
            when=None,
            max_results=50,
        )

    async def test_search_normalizes_records(self):
        self.mock_client.search = AsyncMock(return_value=SAMPLE_CLIENT_SEARCH_RESULT)

        result = await self.adapter.search(query="red hill")

        assert isinstance(result, PaginatedResult)
        assert len(result.features) == 2

        rec = result.features[0]
        assert rec["source"] == "heritage_gateway"
        assert rec["record_id"] == "MEX1001"
        assert rec["name"] == "Red Hill, Goldhanger"
        assert rec["monument_type"] == "Red Hill"
        assert rec["period"] == "Roman"
        assert rec["easting"] == 590500.0
        assert rec["northing"] == 208500.0
        assert rec["source_her"] == "Essex HER"
        assert rec["url"] is not None

    async def test_search_with_what_where_when(self):
        self.mock_client.search = AsyncMock(return_value=SAMPLE_CLIENT_SEARCH_RESULT)

        await self.adapter.search(
            query="saltern",
            what="saltern mound",
            where="Essex",
            when="Iron Age",
        )

        # 'what' kwarg overrides query
        self.mock_client.search.assert_called_once_with(
            what="saltern mound",
            where="Essex",
            when="Iron Age",
            max_results=50,
        )

    async def test_search_returns_paginated_result(self):
        self.mock_client.search = AsyncMock(return_value=SAMPLE_CLIENT_SEARCH_RESULT)

        result = await self.adapter.search(query="red hill")

        assert isinstance(result, PaginatedResult)
        assert result.total_count == 2
        assert result.has_more is False

    async def test_search_with_offset(self):
        self.mock_client.search = AsyncMock(return_value=SAMPLE_CLIENT_SEARCH_RESULT)

        result = await self.adapter.search(query="red hill", offset=1)

        # Offset 1 means skip first record
        assert len(result.features) == 1
        assert result.features[0]["name"] == "Saltern mound, Tollesbury"

    async def test_search_with_max_results(self):
        self.mock_client.search = AsyncMock(return_value=SAMPLE_CLIENT_SEARCH_RESULT)

        result = await self.adapter.search(query="red hill", max_results=1)

        assert len(result.features) <= 1

    async def test_search_empty_result(self):
        empty_result = {"records": [], "total_count": 0, "has_more": False}
        self.mock_client.search = AsyncMock(return_value=empty_result)

        result = await self.adapter.search(query="nonexistent")

        assert len(result.features) == 0
        assert result.total_count == 0
        assert result.has_more is False

    async def test_search_query_maps_to_what(self):
        """When only query is provided (no 'what' kwarg), it maps to what."""
        self.mock_client.search = AsyncMock(
            return_value={"records": [], "total_count": 0, "has_more": False}
        )

        await self.adapter.search(query="church")

        self.mock_client.search.assert_called_once_with(
            what="church",
            where=None,
            when=None,
            max_results=50,
        )


# ============================================================================
# TestHeritageGatewayAdapterGetById
# ============================================================================


class TestHeritageGatewayAdapterGetById:
    @pytest.fixture(autouse=True)
    def setup(self):
        with patch("chuk_mcp_her.core.adapters.heritage_gateway.GatewayClient") as mock_cls:
            self.mock_client = MagicMock()
            mock_cls.return_value = self.mock_client
            self.adapter = HeritageGatewayAdapter()

    async def test_get_by_id_with_url(self):
        self.mock_client.get_record = AsyncMock(return_value=SAMPLE_CLIENT_DETAIL_RESULT)

        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001"
        result = await self.adapter.get_by_id(url)

        self.mock_client.get_record.assert_called_once_with(url)
        assert result is not None
        assert result["source"] == "heritage_gateway"
        assert result["name"] == "Red Hill, Goldhanger"

    async def test_get_by_id_without_url_returns_none(self):
        result = await self.adapter.get_by_id("MEX1001")
        assert result is None

    async def test_get_by_id_with_hg_prefix_returns_none(self):
        result = await self.adapter.get_by_id("hg:MEX1001")
        assert result is None

    async def test_get_by_id_normalizes_result(self):
        self.mock_client.get_record = AsyncMock(return_value=SAMPLE_CLIENT_DETAIL_RESULT)

        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001"
        result = await self.adapter.get_by_id(url)

        assert result is not None
        # Verify normalized schema
        expected_keys = {
            "record_id",
            "name",
            "source",
            "source_her",
            "monument_type",
            "period",
            "description",
            "grid_reference",
            "easting",
            "northing",
            "designation",
            "url",
        }
        assert set(result.keys()) == expected_keys

    async def test_get_by_id_returns_none_when_client_returns_none(self):
        self.mock_client.get_record = AsyncMock(return_value=None)

        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MISSING"
        result = await self.adapter.get_by_id(url)

        assert result is None


# ============================================================================
# TestHeritageGatewayAdapterClose
# ============================================================================


class TestHeritageGatewayAdapterClose:
    async def test_close_delegates_to_client(self):
        with patch("chuk_mcp_her.core.adapters.heritage_gateway.GatewayClient") as mock_cls:
            mock_client = MagicMock()
            mock_client.close = AsyncMock()
            mock_cls.return_value = mock_client
            adapter = HeritageGatewayAdapter()

        await adapter.close()
        mock_client.close.assert_called_once()


# ============================================================================
# TestNormalizeRecord
# ============================================================================


class TestNormalizeRecord:
    def test_normalizes_full_record(self):
        raw = {
            "record_id": "MEX1001",
            "name": "Red Hill",
            "source_her": "Essex HER",
            "monument_type": "Red Hill",
            "period": "Roman",
            "description": "Salt production mound",
            "grid_reference": "TL 9050 0850",
            "easting": 590500.0,
            "northing": 208500.0,
            "designation": "Scheduled Monument",
            "url": "https://example.com/detail",
        }
        result = HeritageGatewayAdapter._normalize_record(raw)
        assert result["source"] == "heritage_gateway"
        assert result["record_id"] == "MEX1001"
        assert result["name"] == "Red Hill"
        assert result["monument_type"] == "Red Hill"
        assert result["easting"] == 590500.0

    def test_normalizes_sparse_record(self):
        raw = {"name": "Unknown site"}
        result = HeritageGatewayAdapter._normalize_record(raw)
        assert result["source"] == "heritage_gateway"
        assert result["name"] == "Unknown site"
        assert result["record_id"] is None
        assert result["monument_type"] is None
        assert result["period"] is None
        assert result["easting"] is None

    def test_ignores_extra_fields(self):
        raw = {
            "name": "Test",
            "extra_field": "should not appear",
            "another": 42,
        }
        result = HeritageGatewayAdapter._normalize_record(raw)
        assert "extra_field" not in result
        assert "another" not in result
