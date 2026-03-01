"""Tests for all MCP tool modules.

Uses MockMCPServer and mock_registry fixtures from conftest.py.
Each tool is invoked via mock_mcp.get_tool() and validated for
correct JSON output.
"""

from __future__ import annotations

import json

import pytest

from chuk_mcp_her.core.adapters.base import PaginatedResult


# ============================================================================
# Discovery Tools
# ============================================================================


class TestDiscoveryTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.discovery.api import register_discovery_tools

        register_discovery_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_status(self):
        result = await self.mcp.get_tool("her_status")()
        parsed = json.loads(result)
        assert "server" in parsed
        assert parsed["server"] == "chuk-mcp-her"
        assert parsed["version"] == "0.3.0"
        assert parsed["tool_count"] == 28
        assert "sources" in parsed
        assert "nhle" in parsed["sources"]

    async def test_her_status_text_mode(self):
        result = await self.mcp.get_tool("her_status")(output_mode="text")
        assert "chuk-mcp-her" in result
        assert "nhle" in result

    async def test_her_list_sources(self):
        result = await self.mcp.get_tool("her_list_sources")()
        parsed = json.loads(result)
        assert parsed["count"] == 6
        assert len(parsed["sources"]) == 6
        source_ids = [s["source_id"] for s in parsed["sources"]]
        assert "nhle" in source_ids
        assert "aim" in source_ids
        assert "conservation_area" in source_ids
        assert "heritage_at_risk" in source_ids
        assert "heritage_gateway" in source_ids
        assert "scotland" in source_ids

    async def test_her_list_sources_text_mode(self):
        result = await self.mcp.get_tool("her_list_sources")(output_mode="text")
        assert "nhle" in result
        assert "aim" in result

    async def test_her_capabilities(self):
        result = await self.mcp.get_tool("her_capabilities")()
        parsed = json.loads(result)
        assert len(parsed["tools"]) >= 16
        assert parsed["server"] == "chuk-mcp-her"
        assert parsed["tool_count"] == len(parsed["tools"])
        assert "sources" in parsed
        assert "llm_guidance" in parsed

    async def test_her_capabilities_has_all_tools(self):
        result = await self.mcp.get_tool("her_capabilities")()
        parsed = json.loads(result)
        tool_names = [t["name"] for t in parsed["tools"]]
        expected_tools = [
            "her_status",
            "her_list_sources",
            "her_capabilities",
            "her_search_monuments",
            "her_get_monument",
            "her_search_listed_buildings",
            "her_search_designations",
            "her_count_features",
            "her_search_aerial",
            "her_count_aerial",
            "her_get_aerial_feature",
            "her_search_heritage_gateway",
            "her_cross_reference",
            "her_enrich_gateway",
            "her_nearby",
            "her_export_geojson",
            "her_export_for_lidar",
        ]
        for tool in expected_tools:
            assert tool in tool_names, f"Missing tool: {tool}"

    async def test_her_capabilities_text_mode(self):
        result = await self.mcp.get_tool("her_capabilities")(output_mode="text")
        assert "her_status" in result
        assert "her_search_monuments" in result

    async def test_her_status_error(self):
        self.registry.list_sources.side_effect = Exception("connection failed")
        result = await self.mcp.get_tool("her_status")()
        parsed = json.loads(result)
        assert "error" in parsed
        assert "connection failed" in parsed["error"]

    async def test_her_list_sources_error(self):
        self.registry.list_sources.side_effect = Exception("db error")
        result = await self.mcp.get_tool("her_list_sources")()
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_capabilities_error(self):
        self.registry.list_sources.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_capabilities")()
        parsed = json.loads(result)
        assert "error" in parsed


# ============================================================================
# NHLE Tools
# ============================================================================


class TestNHLETools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.nhle.api import register_nhle_tools

        register_nhle_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_search_monuments(self):
        result = await self.mcp.get_tool("her_search_monuments")(name="Red Hill")
        parsed = json.loads(result)
        assert "monuments" in parsed
        assert parsed["count"] == 2
        assert parsed["source"] == "nhle"
        self.registry.search_monuments.assert_called_once()

    async def test_her_search_monuments_with_bbox(self):
        result = await self.mcp.get_tool("her_search_monuments")(bbox="586000,205000,602500,215000")
        parsed = json.loads(result)
        assert "monuments" in parsed
        call_kwargs = self.registry.search_monuments.call_args[1]
        assert call_kwargs["bbox"] == (586000.0, 205000.0, 602500.0, 215000.0)

    async def test_her_search_monuments_with_lat_lon(self):
        result = await self.mcp.get_tool("her_search_monuments")(
            lat=51.754, lon=0.812, radius_m=500
        )
        parsed = json.loads(result)
        assert "monuments" in parsed
        call_kwargs = self.registry.search_monuments.call_args[1]
        assert call_kwargs["lat"] == 51.754
        assert call_kwargs["lon"] == 0.812
        assert call_kwargs["radius_m"] == 500

    async def test_her_search_monuments_text_mode(self):
        result = await self.mcp.get_tool("her_search_monuments")(
            name="Red Hill", output_mode="text"
        )
        assert "Red Hill" in result

    async def test_her_get_monument(self):
        result = await self.mcp.get_tool("her_get_monument")(nhle_id="1000001")
        parsed = json.loads(result)
        assert "monument" in parsed
        assert parsed["monument"]["nhle_id"] == "1000001"
        assert parsed["monument"]["name"] == "Church of St Mary"
        self.registry.get_monument.assert_called_once_with("1000001")

    async def test_her_get_monument_not_found(self):
        self.registry.get_monument.return_value = None
        result = await self.mcp.get_tool("her_get_monument")(nhle_id="9999999")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"].lower()

    async def test_her_search_listed_buildings(self):
        result = await self.mcp.get_tool("her_search_listed_buildings")(name="Church", grade="I")
        parsed = json.loads(result)
        assert "monuments" in parsed
        assert parsed["count"] == 1
        self.registry.search_listed_buildings.assert_called_once()
        call_kwargs = self.registry.search_listed_buildings.call_args[1]
        assert call_kwargs["grade"] == "I"

    async def test_her_search_listed_buildings_invalid_grade(self):
        result = await self.mcp.get_tool("her_search_listed_buildings")(grade="III")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "III" in parsed["error"]

    async def test_her_search_designations(self):
        result = await self.mcp.get_tool("her_search_designations")(
            designation_type="scheduled_monument", name="Red Hill"
        )
        parsed = json.loads(result)
        assert "designations" in parsed
        assert parsed["count"] == 3
        self.registry.search_designations.assert_called_once()

    async def test_her_search_designations_invalid_type(self):
        result = await self.mcp.get_tool("her_search_designations")(designation_type="castle")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "castle" in parsed["error"]

    async def test_her_count_features(self):
        result = await self.mcp.get_tool("her_count_features")(bbox="530000,170000,540000,190000")
        parsed = json.loads(result)
        assert "counts" in parsed
        assert parsed["counts"]["total"] == 170
        assert parsed["counts"]["listed_building"] == 156
        assert parsed["counts"]["scheduled_monument"] == 12

    async def test_her_count_features_with_designation(self):
        result = await self.mcp.get_tool("her_count_features")(
            designation_type="scheduled_monument"
        )
        parsed = json.loads(result)
        assert "counts" in parsed

    async def test_her_search_monuments_no_results(self):
        self.registry.search_monuments.return_value = PaginatedResult(
            features=[], total_count=0, has_more=False
        )
        result = await self.mcp.get_tool("her_search_monuments")(name="nonexistent")
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error_type"] == "no_data"

    async def test_her_search_monuments_invalid_bbox(self):
        result = await self.mcp.get_tool("her_search_monuments")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error_type"] == "validation_error"

    async def test_her_search_monuments_error(self):
        self.registry.search_monuments.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_search_monuments")(name="test")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_get_monument_error(self):
        self.registry.get_monument.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_get_monument")(nhle_id="1000001")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_search_listed_buildings_no_results(self):
        self.registry.search_listed_buildings.return_value = PaginatedResult(
            features=[], total_count=0, has_more=False
        )
        result = await self.mcp.get_tool("her_search_listed_buildings")(name="nonexistent")
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error_type"] == "no_data"

    async def test_her_search_listed_buildings_invalid_bbox(self):
        result = await self.mcp.get_tool("her_search_listed_buildings")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_search_listed_buildings_error(self):
        self.registry.search_listed_buildings.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_search_listed_buildings")(name="test")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_search_designations_no_results(self):
        self.registry.search_designations.return_value = PaginatedResult(
            features=[], total_count=0, has_more=False
        )
        result = await self.mcp.get_tool("her_search_designations")(name="nonexistent")
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error_type"] == "no_data"

    async def test_her_search_designations_invalid_bbox(self):
        result = await self.mcp.get_tool("her_search_designations")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_search_designations_error(self):
        self.registry.search_designations.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_search_designations")(name="test")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_features_invalid_bbox(self):
        result = await self.mcp.get_tool("her_count_features")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_features_error(self):
        self.registry.count_features.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_count_features")()
        parsed = json.loads(result)
        assert "error" in parsed


# ============================================================================
# Aerial Tools
# ============================================================================


class TestAerialTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.aerial.api import register_aerial_tools

        register_aerial_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_search_aerial(self):
        result = await self.mcp.get_tool("her_search_aerial")(monument_type="ENCLOSURE")
        parsed = json.loads(result)
        assert "features" in parsed
        assert parsed["count"] == 2
        assert parsed["source"] == "aim"
        self.registry.search_aerial.assert_called_once()

    async def test_her_search_aerial_with_bbox(self):
        result = await self.mcp.get_tool("her_search_aerial")(bbox="586000,205000,602500,215000")
        parsed = json.loads(result)
        assert "features" in parsed
        call_kwargs = self.registry.search_aerial.call_args[1]
        assert call_kwargs["bbox"] == (586000.0, 205000.0, 602500.0, 215000.0)

    async def test_her_search_aerial_with_lat_lon(self):
        result = await self.mcp.get_tool("her_search_aerial")(lat=51.77, lon=0.87, radius_m=1000)
        parsed = json.loads(result)
        assert "features" in parsed
        call_kwargs = self.registry.search_aerial.call_args[1]
        assert call_kwargs["lat"] == 51.77
        assert call_kwargs["lon"] == 0.87

    async def test_her_search_aerial_text_mode(self):
        result = await self.mcp.get_tool("her_search_aerial")(
            monument_type="ENCLOSURE", output_mode="text"
        )
        assert "ENCLOSURE" in result

    async def test_her_search_aerial_invalid_bbox(self):
        result = await self.mcp.get_tool("her_search_aerial")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_aerial(self):
        result = await self.mcp.get_tool("her_count_aerial")(bbox="586000,205000,602500,215000")
        parsed = json.loads(result)
        assert parsed["count"] == 42
        assert parsed["source"] == "aim"
        self.registry.count_aerial.assert_called_once()

    async def test_her_count_aerial_with_filters(self):
        result = await self.mcp.get_tool("her_count_aerial")(monument_type="MOUND", period="ROMAN")
        parsed = json.loads(result)
        assert parsed["count"] == 42
        call_kwargs = self.registry.count_aerial.call_args[1]
        assert call_kwargs["monument_type"] == "MOUND"
        assert call_kwargs["period"] == "ROMAN"

    async def test_her_count_aerial_text_mode(self):
        result = await self.mcp.get_tool("her_count_aerial")(output_mode="text")
        assert "42" in result

    async def test_her_get_aerial_feature(self):
        result = await self.mcp.get_tool("her_get_aerial_feature")(record_id="aim:AIM001")
        parsed = json.loads(result)
        assert "monument" in parsed
        assert parsed["monument"]["aim_id"] == "AIM001"
        self.registry.get_aerial_feature.assert_called_once_with("aim:AIM001")

    async def test_her_get_aerial_feature_auto_prefix(self):
        result = await self.mcp.get_tool("her_get_aerial_feature")(record_id="AIM001")
        parsed = json.loads(result)
        assert "monument" in parsed
        self.registry.get_aerial_feature.assert_called_once_with("aim:AIM001")

    async def test_her_get_aerial_feature_not_found(self):
        self.registry.get_aerial_feature.return_value = None
        result = await self.mcp.get_tool("her_get_aerial_feature")(record_id="aim:MISSING")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"].lower()

    async def test_her_get_aerial_feature_empty_id(self):
        result = await self.mcp.get_tool("her_get_aerial_feature")(record_id="")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "required" in parsed["error"]

    async def test_her_search_aerial_error(self):
        self.registry.search_aerial.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_search_aerial")(monument_type="ENCLOSURE")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_aerial_invalid_bbox(self):
        result = await self.mcp.get_tool("her_count_aerial")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_aerial_error(self):
        self.registry.count_aerial.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_count_aerial")()
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_get_aerial_feature_error(self):
        self.registry.get_aerial_feature.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_get_aerial_feature")(record_id="aim:AIM001")
        parsed = json.loads(result)
        assert "error" in parsed


# ============================================================================
# Conservation Area Tools
# ============================================================================


class TestConservationAreaTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.conservation_area.api import (
            register_conservation_area_tools,
        )

        register_conservation_area_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_search_conservation_areas(self):
        result = await self.mcp.get_tool("her_search_conservation_areas")(query="Maldon")
        parsed = json.loads(result)
        assert "areas" in parsed
        assert parsed["count"] == 2
        assert parsed["areas"][0]["name"] == "Maldon Conservation Area"
        assert parsed["areas"][1]["name"] == "Heybridge Basin Conservation Area"
        self.registry.search_conservation_areas.assert_called_once()

    async def test_her_search_conservation_areas_text_mode(self):
        result = await self.mcp.get_tool("her_search_conservation_areas")(
            query="Maldon", output_mode="text"
        )
        assert "Maldon Conservation Area" in result

    async def test_her_search_conservation_areas_with_lpa(self):
        result = await self.mcp.get_tool("her_search_conservation_areas")(
            lpa="Maldon District Council"
        )
        parsed = json.loads(result)
        assert "areas" in parsed
        call_kwargs = self.registry.search_conservation_areas.call_args[1]
        assert call_kwargs["lpa"] == "Maldon District Council"

    async def test_her_search_conservation_areas_with_bbox(self):
        result = await self.mcp.get_tool("her_search_conservation_areas")(
            bbox="585000,207000,587000,208000"
        )
        parsed = json.loads(result)
        assert "areas" in parsed
        call_kwargs = self.registry.search_conservation_areas.call_args[1]
        assert call_kwargs["bbox"] == (585000.0, 207000.0, 587000.0, 208000.0)

    async def test_her_search_conservation_areas_invalid_bbox(self):
        result = await self.mcp.get_tool("her_search_conservation_areas")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_conservation_areas(self):
        result = await self.mcp.get_tool("her_count_conservation_areas")(
            bbox="585000,207000,587000,208000"
        )
        parsed = json.loads(result)
        assert parsed["count"] == 25
        self.registry.count_conservation_areas.assert_called_once()

    async def test_her_count_conservation_areas_with_lpa(self):
        result = await self.mcp.get_tool("her_count_conservation_areas")(
            lpa="Maldon District Council"
        )
        parsed = json.loads(result)
        assert parsed["count"] == 25
        call_kwargs = self.registry.count_conservation_areas.call_args[1]
        assert call_kwargs["lpa"] == "Maldon District Council"

    async def test_her_get_conservation_area(self):
        result = await self.mcp.get_tool("her_get_conservation_area")(record_id="ca:1001")
        parsed = json.loads(result)
        assert "monument" in parsed
        assert parsed["monument"]["name"] == "Maldon Conservation Area"
        self.registry.get_conservation_area.assert_called_once_with("ca:1001")

    async def test_her_get_conservation_area_adds_prefix(self):
        result = await self.mcp.get_tool("her_get_conservation_area")(record_id="1001")
        parsed = json.loads(result)
        assert "monument" in parsed
        self.registry.get_conservation_area.assert_called_once_with("ca:1001")

    async def test_her_get_conservation_area_not_found(self):
        from unittest.mock import AsyncMock

        self.registry.get_conservation_area = AsyncMock(return_value=None)
        result = await self.mcp.get_tool("her_get_conservation_area")(record_id="ca:9999")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"].lower()

    async def test_her_search_conservation_areas_error(self):
        self.registry.search_conservation_areas.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_search_conservation_areas")(query="test")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_conservation_areas_invalid_bbox(self):
        result = await self.mcp.get_tool("her_count_conservation_areas")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_conservation_areas_with_query_and_lpa(self):
        result = await self.mcp.get_tool("her_count_conservation_areas")(
            query="Maldon", lpa="Maldon District Council"
        )
        parsed = json.loads(result)
        assert parsed["count"] == 25
        assert parsed["query"]["query"] == "Maldon"
        assert parsed["query"]["lpa"] == "Maldon District Council"

    async def test_her_count_conservation_areas_error(self):
        self.registry.count_conservation_areas.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_count_conservation_areas")()
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_get_conservation_area_empty_id(self):
        result = await self.mcp.get_tool("her_get_conservation_area")(record_id="")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "required" in parsed["error"]

    async def test_her_get_conservation_area_error(self):
        self.registry.get_conservation_area.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_get_conservation_area")(record_id="ca:1001")
        parsed = json.loads(result)
        assert "error" in parsed


# ============================================================================
# Heritage at Risk Tools
# ============================================================================


class TestHeritageAtRiskTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.heritage_at_risk.api import (
            register_heritage_at_risk_tools,
        )

        register_heritage_at_risk_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_search_heritage_at_risk(self):
        result = await self.mcp.get_tool("her_search_heritage_at_risk")(query="church")
        parsed = json.loads(result)
        assert "entries" in parsed
        assert parsed["count"] == 2
        assert parsed["entries"][0]["name"] == "Church of All Saints, Maldon"
        assert parsed["entries"][1]["name"] == "Beeleigh Abbey, Maldon"
        self.registry.search_heritage_at_risk.assert_called_once()

    async def test_her_search_heritage_at_risk_text_mode(self):
        result = await self.mcp.get_tool("her_search_heritage_at_risk")(
            query="church", output_mode="text"
        )
        assert "Church of All Saints" in result

    async def test_her_search_heritage_at_risk_with_category(self):
        result = await self.mcp.get_tool("her_search_heritage_at_risk")(
            heritage_category="Listed Building"
        )
        parsed = json.loads(result)
        assert "entries" in parsed
        call_kwargs = self.registry.search_heritage_at_risk.call_args[1]
        assert call_kwargs["heritage_category"] == "Listed Building"

    async def test_her_search_heritage_at_risk_invalid_category(self):
        result = await self.mcp.get_tool("her_search_heritage_at_risk")(heritage_category="Castle")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Castle" in parsed["error"]
        assert "suggestion" in parsed

    async def test_her_search_heritage_at_risk_with_bbox(self):
        result = await self.mcp.get_tool("her_search_heritage_at_risk")(
            bbox="585000,207000,587000,208000"
        )
        parsed = json.loads(result)
        assert "entries" in parsed
        call_kwargs = self.registry.search_heritage_at_risk.call_args[1]
        assert call_kwargs["bbox"] == (585000.0, 207000.0, 587000.0, 208000.0)

    async def test_her_count_heritage_at_risk(self):
        result = await self.mcp.get_tool("her_count_heritage_at_risk")(
            bbox="585000,207000,587000,208000"
        )
        parsed = json.loads(result)
        assert parsed["count"] == 15
        self.registry.count_heritage_at_risk.assert_called_once()

    async def test_her_count_heritage_at_risk_with_category(self):
        result = await self.mcp.get_tool("her_count_heritage_at_risk")(
            heritage_category="Scheduled Monument"
        )
        parsed = json.loads(result)
        assert parsed["count"] == 15
        call_kwargs = self.registry.count_heritage_at_risk.call_args[1]
        assert call_kwargs["heritage_category"] == "Scheduled Monument"

    async def test_her_count_heritage_at_risk_invalid_category(self):
        result = await self.mcp.get_tool("her_count_heritage_at_risk")(
            heritage_category="Haunted House"
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Haunted House" in parsed["error"]

    async def test_her_get_heritage_at_risk(self):
        result = await self.mcp.get_tool("her_get_heritage_at_risk")(record_id="har:1021506")
        parsed = json.loads(result)
        assert "monument" in parsed
        assert parsed["monument"]["name"] == "Church of All Saints, Maldon"
        self.registry.get_heritage_at_risk.assert_called_once_with("har:1021506")

    async def test_her_get_heritage_at_risk_adds_prefix(self):
        result = await self.mcp.get_tool("her_get_heritage_at_risk")(record_id="1021506")
        parsed = json.loads(result)
        assert "monument" in parsed
        self.registry.get_heritage_at_risk.assert_called_once_with("har:1021506")

    async def test_her_get_heritage_at_risk_not_found(self):
        from unittest.mock import AsyncMock

        self.registry.get_heritage_at_risk = AsyncMock(return_value=None)
        result = await self.mcp.get_tool("her_get_heritage_at_risk")(record_id="har:9999999")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"].lower()

    async def test_her_search_heritage_at_risk_invalid_bbox(self):
        result = await self.mcp.get_tool("her_search_heritage_at_risk")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_search_heritage_at_risk_error(self):
        self.registry.search_heritage_at_risk.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_search_heritage_at_risk")(query="test")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_heritage_at_risk_invalid_bbox(self):
        result = await self.mcp.get_tool("her_count_heritage_at_risk")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_count_heritage_at_risk_error(self):
        self.registry.count_heritage_at_risk.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_count_heritage_at_risk")()
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_get_heritage_at_risk_empty_id(self):
        result = await self.mcp.get_tool("her_get_heritage_at_risk")(record_id="")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "required" in parsed["error"]

    async def test_her_get_heritage_at_risk_error(self):
        self.registry.get_heritage_at_risk.side_effect = Exception("boom")
        result = await self.mcp.get_tool("her_get_heritage_at_risk")(record_id="har:1021506")
        parsed = json.loads(result)
        assert "error" in parsed


# ============================================================================
# Gateway Tools
# ============================================================================


class TestGatewayTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.gateway.api import register_gateway_tools

        register_gateway_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_search_heritage_gateway_returns_records(self):
        """Gateway tool should return matching records."""
        result = await self.mcp.get_tool("her_search_heritage_gateway")(what="red hill")
        parsed = json.loads(result)
        assert "records" in parsed
        assert parsed["count"] == 2
        assert parsed["records"][0]["name"] == "Red Hill, Goldhanger"
        assert parsed["records"][0]["monument_type"] == "Red Hill"

    async def test_her_search_heritage_gateway_text_mode(self):
        result = await self.mcp.get_tool("her_search_heritage_gateway")(
            what="red hill", output_mode="text"
        )
        assert "Red Hill, Goldhanger" in result

    async def test_her_search_heritage_gateway_empty_results(self):
        """Gateway tool should add a note when no results returned."""
        from unittest.mock import AsyncMock
        from chuk_mcp_her.core.adapters.base import PaginatedResult

        self.registry.search_heritage_gateway = AsyncMock(
            return_value=PaginatedResult(features=[], total_count=0, has_more=False)
        )
        result = await self.mcp.get_tool("her_search_heritage_gateway")(what="nonexistent")
        parsed = json.loads(result)
        assert parsed["count"] == 0
        assert parsed["note"] is not None
        assert "unavailable" in parsed["note"]

    async def test_her_search_heritage_gateway_error(self):
        self.registry.search_heritage_gateway.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_search_heritage_gateway")(what="test")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "suggestion" in parsed


# ============================================================================
# Cross-Reference Tools
# ============================================================================


class TestCrossrefTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.crossref.api import register_crossref_tools

        register_crossref_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_cross_reference(self):
        candidates = json.dumps(
            [
                {"easting": 533500, "northing": 180500},
                {"easting": 590625, "northing": 208193},
                {"easting": 400000, "northing": 300000},
            ]
        )
        result = await self.mcp.get_tool("her_cross_reference")(candidates=candidates)
        parsed = json.loads(result)
        assert "candidates_submitted" in parsed
        assert parsed["candidates_submitted"] == 3
        assert "classification" in parsed
        assert "match" in parsed["classification"]
        assert "near" in parsed["classification"]
        assert "novel" in parsed["classification"]
        total = (
            parsed["classification"]["match"]
            + parsed["classification"]["near"]
            + parsed["classification"]["novel"]
        )
        assert total == 3

    async def test_her_cross_reference_empty_candidates(self):
        result = await self.mcp.get_tool("her_cross_reference")(candidates="[]")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_nearby_with_lat_lon(self):
        result = await self.mcp.get_tool("her_nearby")(lat=51.508, lon=-0.076, radius_m=500)
        parsed = json.loads(result)
        assert "assets" in parsed
        assert parsed["count"] == 3
        assert parsed["centre_lat"] == 51.508
        assert parsed["centre_lon"] == -0.076
        assert parsed["radius_m"] == 500
        # Assets should have distance_m and bearing_deg
        for asset in parsed["assets"]:
            assert "record_id" in asset
            assert "name" in asset

    async def test_her_nearby_with_easting_northing(self):
        result = await self.mcp.get_tool("her_nearby")(
            easting=533500, northing=180500, radius_m=1000
        )
        parsed = json.loads(result)
        assert "assets" in parsed
        assert parsed["count"] == 3

    async def test_her_nearby_no_coordinates(self):
        result = await self.mcp.get_tool("her_nearby")()
        parsed = json.loads(result)
        assert "error" in parsed
        assert parsed["error_type"] == "validation_error"

    async def test_her_nearby_assets_sorted_by_distance(self):
        result = await self.mcp.get_tool("her_nearby")(lat=51.508, lon=-0.076, radius_m=50000)
        parsed = json.loads(result)
        distances = [a["distance_m"] for a in parsed["assets"] if a.get("distance_m") is not None]
        assert distances == sorted(distances)

    async def test_her_cross_reference_with_gateway_sites(self):
        """Gateway sites should be merged into known sites pool."""
        candidates = json.dumps(
            [
                {"easting": 590520, "northing": 208510},
            ]
        )
        gateway_sites = json.dumps(
            [
                {
                    "easting": 590500.0,
                    "northing": 208500.0,
                    "name": "Red Hill HER",
                    "record_id": "hg:MEX1001",
                    "source": "heritage_gateway",
                },
            ]
        )
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
            gateway_sites=gateway_sites,
        )
        parsed = json.loads(result)
        assert parsed["candidates_submitted"] == 1
        # The candidate at (590520, 208510) is ~22m from the Gateway site
        # at (590500, 208500), well within the 50m match radius
        assert parsed["classification"]["match"] >= 1

    async def test_her_cross_reference_default_no_gateway(self):
        """Default empty gateway_sites should not break existing behaviour."""
        candidates = json.dumps([{"easting": 590625, "northing": 208193}])
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
        )
        parsed = json.loads(result)
        assert "classification" in parsed
        total = (
            parsed["classification"]["match"]
            + parsed["classification"]["near"]
            + parsed["classification"]["novel"]
        )
        assert total == 1

    async def test_her_cross_reference_with_include_aim(self):
        """AIM features should be merged when include_aim=True."""
        candidates = json.dumps(
            [
                {"easting": 594500, "northing": 210000},  # Exact match to AIM001
            ]
        )
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
            include_aim=True,
        )
        parsed = json.loads(result)
        assert parsed["classification"]["match"] == 1
        self.registry.search_aerial.assert_called_once()

    async def test_her_cross_reference_include_aim_false_default(self):
        """search_aerial should NOT be called when include_aim=False (default)."""
        candidates = json.dumps([{"easting": 594500, "northing": 210000}])
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
        )
        parsed = json.loads(result)
        assert "classification" in parsed
        self.registry.search_aerial.assert_not_called()

    async def test_her_cross_reference_enriched_match_output(self):
        """Matched asset dict should include enriched fields from source data."""
        candidates = json.dumps(
            [{"easting": 533500, "northing": 180500}]  # Exact match to NHLE 1000001
        )
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
        )
        parsed = json.loads(result)
        assert parsed["classification"]["match"] == 1
        match = parsed["matches"][0]
        assert match["classification"] == "match"
        asset = match["matched_asset"]
        assert asset["record_id"] == "nhle:1000001"
        assert asset["name"] == "Church of St Mary"
        assert asset["source"] == "nhle"
        assert asset["designation_type"] == "listed_building"
        assert asset["grade"] == "I"

    async def test_her_cross_reference_designation_types_filter(self):
        """Single designation type should be passed to search_designations."""
        candidates = json.dumps([{"easting": 500000, "northing": 200000}])
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
            designation_types="scheduled_monument",
        )
        parsed = json.loads(result)
        assert "classification" in parsed
        call_kwargs = self.registry.search_designations.call_args[1]
        assert call_kwargs["designation_type"] == "scheduled_monument"

    async def test_her_cross_reference_large_batch(self):
        """100 candidates should all be classified."""
        candidates = json.dumps(
            [{"easting": 533500 + i, "northing": 180500 + i} for i in range(100)]
        )
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
        )
        parsed = json.loads(result)
        assert parsed["candidates_submitted"] == 100
        total = (
            parsed["classification"]["match"]
            + parsed["classification"]["near"]
            + parsed["classification"]["novel"]
        )
        assert total == 100

    async def test_her_enrich_gateway(self):
        """Enrich tool should return resolved Gateway records."""
        result = await self.mcp.get_tool("her_enrich_gateway")(what="red hill", where="Essex")
        parsed = json.loads(result)
        assert parsed["count"] == 1
        assert parsed["resolved_count"] == 1
        assert parsed["fetch_details_used"] is True
        assert len(parsed["records"]) == 1
        assert parsed["records"][0]["record_id"] == "hg:MEX1001"
        assert parsed["records"][0]["easting"] == 590500.0

    async def test_her_enrich_gateway_text_mode(self):
        """Text output mode should include header and coordinates."""
        result = await self.mcp.get_tool("her_enrich_gateway")(what="red hill", output_mode="text")
        assert "Resolved" in result
        assert "E=" in result

    async def test_her_cross_reference_multi_designation_types(self):
        """Comma-separated designation_types should post-filter results."""
        candidates = json.dumps([{"easting": 533500, "northing": 180500}])
        result = await self.mcp.get_tool("her_cross_reference")(
            candidates=candidates,
            designation_types="scheduled_monument,listed_building",
        )
        parsed = json.loads(result)
        assert "classification" in parsed
        # search_designations called without designation_type (post-filter)
        call_kwargs = self.registry.search_designations.call_args[1]
        assert call_kwargs["designation_type"] is None

    async def test_her_cross_reference_error(self):
        self.registry.search_designations.side_effect = Exception("timeout")
        candidates = json.dumps([{"easting": 500000, "northing": 200000}])
        result = await self.mcp.get_tool("her_cross_reference")(candidates=candidates)
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_nearby_error(self):
        self.registry.nearby.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_nearby")(lat=51.5, lon=-0.1)
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_enrich_gateway_error(self):
        self.registry.enrich_gateway_records.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_enrich_gateway")(what="test")
        parsed = json.loads(result)
        assert "error" in parsed


# ============================================================================
# Export Tools
# ============================================================================


class TestExportTools:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.export.api import register_export_tools

        register_export_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_her_export_geojson(self):
        result = await self.mcp.get_tool("her_export_geojson")(bbox="530000,170000,540000,190000")
        parsed = json.loads(result)
        assert "geojson" in parsed
        assert parsed["geojson"]["type"] == "FeatureCollection"
        assert parsed["feature_count"] == 3
        # Features should have geometry with WGS84 coordinates
        for feat in parsed["geojson"]["features"]:
            assert feat["type"] == "Feature"
            assert "properties" in feat

    async def test_her_export_geojson_with_designation_filter(self):
        result = await self.mcp.get_tool("her_export_geojson")(
            designation_type="scheduled_monument"
        )
        parsed = json.loads(result)
        assert "geojson" in parsed
        self.registry.search_designations.assert_called()
        call_kwargs = self.registry.search_designations.call_args[1]
        assert call_kwargs["designation_type"] == "scheduled_monument"

    async def test_her_export_geojson_text_mode(self):
        result = await self.mcp.get_tool("her_export_geojson")(
            bbox="530000,170000,540000,190000", output_mode="text"
        )
        assert "features" in result.lower()

    async def test_her_export_for_lidar(self):
        result = await self.mcp.get_tool("her_export_for_lidar")(bbox="530000,170000,540000,190000")
        parsed = json.loads(result)
        assert "known_sites" in parsed
        assert "bbox" in parsed
        # 3 NHLE + 2 AIM (include_aim=True by default)
        assert parsed["count"] == 5
        assert len(parsed["known_sites"]) == 5
        # Each site should have expected fields
        for site in parsed["known_sites"]:
            assert "id" in site
            assert "source" in site
            assert "name" in site

    async def test_her_export_for_lidar_no_bbox(self):
        result = await self.mcp.get_tool("her_export_for_lidar")(bbox="")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_export_for_lidar_text_mode(self):
        result = await self.mcp.get_tool("her_export_for_lidar")(
            bbox="530000,170000,540000,190000", output_mode="text"
        )
        assert "known sites" in result.lower() or "exported" in result.lower()

    async def test_her_export_for_lidar_with_gateway_sites(self):
        """Gateway sites should be included in LiDAR export."""
        gateway_sites = json.dumps(
            [
                {
                    "record_id": "hg:MEX1001",
                    "name": "Red Hill HER",
                    "monument_type": "Red Hill",
                    "easting": 590500.0,
                    "northing": 208500.0,
                },
            ]
        )
        result = await self.mcp.get_tool("her_export_for_lidar")(
            bbox="530000,170000,600000,220000",
            gateway_sites=gateway_sites,
        )
        parsed = json.loads(result)
        # Should have 3 NHLE + 2 AIM + 1 Gateway = 6 sites
        assert parsed["count"] == 6
        sources = [s["source"] for s in parsed["known_sites"]]
        assert "heritage_gateway" in sources
        assert "aim" in sources

    async def test_her_export_for_lidar_include_aim(self):
        """include_aim=True should add AIM features to export."""
        result = await self.mcp.get_tool("her_export_for_lidar")(
            bbox="530000,170000,600000,220000",
            include_aim=True,
        )
        parsed = json.loads(result)
        # 3 NHLE + 2 AIM
        assert parsed["count"] == 5
        sources = [s["source"] for s in parsed["known_sites"]]
        assert "aim" in sources
        self.registry.search_aerial.assert_called_once()

    async def test_her_export_for_lidar_aim_fields(self):
        """AIM sites should include monument_type, period, form, evidence."""
        result = await self.mcp.get_tool("her_export_for_lidar")(
            bbox="530000,170000,600000,220000",
        )
        parsed = json.loads(result)
        aim_sites = [s for s in parsed["known_sites"] if s["source"] == "aim"]
        assert len(aim_sites) == 2
        for site in aim_sites:
            assert "monument_type" in site
            assert "period" in site
            assert "form" in site
            assert "evidence" in site
        # Check specific values from fixtures
        enclosure = [s for s in aim_sites if s["id"] == "aim:AIM001"][0]
        assert enclosure["monument_type"] == "ENCLOSURE"
        assert enclosure["period"] == "IRON AGE"
        assert enclosure["form"] == "Cropmark"

    async def test_her_export_for_lidar_nhle_grade(self):
        """NHLE sites should include grade when available."""
        result = await self.mcp.get_tool("her_export_for_lidar")(
            bbox="530000,170000,600000,220000",
        )
        parsed = json.loads(result)
        nhle_sites = [s for s in parsed["known_sites"] if s["source"] == "nhle"]
        # First NHLE feature has grade "I"
        graded = [s for s in nhle_sites if s.get("grade") == "I"]
        assert len(graded) == 1
        assert graded[0]["name"] == "Church of St Mary"

    async def test_her_export_for_lidar_include_aim_false(self):
        """include_aim=False should exclude AIM features."""
        result = await self.mcp.get_tool("her_export_for_lidar")(
            bbox="530000,170000,540000,190000",
            include_aim=False,
        )
        parsed = json.loads(result)
        # NHLE only
        assert parsed["count"] == 3
        sources = {s["source"] for s in parsed["known_sites"]}
        assert "aim" not in sources
        self.registry.search_aerial.assert_not_called()

    async def test_her_export_for_lidar_gateway_fields(self):
        """Gateway sites should include monument_type and period."""
        gateway_sites = json.dumps(
            [
                {
                    "record_id": "hg:MEX1001",
                    "name": "Red Hill HER",
                    "monument_type": "Red Hill",
                    "period": "Roman",
                    "easting": 590500.0,
                    "northing": 208500.0,
                },
            ]
        )
        result = await self.mcp.get_tool("her_export_for_lidar")(
            bbox="530000,170000,600000,220000",
            gateway_sites=gateway_sites,
        )
        parsed = json.loads(result)
        gw_sites = [s for s in parsed["known_sites"] if s["source"] == "heritage_gateway"]
        assert len(gw_sites) == 1
        assert gw_sites[0]["monument_type"] == "Red Hill"
        assert gw_sites[0]["period"] == "Roman"

    async def test_her_export_geojson_invalid_bbox(self):
        result = await self.mcp.get_tool("her_export_geojson")(bbox="1,2,3")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_export_geojson_error(self):
        self.registry.search_designations.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_export_geojson")(bbox="530000,170000,540000,190000")
        parsed = json.loads(result)
        assert "error" in parsed

    async def test_her_export_for_lidar_error(self):
        self.registry.search_designations.side_effect = Exception("timeout")
        result = await self.mcp.get_tool("her_export_for_lidar")(bbox="530000,170000,540000,190000")
        parsed = json.loads(result)
        assert "error" in parsed


# ============================================================================
# Tool Registration Counts
# ============================================================================


class TestToolRegistrationCounts:
    def test_discovery_registers_3_tools(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.discovery.api import register_discovery_tools

        register_discovery_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 3
        assert "her_status" in mock_mcp.tool_names
        assert "her_list_sources" in mock_mcp.tool_names
        assert "her_capabilities" in mock_mcp.tool_names

    def test_nhle_registers_5_tools(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.nhle.api import register_nhle_tools

        register_nhle_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 5
        assert "her_search_monuments" in mock_mcp.tool_names
        assert "her_get_monument" in mock_mcp.tool_names
        assert "her_search_listed_buildings" in mock_mcp.tool_names
        assert "her_search_designations" in mock_mcp.tool_names
        assert "her_count_features" in mock_mcp.tool_names

    def test_aerial_registers_3_tools(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.aerial.api import register_aerial_tools

        register_aerial_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 3
        assert "her_search_aerial" in mock_mcp.tool_names
        assert "her_count_aerial" in mock_mcp.tool_names
        assert "her_get_aerial_feature" in mock_mcp.tool_names

    def test_conservation_area_registers_3_tools(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.conservation_area.api import (
            register_conservation_area_tools,
        )

        register_conservation_area_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 3
        assert "her_search_conservation_areas" in mock_mcp.tool_names
        assert "her_count_conservation_areas" in mock_mcp.tool_names
        assert "her_get_conservation_area" in mock_mcp.tool_names

    def test_heritage_at_risk_registers_3_tools(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.heritage_at_risk.api import (
            register_heritage_at_risk_tools,
        )

        register_heritage_at_risk_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 3
        assert "her_search_heritage_at_risk" in mock_mcp.tool_names
        assert "her_count_heritage_at_risk" in mock_mcp.tool_names
        assert "her_get_heritage_at_risk" in mock_mcp.tool_names

    def test_gateway_registers_1_tool(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.gateway.api import register_gateway_tools

        register_gateway_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 1
        assert "her_search_heritage_gateway" in mock_mcp.tool_names

    def test_crossref_registers_3_tools(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.crossref.api import register_crossref_tools

        register_crossref_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 3
        assert "her_cross_reference" in mock_mcp.tool_names
        assert "her_enrich_gateway" in mock_mcp.tool_names
        assert "her_nearby" in mock_mcp.tool_names

    def test_export_registers_2_tools(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.export.api import register_export_tools

        register_export_tools(mock_mcp, mock_registry)
        assert len(mock_mcp.tool_names) == 2
        assert "her_export_geojson" in mock_mcp.tool_names
        assert "her_export_for_lidar" in mock_mcp.tool_names
