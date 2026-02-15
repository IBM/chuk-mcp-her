"""Tests for chuk_mcp_her.core.source_registry."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from chuk_mcp_her.core.adapters.aim import AIMAdapter
from chuk_mcp_her.core.adapters.base import PaginatedResult, SourceCapabilities
from chuk_mcp_her.core.adapters.conservation_area import ConservationAreaAdapter
from chuk_mcp_her.core.adapters.heritage_at_risk import HeritageAtRiskAdapter
from chuk_mcp_her.core.adapters.heritage_gateway import HeritageGatewayAdapter
from chuk_mcp_her.core.adapters.nhle import NHLEAdapter
from chuk_mcp_her.core.source_registry import SourceRegistry


class TestSourceRegistryListSources:
    def test_returns_five_sources(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        sources = registry.list_sources()
        assert len(sources) == 5

    def test_source_ids(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        sources = registry.list_sources()
        ids = [s["id"] for s in sources]
        assert "nhle" in ids
        assert "aim" in ids
        assert "conservation_area" in ids
        assert "heritage_at_risk" in ids
        assert "heritage_gateway" in ids

    def test_nhle_source_has_metadata(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        sources = registry.list_sources()
        nhle = next(s for s in sources if s["id"] == "nhle")
        assert nhle["name"] == "National Heritage List for England"
        assert nhle["organisation"] == "Historic England"
        assert nhle["coverage"] == "England"
        assert "spatial_query" in nhle["capabilities"]
        assert "text_search" in nhle["capabilities"]

    def test_source_has_status(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        sources = registry.list_sources()
        for source in sources:
            assert "status" in source
            assert source["status"] in ("available", "stub", "unavailable")


class TestSourceRegistryGetAdapter:
    def test_get_nhle_adapter(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("nhle")
        assert adapter is not None
        assert isinstance(adapter, NHLEAdapter)

    def test_get_aim_adapter(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("aim")
        assert adapter is not None
        assert isinstance(adapter, AIMAdapter)

    def test_get_heritage_gateway_adapter(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("heritage_gateway")
        assert adapter is not None
        assert isinstance(adapter, HeritageGatewayAdapter)

    def test_get_unknown_adapter_returns_none(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("nonexistent")
        assert adapter is None


class TestSourceRegistrySearchMonuments:
    async def test_delegates_to_nhle_adapter(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        # Mock the NHLE adapter's search method
        mock_result = PaginatedResult(
            features=[
                {
                    "record_id": "nhle:1000002",
                    "name": "Test Monument",
                    "source": "nhle",
                    "designation_type": "scheduled_monument",
                }
            ],
            total_count=1,
            has_more=False,
        )
        nhle_adapter = registry.get_adapter("nhle")
        nhle_adapter.search = AsyncMock(return_value=mock_result)

        result = await registry.search_monuments(query="Test")
        assert len(result.features) == 1
        assert result.features[0]["name"] == "Test Monument"

        # Verify search was called with scheduled_monument designation
        nhle_adapter.search.assert_called_once()
        call_kwargs = nhle_adapter.search.call_args[1]
        assert call_kwargs["designation_type"] == "scheduled_monument"
        assert call_kwargs["query"] == "Test"

    async def test_search_monuments_with_bbox(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(features=[], total_count=0, has_more=False)
        nhle_adapter = registry.get_adapter("nhle")
        nhle_adapter.search = AsyncMock(return_value=mock_result)

        bbox = (530000.0, 170000.0, 540000.0, 190000.0)
        result = await registry.search_monuments(bbox=bbox)
        assert result.total_count == 0
        call_kwargs = nhle_adapter.search.call_args[1]
        assert call_kwargs["bbox"] == bbox


class TestSourceRegistrySearchListedBuildings:
    async def test_delegates_with_listed_building_type(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(
            features=[{"record_id": "nhle:1", "name": "Church"}],
            total_count=1,
            has_more=False,
        )
        nhle_adapter = registry.get_adapter("nhle")
        nhle_adapter.search = AsyncMock(return_value=mock_result)

        await registry.search_listed_buildings(query="Church", grade="I")
        call_kwargs = nhle_adapter.search.call_args[1]
        assert call_kwargs["designation_type"] == "listed_building"
        assert call_kwargs["grade"] == "I"


class TestSourceRegistryCountFeatures:
    async def test_count_all_types(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        nhle_adapter = registry.get_adapter("nhle")
        nhle_adapter.count = AsyncMock(return_value=5)

        result = await registry.count_features()
        assert "total" in result
        assert result["total"] > 0

    async def test_count_single_type(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        nhle_adapter = registry.get_adapter("nhle")
        nhle_adapter.count = AsyncMock(return_value=42)

        result = await registry.count_features(designation_type="scheduled_monument")
        assert result["scheduled_monument"] == 42
        assert result["total"] == 42


class TestAdapterCapabilities:
    def test_aim_adapter_is_registered(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        aim = registry.get_adapter("aim")
        assert aim is not None
        assert aim.source_id == "aim"

    def test_aim_capabilities(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        aim = registry.get_adapter("aim")
        cap = aim.capabilities
        assert cap.supports_spatial_query is True
        assert cap.supports_text_search is True
        assert cap.supports_feature_count is True

    def test_conservation_area_adapter_is_registered(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        ca = registry.get_adapter("conservation_area")
        assert ca is not None
        assert isinstance(ca, ConservationAreaAdapter)
        assert ca.source_id == "conservation_area"

    def test_conservation_area_capabilities(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        ca = registry.get_adapter("conservation_area")
        cap = ca.capabilities
        assert cap.supports_spatial_query is True
        assert cap.supports_text_search is True
        assert cap.supports_feature_count is True
        assert cap.supports_pagination is True

    def test_heritage_at_risk_adapter_is_registered(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        har = registry.get_adapter("heritage_at_risk")
        assert har is not None
        assert isinstance(har, HeritageAtRiskAdapter)
        assert har.source_id == "heritage_at_risk"

    def test_heritage_at_risk_capabilities(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        har = registry.get_adapter("heritage_at_risk")
        cap = har.capabilities
        assert cap.supports_spatial_query is True
        assert cap.supports_text_search is True
        assert cap.supports_feature_count is True
        assert cap.supports_attribute_filter is True

    def test_heritage_gateway_adapter_is_registered(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        hg = registry.get_adapter("heritage_gateway")
        assert hg is not None
        assert isinstance(hg, HeritageGatewayAdapter)
        assert hg.source_id == "heritage_gateway"

    def test_heritage_gateway_capabilities(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        hg = registry.get_adapter("heritage_gateway")
        cap = hg.capabilities
        assert cap.supports_text_search is True
        assert cap.supports_spatial_query is False


class TestSourceRegistryNearby:
    async def test_nearby_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(
            features=[{"record_id": "nhle:1", "name": "Nearby Asset"}],
            total_count=1,
            has_more=False,
        )
        nhle_adapter = registry.get_adapter("nhle")
        nhle_adapter.search = AsyncMock(return_value=mock_result)

        result = await registry.nearby(lat=51.508, lon=-0.076, radius_m=500)
        assert len(result.features) == 1


class TestSourceRegistryClose:
    async def test_close_all_adapters(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        # Mock close on all adapters
        for sid in ["nhle", "aim", "conservation_area", "heritage_at_risk", "heritage_gateway"]:
            adapter = registry.get_adapter(sid)
            adapter.close = AsyncMock()

        await registry.close()
        # Verify close was called on each adapter
        for sid in ["nhle", "aim", "conservation_area", "heritage_at_risk", "heritage_gateway"]:
            adapter = registry.get_adapter(sid)
            adapter.close.assert_called_once()


class TestSourceRegistryGetMonument:
    async def test_get_monument_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("nhle")
        adapter.get_by_id = AsyncMock(return_value={"record_id": "nhle:1", "name": "Test"})
        result = await registry.get_monument("1000001")
        assert result["name"] == "Test"
        adapter.get_by_id.assert_called_once_with("1000001")


class TestSourceRegistrySearchDesignations:
    async def test_search_designations_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(features=[{"name": "Test"}], total_count=1, has_more=False)
        adapter = registry.get_adapter("nhle")
        adapter.search = AsyncMock(return_value=mock_result)
        result = await registry.search_designations(
            query="test", designation_type="listed_building"
        )
        assert len(result.features) == 1
        call_kwargs = adapter.search.call_args[1]
        assert call_kwargs["designation_type"] == "listed_building"


class TestSourceRegistryAerial:
    async def test_search_aerial_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(
            features=[{"name": "Enclosure"}], total_count=1, has_more=False
        )
        adapter = registry.get_adapter("aim")
        adapter.search = AsyncMock(return_value=mock_result)
        result = await registry.search_aerial(monument_type="ENCLOSURE", period="IRON AGE")
        assert len(result.features) == 1

    async def test_get_aerial_feature_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("aim")
        adapter.get_by_id = AsyncMock(return_value={"record_id": "aim:1"})
        result = await registry.get_aerial_feature("aim:1")
        assert result["record_id"] == "aim:1"

    async def test_count_aerial_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("aim")
        adapter.count = AsyncMock(return_value=42)
        result = await registry.count_aerial(monument_type="ENCLOSURE")
        assert result == 42


class TestSourceRegistryConservationArea:
    async def test_search_conservation_areas_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(features=[{"name": "CA"}], total_count=1, has_more=False)
        adapter = registry.get_adapter("conservation_area")
        adapter.search = AsyncMock(return_value=mock_result)
        result = await registry.search_conservation_areas(query="test", lpa="Maldon")
        assert len(result.features) == 1

    async def test_get_conservation_area_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("conservation_area")
        adapter.get_by_id = AsyncMock(return_value={"record_id": "ca:1"})
        result = await registry.get_conservation_area("ca:1")
        assert result["record_id"] == "ca:1"

    async def test_count_conservation_areas_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("conservation_area")
        adapter.count = AsyncMock(return_value=25)
        result = await registry.count_conservation_areas(lpa="Maldon")
        assert result == 25


class TestSourceRegistryHeritageAtRisk:
    async def test_search_heritage_at_risk_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(features=[{"name": "HAR"}], total_count=1, has_more=False)
        adapter = registry.get_adapter("heritage_at_risk")
        adapter.search = AsyncMock(return_value=mock_result)
        result = await registry.search_heritage_at_risk(heritage_category="Listed Building")
        assert len(result.features) == 1

    async def test_get_heritage_at_risk_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("heritage_at_risk")
        adapter.get_by_id = AsyncMock(return_value={"record_id": "har:1"})
        result = await registry.get_heritage_at_risk("har:1")
        assert result["record_id"] == "har:1"

    async def test_count_heritage_at_risk_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        adapter = registry.get_adapter("heritage_at_risk")
        adapter.count = AsyncMock(return_value=15)
        result = await registry.count_heritage_at_risk(heritage_category="Listed Building")
        assert result == 15


class TestSourceRegistryGateway:
    async def test_search_heritage_gateway_delegates(self, tmp_path):
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_result = PaginatedResult(features=[{"name": "HER"}], total_count=1, has_more=False)
        adapter = registry.get_adapter("heritage_gateway")
        adapter.search = AsyncMock(return_value=mock_result)
        result = await registry.search_heritage_gateway(what="red hill", where="Essex")
        assert len(result.features) == 1


class TestSourceRegistryStubStatus:
    def test_stub_source_detected(self, tmp_path):
        """Source with no spatial or text support should be marked 'stub'."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        mock_adapter = MagicMock()
        mock_adapter.capabilities = SourceCapabilities(
            supports_spatial_query=False,
            supports_text_search=False,
        )
        registry._adapters["nhle"] = mock_adapter

        sources = registry.list_sources()
        nhle = next(s for s in sources if s["id"] == "nhle")
        assert nhle["status"] == "stub"


class TestSourceRegistryEnrichGateway:
    async def test_enrich_with_existing_coords(self, tmp_path):
        """Records with easting/northing should be enriched directly."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site A", "easting": 533500.0, "northing": 180500.0}],
                total_count=1,
                has_more=False,
            )
        )
        enriched, total = await registry.enrich_gateway_records(what="test")
        assert total == 1
        assert len(enriched) == 1
        assert enriched[0]["easting"] == 533500.0

    async def test_enrich_with_valid_grid_ref(self, tmp_path):
        """Records with valid grid reference should get coords resolved."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site B", "grid_reference": "TQ 336 805"}],
                total_count=1,
                has_more=False,
            )
        )
        enriched, total = await registry.enrich_gateway_records(what="test")
        assert total == 1
        assert len(enriched) == 1
        assert enriched[0]["easting"] is not None

    async def test_enrich_invalid_grid_ref_no_fetch(self, tmp_path):
        """Invalid grid ref without fetch_details should not be enriched."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site C", "grid_reference": "INVALID"}],
                total_count=1,
                has_more=False,
            )
        )
        enriched, total = await registry.enrich_gateway_records(what="test")
        assert total == 1
        assert len(enriched) == 0

    async def test_enrich_fetch_details_with_coords(self, tmp_path):
        """fetch_details=True with detail page having coords."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site D", "url": "https://example.com/d"}],
                total_count=1,
                has_more=False,
            )
        )
        gw.get_by_id = AsyncMock(
            return_value={
                "easting": 533500.0,
                "northing": 180500.0,
                "grid_reference": "TQ 336 805",
            }
        )
        enriched, total = await registry.enrich_gateway_records(what="test", fetch_details=True)
        assert total == 1
        assert len(enriched) == 1
        assert enriched[0]["easting"] == 533500.0
        assert enriched[0]["grid_reference"] == "TQ 336 805"

    async def test_enrich_fetch_details_with_grid_ref(self, tmp_path):
        """fetch_details=True, detail page has grid ref but no coords."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site E", "url": "https://example.com/e"}],
                total_count=1,
                has_more=False,
            )
        )
        gw.get_by_id = AsyncMock(return_value={"grid_reference": "TQ 336 805"})
        enriched, total = await registry.enrich_gateway_records(what="test", fetch_details=True)
        assert total == 1
        assert len(enriched) == 1
        assert enriched[0]["easting"] is not None
        assert enriched[0]["grid_reference"] == "TQ 336 805"

    async def test_enrich_fetch_details_invalid_grid_ref(self, tmp_path):
        """fetch_details=True, detail page has invalid grid ref."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site F", "url": "https://example.com/f"}],
                total_count=1,
                has_more=False,
            )
        )
        gw.get_by_id = AsyncMock(return_value={"grid_reference": "INVALID"})
        enriched, total = await registry.enrich_gateway_records(what="test", fetch_details=True)
        assert total == 1
        assert len(enriched) == 0

    async def test_enrich_fetch_details_none_result(self, tmp_path):
        """fetch_details=True, detail page returns None."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site G", "url": "https://example.com/g"}],
                total_count=1,
                has_more=False,
            )
        )
        gw.get_by_id = AsyncMock(return_value=None)
        enriched, total = await registry.enrich_gateway_records(what="test", fetch_details=True)
        assert total == 1
        assert len(enriched) == 0

    async def test_enrich_no_url_no_coords_no_gridref(self, tmp_path):
        """Record with no coords, no grid ref, and no URL is not enriched."""
        registry = SourceRegistry(cache_dir=str(tmp_path))
        gw = registry.get_adapter("heritage_gateway")
        gw.search = AsyncMock(
            return_value=PaginatedResult(
                features=[{"name": "Site H"}],
                total_count=1,
                has_more=False,
            )
        )
        enriched, total = await registry.enrich_gateway_records(what="test")
        assert total == 1
        assert len(enriched) == 0
