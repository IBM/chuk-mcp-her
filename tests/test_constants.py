"""Tests for chuk_mcp_her.constants."""

from __future__ import annotations


from chuk_mcp_her.constants import (
    DESIGNATION_LAYERS,
    DESIGNATION_TYPES,
    LAYER_DESIGNATION,
    SOURCE_METADATA,
    ErrorMessages,
    NHLELayer,
    ServerConfig,
    SourceId,
    SuccessMessages,
)


class TestServerConfig:
    def test_name(self):
        assert ServerConfig.NAME == "chuk-mcp-her"

    def test_version(self):
        assert ServerConfig.VERSION == "0.3.0"

    def test_description(self):
        assert ServerConfig.DESCRIPTION == "Historic Environment Records"

    def test_is_str_enum(self):
        assert isinstance(ServerConfig.NAME, str)
        assert isinstance(ServerConfig.NAME.value, str)


class TestSourceMetadata:
    def test_has_all_six_sources(self):
        assert "nhle" in SOURCE_METADATA
        assert "aim" in SOURCE_METADATA
        assert "conservation_area" in SOURCE_METADATA
        assert "heritage_at_risk" in SOURCE_METADATA
        assert "heritage_gateway" in SOURCE_METADATA
        assert "scotland" in SOURCE_METADATA
        assert len(SOURCE_METADATA) == 6

    def test_nhle_metadata(self):
        nhle = SOURCE_METADATA["nhle"]
        assert nhle["name"] == "National Heritage List for England"
        assert nhle["organisation"] == "Historic England"
        assert nhle["coverage"] == "England"
        assert nhle["api_type"] == "arcgis_feature_service"
        assert nhle["native_srid"] == 27700
        assert "listed_building" in nhle["designation_types"]
        assert nhle["licence"] == "Open Government Licence"

    def test_aim_metadata(self):
        aim = SOURCE_METADATA["aim"]
        assert aim["name"] == "Aerial Investigation and Mapping"
        assert aim["organisation"] == "Historic England"
        assert aim["api_type"] == "arcgis_feature_service"

    def test_heritage_gateway_metadata(self):
        hg = SOURCE_METADATA["heritage_gateway"]
        assert hg["name"] == "Heritage Gateway (Local HERs)"
        assert hg["api_type"] == "web_scraper"
        assert "note" in hg


class TestSourceId:
    def test_nhle(self):
        assert SourceId.NHLE == "nhle"

    def test_aim(self):
        assert SourceId.AIM == "aim"

    def test_heritage_gateway(self):
        assert SourceId.HERITAGE_GATEWAY == "heritage_gateway"


class TestNHLELayer:
    def test_listed_building_points(self):
        assert NHLELayer.LISTED_BUILDING_POINTS == 0

    def test_listed_building_polygons(self):
        assert NHLELayer.LISTED_BUILDING_POLYGONS == 1

    def test_scheduled_monuments(self):
        assert NHLELayer.SCHEDULED_MONUMENTS == 6

    def test_parks_and_gardens(self):
        assert NHLELayer.PARKS_AND_GARDENS == 7

    def test_battlefields(self):
        assert NHLELayer.BATTLEFIELDS == 8

    def test_protected_wrecks(self):
        assert NHLELayer.PROTECTED_WRECKS == 9

    def test_world_heritage_sites(self):
        assert NHLELayer.WORLD_HERITAGE_SITES == 10

    def test_is_int_enum(self):
        assert isinstance(NHLELayer.LISTED_BUILDING_POINTS, int)


class TestDesignationLayers:
    def test_all_designation_types_present(self):
        assert "listed_building" in DESIGNATION_LAYERS
        assert "scheduled_monument" in DESIGNATION_LAYERS
        assert "park_and_garden" in DESIGNATION_LAYERS
        assert "battlefield" in DESIGNATION_LAYERS
        assert "protected_wreck" in DESIGNATION_LAYERS
        assert "world_heritage_site" in DESIGNATION_LAYERS

    def test_listed_building_maps_to_points_layer(self):
        assert DESIGNATION_LAYERS["listed_building"] == [NHLELayer.LISTED_BUILDING_POINTS]

    def test_scheduled_monument_maps_correctly(self):
        assert DESIGNATION_LAYERS["scheduled_monument"] == [NHLELayer.SCHEDULED_MONUMENTS]


class TestLayerDesignation:
    def test_reverse_mapping_points(self):
        assert LAYER_DESIGNATION[NHLELayer.LISTED_BUILDING_POINTS] == "listed_building"

    def test_reverse_mapping_polygons(self):
        assert LAYER_DESIGNATION[NHLELayer.LISTED_BUILDING_POLYGONS] == "listed_building"

    def test_reverse_mapping_scheduled_monuments(self):
        assert LAYER_DESIGNATION[NHLELayer.SCHEDULED_MONUMENTS] == "scheduled_monument"

    def test_all_layers_have_reverse_mapping(self):
        for layer in NHLELayer:
            assert layer in LAYER_DESIGNATION


class TestDesignationTypes:
    def test_all_types_listed(self):
        assert len(DESIGNATION_TYPES) == 6
        assert "listed_building" in DESIGNATION_TYPES
        assert "scheduled_monument" in DESIGNATION_TYPES
        assert "park_and_garden" in DESIGNATION_TYPES
        assert "battlefield" in DESIGNATION_TYPES
        assert "protected_wreck" in DESIGNATION_TYPES
        assert "world_heritage_site" in DESIGNATION_TYPES


class TestErrorMessages:
    def test_format_source_not_found(self):
        msg = ErrorMessages.SOURCE_NOT_FOUND.format("foo", "nhle, aim")
        assert "foo" in msg
        assert "nhle, aim" in msg

    def test_format_monument_not_found(self):
        msg = ErrorMessages.MONUMENT_NOT_FOUND.format("12345")
        assert "12345" in msg

    def test_format_not_implemented(self):
        msg = ErrorMessages.NOT_IMPLEMENTED.format("aim")
        assert "aim" in msg
        assert "not yet implemented" in msg

    def test_format_invalid_grade(self):
        msg = ErrorMessages.INVALID_GRADE.format("III")
        assert "III" in msg

    def test_format_invalid_designation(self):
        msg = ErrorMessages.INVALID_DESIGNATION.format(
            "castle", "listed_building, scheduled_monument"
        )
        assert "castle" in msg
        assert "listed_building" in msg

    def test_format_arcgis_error(self):
        msg = ErrorMessages.ARCGIS_ERROR.format("timeout")
        assert "timeout" in msg

    def test_no_results_is_string(self):
        assert isinstance(ErrorMessages.NO_RESULTS, str)
        assert "No results" in ErrorMessages.NO_RESULTS


class TestSuccessMessages:
    def test_format_sources_listed(self):
        msg = SuccessMessages.SOURCES_LISTED.format(3)
        assert "3" in msg

    def test_format_monuments_found(self):
        msg = SuccessMessages.MONUMENTS_FOUND.format(42)
        assert "42" in msg

    def test_format_buildings_found(self):
        msg = SuccessMessages.BUILDINGS_FOUND.format(10)
        assert "10" in msg

    def test_format_designations_found(self):
        msg = SuccessMessages.DESIGNATIONS_FOUND.format(5, 100)
        assert "5" in msg
        assert "100" in msg

    def test_format_features_counted(self):
        msg = SuccessMessages.FEATURES_COUNTED.format(170)
        assert "170" in msg

    def test_format_cross_ref_complete(self):
        msg = SuccessMessages.CROSS_REF_COMPLETE.format(3, 2, 1)
        assert "3" in msg
        assert "2" in msg
        assert "1" in msg

    def test_format_nearby_found(self):
        msg = SuccessMessages.NEARBY_FOUND.format(5, 500)
        assert "5" in msg
        assert "500" in msg

    def test_format_export_complete(self):
        msg = SuccessMessages.EXPORT_COMPLETE.format(50)
        assert "50" in msg

    def test_format_server_ok(self):
        msg = SuccessMessages.SERVER_OK.format(3, "England")
        assert "3" in msg
        assert "England" in msg

    def test_format_gateway_enriched(self):
        msg = SuccessMessages.GATEWAY_ENRICHED.format(10, 24)
        assert "10" in msg
        assert "24" in msg

    def test_grid_ref_invalid_exists(self):
        assert "Invalid grid reference" in ErrorMessages.GRID_REF_INVALID
