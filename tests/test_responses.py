"""Tests for chuk_mcp_her.models.responses."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from chuk_mcp_her.models.responses import (
    AerialCountResponse,
    AerialFeatureInfo,
    AerialSearchResponse,
    CapabilitiesResponse,
    CrossReferenceMatch,
    CrossReferenceResponse,
    DesignationInfo,
    DesignationSearchResponse,
    ErrorResponse,
    FeatureCountResponse,
    GatewayEnrichResponse,
    GatewayRecordInfo,
    GatewaySearchResponse,
    GeoJSONExportResponse,
    LiDARExportResponse,
    MonumentDetailResponse,
    MonumentInfo,
    MonumentSearchResponse,
    NearbyAssetInfo,
    NearbyResponse,
    SourceInfo,
    SourceListResponse,
    StatusResponse,
    StatusSourceInfo,
    ToolInfo,
    format_response,
)


class TestFormatResponseJson:
    def test_json_mode_returns_valid_json(self):
        resp = ErrorResponse(error="test error")
        result = format_response(resp, "json")
        parsed = json.loads(result)
        assert parsed["error"] == "test error"

    def test_json_mode_excludes_none(self):
        resp = ErrorResponse(error="test", suggestion=None)
        result = format_response(resp, "json")
        parsed = json.loads(result)
        assert "suggestion" not in parsed

    def test_json_mode_is_default(self):
        resp = ErrorResponse(error="test")
        result_json = format_response(resp, "json")
        result_default = format_response(resp)
        assert result_json == result_default


class TestFormatResponseText:
    def test_text_mode_calls_to_text(self):
        resp = ErrorResponse(error="something broke", suggestion="fix it")
        result = format_response(resp, "text")
        assert "Error: something broke" in result
        assert "Suggestion: fix it" in result

    def test_text_mode_on_model_without_to_text(self):
        """Models without to_text() should fall back to JSON."""
        resp = ToolInfo(name="test_tool", category="test", description="A tool")
        result = format_response(resp, "text")
        # Should still return valid JSON since ToolInfo has no to_text()
        parsed = json.loads(result)
        assert parsed["name"] == "test_tool"


class TestErrorResponse:
    def test_basic_error(self):
        resp = ErrorResponse(error="Something went wrong")
        assert resp.error == "Something went wrong"
        assert resp.error_type == "error"
        assert resp.message == ""

    def test_to_text(self):
        resp = ErrorResponse(error="bad request", suggestion="try again")
        text = resp.to_text()
        assert "Error: bad request" in text
        assert "Suggestion: try again" in text

    def test_to_text_without_suggestion(self):
        resp = ErrorResponse(error="bad request")
        text = resp.to_text()
        assert "Error: bad request" in text
        assert "Suggestion" not in text

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            ErrorResponse(error="test", unknown_field="x")


class TestSourceListResponse:
    def test_to_text(self):
        resp = SourceListResponse(
            sources=[
                SourceInfo(
                    source_id="nhle",
                    name="NHLE",
                    coverage="England",
                    capabilities=["spatial_query"],
                ),
            ],
            count=1,
            message="1 heritage data sources available",
        )
        text = resp.to_text()
        assert "nhle" in text
        assert "NHLE" in text
        assert "England" in text

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            SourceListResponse(sources=[], count=0, unknown="x")


class TestStatusResponse:
    def test_to_text(self):
        resp = StatusResponse(
            server="chuk-mcp-her",
            version="0.2.0",
            sources={
                "nhle": StatusSourceInfo(status="available"),
            },
            tool_count=16,
            message="Server operational",
        )
        text = resp.to_text()
        assert "chuk-mcp-her" in text
        assert "0.2.0" in text
        assert "nhle" in text

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            StatusResponse(server="x", version="0", sources={}, tool_count=0, bonus="y")


class TestCapabilitiesResponse:
    def test_to_text(self):
        resp = CapabilitiesResponse(
            server="chuk-mcp-her",
            version="0.2.0",
            sources=[],
            tools=[
                ToolInfo(name="her_status", category="discovery", description="Status"),
            ],
            tool_count=1,
            llm_guidance="Start with her_status",
            message="1 tools across 0 sources",
        )
        text = resp.to_text()
        assert "her_status" in text
        assert "Start with her_status" in text

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            CapabilitiesResponse(server="x", version="0", sources=[], tools=[], extra_field="bad")


class TestMonumentInfo:
    def test_basic_fields(self):
        m = MonumentInfo(
            record_id="nhle:1000001",
            name="Church of St Mary",
            source="nhle",
            designation_type="listed_building",
            grade="I",
        )
        assert m.record_id == "nhle:1000001"
        assert m.grade == "I"

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            MonumentInfo(record_id="x", name="y", source="z", bonus="bad")


class TestMonumentSearchResponse:
    def test_to_text(self):
        resp = MonumentSearchResponse(
            count=1,
            total_available=100,
            monuments=[
                MonumentInfo(
                    record_id="nhle:1000001",
                    name="Church of St Mary",
                    source="nhle",
                    designation_type="listed_building",
                    grade="I",
                    lat=51.508,
                    lon=-0.076,
                ),
            ],
            has_more=True,
            next_offset=1,
            message="Found 1 scheduled monuments",
        )
        text = resp.to_text()
        assert "Church of St Mary" in text
        assert "Grade I" in text
        assert "51.508" in text

    def test_to_text_with_pagination(self):
        resp = MonumentSearchResponse(
            count=1,
            total_available=50,
            monuments=[
                MonumentInfo(record_id="x", name="y", source="nhle"),
            ],
            has_more=True,
            next_offset=1,
            message="Found 1",
        )
        text = resp.to_text()
        assert "offset=1" in text


class TestMonumentDetailResponse:
    def test_to_text(self):
        resp = MonumentDetailResponse(
            monument={
                "nhle_id": "1000001",
                "name": "Church",
                "designation_type": "listed_building",
                "grade": "I",
                "lat": 51.508,
                "lon": -0.076,
                "list_date": "1967-01-01",
                "url": "https://example.com",
            },
            message="Monument record retrieved",
        )
        text = resp.to_text()
        assert "Church" in text
        assert "Grade: I" in text
        assert "https://example.com" in text


class TestDesignationSearchResponse:
    def test_to_text(self):
        resp = DesignationSearchResponse(
            count=1,
            designations=[
                DesignationInfo(
                    record_id="nhle:1",
                    name="Castle",
                    designation_type="scheduled_monument",
                ),
            ],
            message="1 designations returned",
        )
        text = resp.to_text()
        assert "Castle" in text
        assert "scheduled_monument" in text

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            DesignationSearchResponse(count=0, designations=[], extra="bad")


class TestFeatureCountResponse:
    def test_to_text(self):
        resp = FeatureCountResponse(
            counts={
                "listed_building": 100,
                "scheduled_monument": 10,
                "total": 110,
            },
            message="110 designated heritage assets",
        )
        text = resp.to_text()
        assert "listed_building: 100" in text
        assert "scheduled_monument: 10" in text
        assert "Total: 110" in text


class TestAerialSearchResponse:
    def test_to_text(self):
        resp = AerialSearchResponse(
            count=1,
            total_available=100,
            features=[
                AerialFeatureInfo(
                    record_id="aim:AIM001",
                    aim_id="AIM001",
                    name="ENCLOSURE (IRON AGE)",
                    monument_type="ENCLOSURE",
                    period="IRON AGE",
                    lat=51.770,
                    lon=0.870,
                ),
            ],
            has_more=True,
            next_offset=1,
            message="Found 100 aerial mapping features",
        )
        text = resp.to_text()
        assert "AIM001" in text
        assert "ENCLOSURE" in text
        assert "51.7700" in text
        assert "offset=1" in text

    def test_to_text_no_pagination(self):
        resp = AerialSearchResponse(
            count=1,
            features=[
                AerialFeatureInfo(
                    aim_id="AIM001",
                    monument_type="ENCLOSURE",
                    period="IRON AGE",
                ),
            ],
            message="Found 1",
        )
        text = resp.to_text()
        assert "offset" not in text


class TestAerialCountResponse:
    def test_to_text(self):
        resp = AerialCountResponse(
            count=42,
            message="42 aerial mapping features in area",
        )
        text = resp.to_text()
        assert "42" in text

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            AerialCountResponse(count=0, bonus="bad")


class TestGatewaySearchResponse:
    def test_to_text(self):
        resp = GatewaySearchResponse(
            count=1,
            records=[
                GatewayRecordInfo(
                    record_id="HER001",
                    name="Red Hill",
                    monument_type="Saltern",
                    period="Roman",
                ),
            ],
            note="Scraper-based",
            message="Found 1",
        )
        text = resp.to_text()
        assert "Red Hill" in text
        assert "Scraper-based" in text


class TestGatewayEnrichResponse:
    def test_construction(self):
        resp = GatewayEnrichResponse(
            records=[
                {"record_id": "hg:1", "name": "Red Hill", "easting": 590500.0, "northing": 208500.0}
            ],
            count=1,
            resolved_count=1,
            unresolved_count=2,
            fetch_details_used=True,
            message="Resolved 1 of 3",
        )
        assert resp.count == 1
        assert resp.resolved_count == 1
        assert resp.unresolved_count == 2

    def test_to_text(self):
        resp = GatewayEnrichResponse(
            records=[
                {"record_id": "hg:1", "name": "Red Hill", "easting": 590500.0, "northing": 208500.0}
            ],
            count=1,
            resolved_count=1,
            unresolved_count=0,
            fetch_details_used=True,
            message="Resolved 1 of 1",
        )
        text = resp.to_text()
        assert "Resolved" in text
        assert "E=" in text
        assert "Red Hill" in text

    def test_extra_forbid(self):
        with pytest.raises(ValidationError):
            GatewayEnrichResponse(
                records=[],
                count=0,
                resolved_count=0,
                unresolved_count=0,
                fetch_details_used=False,
                extra_field="bad",
            )


class TestCrossReferenceResponse:
    def test_to_text(self):
        resp = CrossReferenceResponse(
            candidates_submitted=3,
            classification={"match": 1, "near": 1, "novel": 1},
            message="Cross-reference complete",
        )
        text = resp.to_text()
        assert "Submitted: 3" in text
        assert "Matches: 1" in text
        assert "Near: 1" in text
        assert "Novel: 1" in text


class TestNearbyResponse:
    def test_to_text(self):
        resp = NearbyResponse(
            centre_lat=51.508,
            centre_lon=-0.076,
            radius_m=500,
            count=1,
            assets=[
                NearbyAssetInfo(
                    record_id="nhle:1",
                    name="Church",
                    distance_m=120.5,
                ),
            ],
            message="1 heritage assets within 500m",
        )
        text = resp.to_text()
        assert "Church" in text
        assert "120m" in text  # formatted as integer in f-string


class TestGeoJSONExportResponse:
    def test_to_text(self):
        resp = GeoJSONExportResponse(
            geojson={"type": "FeatureCollection", "features": []},
            feature_count=42,
            message="Exported 42 features",
        )
        text = resp.to_text()
        assert "42 features" in text


class TestLiDARExportResponse:
    def test_to_text(self):
        sites = [
            {"id": f"nhle:{i}", "name": f"Site {i}", "type": "scheduled_monument"}
            for i in range(15)
        ]
        resp = LiDARExportResponse(
            bbox=[530000, 170000, 540000, 190000],
            known_sites=sites,
            count=15,
            message="15 known sites exported",
        )
        text = resp.to_text()
        assert "Site 0" in text
        assert "... and 5 more" in text

    def test_to_text_few_sites(self):
        resp = LiDARExportResponse(
            bbox=[530000, 170000, 540000, 190000],
            known_sites=[{"id": "nhle:1", "name": "One", "type": "sm"}],
            count=1,
            message="1 known site",
        )
        text = resp.to_text()
        assert "One" in text
        assert "more" not in text


class TestExtraForbidOnAllModels:
    """Verify extra='forbid' raises ValidationError on all response models."""

    def test_source_info_extra_forbid(self):
        with pytest.raises(ValidationError):
            SourceInfo(source_id="x", name="y", bonus="bad")

    def test_monument_info_extra_forbid(self):
        with pytest.raises(ValidationError):
            MonumentInfo(record_id="x", name="y", source="z", bonus="bad")

    def test_designation_info_extra_forbid(self):
        with pytest.raises(ValidationError):
            DesignationInfo(record_id="x", name="y", designation_type="z", bonus="bad")

    def test_nearby_asset_info_extra_forbid(self):
        with pytest.raises(ValidationError):
            NearbyAssetInfo(record_id="x", name="y", bonus="bad")

    def test_aerial_feature_info_extra_forbid(self):
        with pytest.raises(ValidationError):
            AerialFeatureInfo(bonus="bad")

    def test_gateway_record_info_extra_forbid(self):
        with pytest.raises(ValidationError):
            GatewayRecordInfo(bonus="bad")

    def test_tool_info_extra_forbid(self):
        with pytest.raises(ValidationError):
            ToolInfo(name="x", category="y", description="z", bonus="bad")

    def test_cross_reference_match_extra_forbid(self):
        with pytest.raises(ValidationError):
            CrossReferenceMatch(
                candidate={"easting": 0, "northing": 0},
                classification="match",
                bonus="bad",
            )
