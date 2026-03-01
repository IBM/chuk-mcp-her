"""Tests for map visualisation tools: her_map and her_crossref_map."""

from __future__ import annotations

import json

import pytest


class TestHerMap:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.map.api import register_map_tools

        register_map_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    def test_tools_registered(self):
        assert "her_map" in self.mcp.tool_names
        assert "her_crossref_map" in self.mcp.tool_names

    async def test_her_map_returns_structured_content(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, radius_m=1000)
        assert isinstance(result, dict)
        assert "structuredContent" in result

    async def test_her_map_content_type(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, radius_m=1000)
        sc = result["structuredContent"]
        assert sc["type"] == "map"
        assert sc["version"] == "1.0"

    async def test_her_map_center(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, radius_m=500)
        sc = result["structuredContent"]
        assert sc["center"]["lat"] == pytest.approx(51.508)
        assert sc["center"]["lon"] == pytest.approx(-0.076)

    async def test_her_map_has_layers(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, radius_m=1000)
        sc = result["structuredContent"]
        assert "layers" in sc
        assert isinstance(sc["layers"], list)
        assert len(sc["layers"]) > 0

    async def test_her_map_nhle_layers_split_by_type(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, radius_m=1000)
        sc = result["structuredContent"]
        layer_ids = [la["id"] for la in sc["layers"]]
        # NHLE features in mock have listed_building and scheduled_monument types
        nhle_layers = [lid for lid in layer_ids if lid.startswith("nhle_")]
        assert len(nhle_layers) >= 1

    async def test_her_map_basemap_default(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076)
        assert result["structuredContent"]["basemap"] == "osm"

    async def test_her_map_basemap_custom(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, basemap="satellite")
        assert result["structuredContent"]["basemap"] == "satellite"

    async def test_her_map_invalid_basemap_defaults_to_osm(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, basemap="invalid")
        assert result["structuredContent"]["basemap"] == "osm"

    async def test_her_map_has_controls(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076)
        sc = result["structuredContent"]
        assert "controls" in sc

    async def test_her_map_with_bbox(self):
        result = await self.mcp.get_tool("her_map")(bbox="-0.2,51.4,0.1,51.6")
        sc = result["structuredContent"]
        assert sc["type"] == "map"
        assert sc["center"]["lat"] == pytest.approx(51.5)
        assert sc["center"]["lon"] == pytest.approx(-0.05)

    async def test_her_map_sources_filter(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, sources="nhle")
        sc = result["structuredContent"]
        layer_ids = [la["id"] for la in sc["layers"]]
        # Only nhle_ layers should be present
        non_nhle = [lid for lid in layer_ids if not lid.startswith("nhle_")]
        assert non_nhle == []

    async def test_her_map_no_spatial_params_raises(self):
        with pytest.raises(ValueError):
            await self.mcp.get_tool("her_map")()

    async def test_her_map_layer_has_features(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076)
        sc = result["structuredContent"]
        for layer in sc["layers"]:
            assert "features" in layer
            assert layer["features"]["type"] == "FeatureCollection"

    async def test_her_map_layer_has_style(self):
        result = await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076)
        sc = result["structuredContent"]
        for layer in sc["layers"]:
            assert "style" in layer
            assert "color" in layer["style"]

    async def test_her_map_calls_all_sources(self):
        await self.mcp.get_tool("her_map")(lat=51.508, lon=-0.076, radius_m=500)
        self.registry.search_designations.assert_called_once()
        self.registry.search_aerial.assert_called_once()
        self.registry.search_conservation_areas.assert_called_once()
        self.registry.search_heritage_at_risk.assert_called_once()
        self.registry.search_scotland.assert_called_once()


class TestHerCrossrefMap:
    @pytest.fixture(autouse=True)
    def setup(self, mock_mcp, mock_registry):
        from chuk_mcp_her.tools.map.api import register_map_tools

        register_map_tools(mock_mcp, mock_registry)
        self.mcp = mock_mcp
        self.registry = mock_registry

    async def test_empty_candidates_returns_map(self):
        result = await self.mcp.get_tool("her_crossref_map")(candidates="[]")
        assert isinstance(result, dict)
        assert "structuredContent" in result
        sc = result["structuredContent"]
        assert sc["type"] == "map"
        assert sc["layers"] == []

    async def test_empty_candidates_centres_on_uk(self):
        result = await self.mcp.get_tool("her_crossref_map")(candidates="[]")
        sc = result["structuredContent"]
        assert sc["center"]["lat"] == pytest.approx(54.0)
        assert sc["center"]["lon"] == pytest.approx(-2.0)

    async def test_with_candidates_returns_structured_content(self):
        candidates = json.dumps(
            [
                {"easting": 590625, "northing": 208193, "name": "Candidate A"},
                {"easting": 596100, "northing": 211850, "name": "Candidate B"},
            ]
        )
        result = await self.mcp.get_tool("her_crossref_map")(candidates=candidates)
        assert "structuredContent" in result
        sc = result["structuredContent"]
        assert sc["type"] == "map"

    async def test_with_candidates_has_layers(self):
        candidates = json.dumps(
            [
                {"easting": 590625, "northing": 208193, "name": "Candidate A"},
            ]
        )
        result = await self.mcp.get_tool("her_crossref_map")(candidates=candidates)
        sc = result["structuredContent"]
        assert isinstance(sc["layers"], list)

    async def test_known_assets_layer_present(self):
        candidates = json.dumps(
            [
                {"easting": 590625, "northing": 208193, "name": "Test Site"},
            ]
        )
        result = await self.mcp.get_tool("her_crossref_map")(candidates=candidates)
        sc = result["structuredContent"]
        layer_ids = [la["id"] for la in sc["layers"]]
        # Known assets layer should always be present when there are known assets
        assert "known_assets" in layer_ids

    async def test_classification_layers_present(self):
        # Use a candidate far from all mock known assets → should be novel
        candidates = json.dumps(
            [
                {"easting": 100000, "northing": 100000, "name": "Remote Site"},
            ]
        )
        result = await self.mcp.get_tool("her_crossref_map")(candidates=candidates)
        sc = result["structuredContent"]
        layer_ids = [la["id"] for la in sc["layers"]]
        # Remote candidate should be classified as novel
        assert "novel" in layer_ids

    async def test_match_candidate_classified_correctly(self):
        # Place candidate at exact same location as known NHLE asset
        candidates = json.dumps(
            [
                {"easting": 590625, "northing": 208193, "name": "On NHLE Site"},
            ]
        )
        result = await self.mcp.get_tool("her_crossref_map")(
            candidates=candidates, match_radius_m=100.0
        )
        sc = result["structuredContent"]
        layer_ids = [la["id"] for la in sc["layers"]]
        assert "match" in layer_ids

    async def test_basemap_passed_through(self):
        candidates = json.dumps([{"easting": 590625, "northing": 208193}])
        result = await self.mcp.get_tool("her_crossref_map")(
            candidates=candidates, basemap="terrain"
        )
        assert result["structuredContent"]["basemap"] == "terrain"

    async def test_invalid_basemap_defaults_to_osm(self):
        candidates = json.dumps([{"easting": 590625, "northing": 208193}])
        result = await self.mcp.get_tool("her_crossref_map")(candidates=candidates, basemap="bad")
        assert result["structuredContent"]["basemap"] == "osm"

    async def test_layer_features_are_geojson(self):
        candidates = json.dumps(
            [
                {"easting": 590625, "northing": 208193, "name": "Site A"},
                {"easting": 100000, "northing": 100000, "name": "Site B"},
            ]
        )
        result = await self.mcp.get_tool("her_crossref_map")(candidates=candidates)
        sc = result["structuredContent"]
        for layer in sc["layers"]:
            assert layer["features"]["type"] == "FeatureCollection"
            assert isinstance(layer["features"]["features"], list)

    async def test_include_aim_calls_search_aerial(self):
        candidates = json.dumps([{"easting": 590625, "northing": 208193}])
        await self.mcp.get_tool("her_crossref_map")(candidates=candidates, include_aim=True)
        self.registry.search_aerial.assert_called()

    async def test_no_aim_without_flag(self):
        candidates = json.dumps([{"easting": 590625, "northing": 208193}])
        self.registry.search_aerial.reset_mock()
        await self.mcp.get_tool("her_crossref_map")(candidates=candidates, include_aim=False)
        self.registry.search_aerial.assert_not_called()


class TestMapHelpers:
    """Tests for private helper functions."""

    def test_zoom_from_radius_small(self):
        from chuk_mcp_her.tools.map.api import _zoom_from_radius_m

        # 50m radius → zoom 16
        assert _zoom_from_radius_m(50) == 16

    def test_zoom_from_radius_large(self):
        from chuk_mcp_her.tools.map.api import _zoom_from_radius_m

        # Very large radius → clamped to 8
        assert _zoom_from_radius_m(50000) == 8

    def test_zoom_from_radius_clamp_min(self):
        from chuk_mcp_her.tools.map.api import _zoom_from_radius_m

        # Radius below 50 uses 50 as minimum
        assert _zoom_from_radius_m(10) == 16

    def test_zoom_from_extent_small(self):
        from chuk_mcp_her.tools.map.api import _zoom_from_wgs84_extent

        assert _zoom_from_wgs84_extent(0.001, 0.001) <= 16

    def test_zoom_from_extent_large(self):
        from chuk_mcp_her.tools.map.api import _zoom_from_wgs84_extent

        assert _zoom_from_wgs84_extent(5.0, 5.0) >= 7

    def test_to_geojson_basic(self):
        from chuk_mcp_her.tools.map.api import _to_geojson

        features = [
            {"name": "Site A", "lat": 51.5, "lon": -0.1, "record_id": "nhle:1"},
            {"name": "Site B", "lat": 52.0, "lon": -1.0, "record_id": "nhle:2"},
        ]
        fc = _to_geojson(features)
        assert fc["type"] == "FeatureCollection"
        assert len(fc["features"]) == 2
        assert fc["features"][0]["geometry"]["type"] == "Point"
        assert fc["features"][0]["geometry"]["coordinates"] == [-0.1, 51.5]

    def test_to_geojson_skips_missing_coords(self):
        from chuk_mcp_her.tools.map.api import _to_geojson

        features = [
            {"name": "Site A", "lat": 51.5, "lon": -0.1},
            {"name": "No Coords"},
            {"name": "Site C", "lat": 52.0, "lon": None},
        ]
        fc = _to_geojson(features)
        assert len(fc["features"]) == 1

    def test_to_geojson_lat_lon_excluded_from_properties(self):
        from chuk_mcp_her.tools.map.api import _to_geojson

        features = [{"name": "Site", "lat": 51.5, "lon": -0.1, "easting": 533500.0}]
        fc = _to_geojson(features)
        props = fc["features"][0]["properties"]
        assert "lat" not in props
        assert "lon" not in props
        assert props["easting"] == 533500.0

    def test_to_geojson_coordinates_order(self):
        from chuk_mcp_her.tools.map.api import _to_geojson

        features = [{"name": "X", "lat": 51.5, "lon": -0.076}]
        fc = _to_geojson(features)
        coords = fc["features"][0]["geometry"]["coordinates"]
        # GeoJSON is [longitude, latitude]
        assert coords[0] == pytest.approx(-0.076)
        assert coords[1] == pytest.approx(51.5)
