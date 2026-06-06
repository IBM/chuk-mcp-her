"""Shared fixtures for chuk-mcp-her tests."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from chuk_mcp_her.core.adapters.base import PaginatedResult


class MockMCPServer:
    """Minimal MCP server mock that captures tools registered via @mcp.tool or view_tool."""

    def __init__(self) -> None:
        self._tools: dict[str, Any] = {}

    def tool(self, fn: Any = None, **kwargs: Any) -> Any:
        if fn is not None and callable(fn):
            # Direct decorator: @mcp.tool
            self._tools[fn.__name__] = fn
            return fn
        else:
            # Called with kwargs: mcp.tool(name=..., ...)(fn)
            tool_name = kwargs.get("name")

            def decorator(f: Any) -> Any:
                name = tool_name or f.__name__
                self._tools[name] = f
                return f

            return decorator

    def view_tool(self, **kwargs: Any) -> Any:
        """Support ChukMCPServer.view_tool(**vt_kwargs)(wrapper) pattern."""
        tool_name = kwargs.get("name")

        def decorator(f: Any) -> Any:
            name = tool_name or f.__name__
            self._tools[name] = f
            return f

        return decorator

    def get_tool(self, name: str) -> Any:
        return self._tools[name]

    def get_tools(self) -> list[Any]:
        return list(self._tools.values())

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())


@pytest.fixture
def mock_mcp() -> MockMCPServer:
    return MockMCPServer()


# Sample NHLE features (as returned by NHLEAdapter._normalize_feature)
SAMPLE_NHLE_FEATURES = [
    {
        "record_id": "nhle:1000001",
        "nhle_id": "1000001",
        "name": "Church of St Mary",
        "source": "nhle",
        "designation_type": "listed_building",
        "grade": "I",
        "list_date": "1967-01-01",
        "amendment_date": None,
        "easting": 533500.0,
        "northing": 180500.0,
        "lat": 51.508,
        "lon": -0.076,
        "url": "https://historicengland.org.uk/listing/the-list/list-entry/1000001",
    },
    {
        "record_id": "nhle:1000002",
        "nhle_id": "1000002",
        "name": "Red Hill 200m NE of Bounds Farm",
        "source": "nhle",
        "designation_type": "scheduled_monument",
        "grade": None,
        "list_date": "1978-03-15",
        "amendment_date": "2002-11-01",
        "easting": 590625.0,
        "northing": 208193.0,
        "lat": 51.754,
        "lon": 0.812,
        "url": "https://historicengland.org.uk/listing/the-list/list-entry/1000002",
    },
    {
        "record_id": "nhle:1000003",
        "nhle_id": "1000003",
        "name": "Tollesbury Wick Marshes: five red hills",
        "source": "nhle",
        "designation_type": "scheduled_monument",
        "grade": None,
        "list_date": "1995-06-20",
        "amendment_date": None,
        "easting": 596100.0,
        "northing": 211850.0,
        "lat": 51.787,
        "lon": 0.893,
        "url": "https://historicengland.org.uk/listing/the-list/list-entry/1000003",
    },
]

# Sample ArcGIS GeoJSON response
SAMPLE_ARCGIS_GEOJSON = {
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

SAMPLE_ARCGIS_COUNT = {"count": 42}

# Sample AIM features (as returned by AIMAdapter._normalize_feature)
SAMPLE_AIM_FEATURES = [
    {
        "record_id": "aim:AIM001",
        "aim_id": "AIM001",
        "name": "ENCLOSURE (IRON AGE)",
        "source": "aim",
        "monument_type": "ENCLOSURE",
        "broad_type": "ENCLOSURE",
        "narrow_type": "ENCLOSURE: OVAL",
        "period": "IRON AGE",
        "form": "Cropmark",
        "evidence": "Cropmark",
        "project": "Essex NMP",
        "her_no": "HER001",
        "easting": 594500.0,
        "northing": 210000.0,
        "lat": 51.770,
        "lon": 0.870,
    },
    {
        "record_id": "aim:AIM002",
        "aim_id": "AIM002",
        "name": "SALTERN MOUND (ROMAN)",
        "source": "aim",
        "monument_type": "SALTERN MOUND",
        "broad_type": "INDUSTRIAL",
        "narrow_type": "SALTERN MOUND",
        "period": "ROMAN",
        "form": "Earthwork",
        "evidence": "Earthwork",
        "project": "Essex NMP",
        "her_no": "HER002",
        "easting": 596100.0,
        "northing": 211850.0,
        "lat": 51.787,
        "lon": 0.893,
    },
]

# Sample AIM ArcGIS GeoJSON response (polygon features)
SAMPLE_AIM_ARCGIS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "HE_UID": "AIM001",
                "MONUMENT_TYPE": "ENCLOSURE",
                "BROAD_TYPE": "ENCLOSURE",
                "NARROW_TYPE": "ENCLOSURE: OVAL",
                "PERIOD": "IRON AGE",
                "FORM": "Cropmark",
                "EVIDENCE_1": "Cropmark",
                "PROJECT": "Essex NMP",
                "HER_NO": "HER001",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [594400.0, 209900.0],
                        [594600.0, 209900.0],
                        [594600.0, 210100.0],
                        [594400.0, 210100.0],
                        [594400.0, 209900.0],
                    ]
                ],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "HE_UID": "AIM002",
                "MONUMENT_TYPE": "SALTERN MOUND",
                "BROAD_TYPE": "INDUSTRIAL",
                "NARROW_TYPE": "SALTERN MOUND",
                "PERIOD": "ROMAN",
                "FORM": "Earthwork",
                "EVIDENCE_1": "Earthwork",
                "PROJECT": "Essex NMP",
                "HER_NO": "HER002",
            },
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [596000.0, 211750.0],
                        [596200.0, 211750.0],
                        [596200.0, 211950.0],
                        [596000.0, 211950.0],
                        [596000.0, 211750.0],
                    ]
                ],
            },
        },
    ],
}


# Sample Conservation Area features
SAMPLE_CONSERVATION_AREA_FEATURES = [
    {
        "record_id": "ca:1001",
        "uid": 1001,
        "name": "Maldon Conservation Area",
        "lpa": "Maldon District Council",
        "designation_date": "1969-01-01",
        "easting": 585200.0,
        "northing": 207100.0,
        "lat": 51.732,
        "lon": 0.677,
        "area_sqm": 125000.0,
    },
    {
        "record_id": "ca:1002",
        "uid": 1002,
        "name": "Heybridge Basin Conservation Area",
        "lpa": "Maldon District Council",
        "designation_date": "1984-06-15",
        "easting": 586800.0,
        "northing": 207300.0,
        "lat": 51.734,
        "lon": 0.700,
        "area_sqm": 45000.0,
    },
]

# Sample Heritage at Risk features
SAMPLE_HERITAGE_AT_RISK_FEATURES = [
    {
        "record_id": "har:1021506",
        "list_entry": 1021506,
        "name": "Church of All Saints, Maldon",
        "heritage_category": "Listed Building",
        "risk_methodology": "Priority Category A",
        "lat": 51.731,
        "lon": 0.675,
        "area_sqm": None,
        "url": "https://historicengland.org.uk/advice/heritage-at-risk/search-register/list-entry/1021506",
    },
    {
        "record_id": "har:1022344",
        "list_entry": 1022344,
        "name": "Beeleigh Abbey, Maldon",
        "heritage_category": "Scheduled Monument",
        "risk_methodology": "Priority Category B",
        "lat": 51.728,
        "lon": 0.660,
        "area_sqm": 8500.0,
        "url": "https://historicengland.org.uk/advice/heritage-at-risk/search-register/list-entry/1022344",
    },
]

# Sample Heritage Gateway features
SAMPLE_GATEWAY_FEATURES = [
    {
        "record_id": "hg:MEX1001",
        "name": "Red Hill, Goldhanger",
        "source_her": "Essex HER",
        "monument_type": "Red Hill",
        "period": "Roman",
        "description": "A red hill mound indicating salt production",
        "grid_reference": "TL 9050 0850",
        "easting": 590500.0,
        "northing": 208500.0,
        "lat": None,
        "lon": None,
        "designation": None,
        "url": "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001",
    },
    {
        "record_id": "hg:MEX1002",
        "name": "Saltern mound, Tollesbury",
        "source_her": "Essex HER",
        "monument_type": "Saltern",
        "period": "Iron Age",
        "description": "Remains of salt production site",
        "grid_reference": "TL 9610 1185",
        "easting": 596100.0,
        "northing": 211850.0,
        "lat": None,
        "lon": None,
        "designation": None,
        "url": "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1002",
    },
]


# Sample Scotland NRHE features (as returned by ScotlandAdapter._normalize_nrhe_feature)
SAMPLE_SCOTLAND_NRHE_FEATURES = [
    {
        "record_id": "scotland:12345",
        "canmore_id": "12345",
        "site_number": "NT27SE 1",
        "name": "Edinburgh Castle",
        "alt_name": None,
        "source": "scotland",
        "broad_class": "SECULAR",
        "site_type": "CASTLE",
        "form": "Building",
        "county": "Midlothian",
        "council": "City of Edinburgh",
        "parish": "Edinburgh",
        "grid_reference": "NT 2520 7348",
        "easting": 325200.0,
        "northing": 673480.0,
        "lat": 55.948611,
        "lon": -3.199444,
        "url": "https://canmore.org.uk/site/12345",
    },
    {
        "record_id": "scotland:67890",
        "canmore_id": "67890",
        "site_number": "NH55NW 1",
        "name": "Clava Cairns",
        "alt_name": "Balnuaran of Clava",
        "source": "scotland",
        "broad_class": "RELIGIOUS AND FUNERARY",
        "site_type": "CAIRN",
        "form": "Earthwork",
        "county": "Inverness-shire",
        "council": "Highland",
        "parish": "Inverness and Bona",
        "grid_reference": "NH 7571 4449",
        "easting": 275710.0,
        "northing": 844490.0,
        "lat": 57.473333,
        "lon": -4.073611,
        "url": "https://canmore.org.uk/site/67890",
    },
]

# Sample Scotland NRHE ArcGIS GeoJSON response
SAMPLE_SCOTLAND_NRHE_ARCGIS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "CANMOREID": "12345",
                "SITENUMBER": "NT27SE 1",
                "NMRSNAME": "Edinburgh Castle",
                "ALTNAME": None,
                "BROADCLASS": "SECULAR",
                "SITETYPE": "CASTLE",
                "FORM": "Building",
                "COUNTY": "Midlothian",
                "COUNCIL": "City of Edinburgh",
                "PARISH": "Edinburgh",
                "GRIDREF": "NT 2520 7348",
                "URL": "https://canmore.org.uk/site/12345",
                "XCOORD": 325200.0,
                "YCOORD": 673480.0,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [325200.0, 673480.0],
            },
        },
        {
            "type": "Feature",
            "properties": {
                "CANMOREID": "67890",
                "SITENUMBER": "NH55NW 1",
                "NMRSNAME": "Clava Cairns",
                "ALTNAME": "Balnuaran of Clava",
                "BROADCLASS": "RELIGIOUS AND FUNERARY",
                "SITETYPE": "CAIRN",
                "FORM": "Earthwork",
                "COUNTY": "Inverness-shire",
                "COUNCIL": "Highland",
                "PARISH": "Inverness and Bona",
                "GRIDREF": "NH 7571 4449",
                "URL": "https://canmore.org.uk/site/67890",
                "XCOORD": 275710.0,
                "YCOORD": 844490.0,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [275710.0, 844490.0],
            },
        },
    ],
}

# Sample Scotland designation features
SAMPLE_SCOTLAND_DESIGNATION_FEATURES = [
    {
        "record_id": "scotland_des:LB12345",
        "designation_reference": "LB12345",
        "name": "St Giles Cathedral",
        "source": "scotland",
        "designation_type": "listed_building",
        "category": "A",
        "designated_date": "1970-01-01",
        "local_authority": "City of Edinburgh",
        "easting": 325700.0,
        "northing": 673600.0,
        "lat": 55.949722,
        "lon": -3.191667,
        "url": "https://portal.historicenvironment.scot/designation/LB12345",
    },
]

# Sample Scotland designation ArcGIS GeoJSON response
SAMPLE_SCOTLAND_DESIGNATION_ARCGIS_GEOJSON = {
    "type": "FeatureCollection",
    "features": [
        {
            "type": "Feature",
            "properties": {
                "DES_REF": "LB12345",
                "DES_TITLE": "St Giles Cathedral",
                "DES_TYPE": "Listed Building",
                "CATEGORY": "A",
                "DESIGNATED": "1970-01-01",
                "LOCAL_AUTH": "City of Edinburgh",
                "LINK": "https://portal.historicenvironment.scot/designation/LB12345",
                "X": 325700.0,
                "Y": 673600.0,
            },
            "geometry": {
                "type": "Point",
                "coordinates": [325700.0, 673600.0],
            },
        },
    ],
}


@pytest.fixture
def mock_registry():
    """Create a mock SourceRegistry with canned responses."""
    registry = MagicMock()

    # list_sources returns source metadata
    registry.list_sources.return_value = [
        {
            "id": "nhle",
            "name": "National Heritage List for England",
            "organisation": "Historic England",
            "coverage": "England",
            "api_type": "arcgis_feature_service",
            "description": "Designated heritage assets",
            "native_srid": 27700,
            "capabilities": ["spatial_query", "text_search", "feature_count"],
            "designation_types": ["listed_building", "scheduled_monument"],
            "licence": "Open Government Licence",
            "status": "available",
        },
        {
            "id": "aim",
            "name": "Aerial Investigation and Mapping",
            "organisation": "Historic England",
            "coverage": "England",
            "api_type": "arcgis_feature_service",
            "capabilities": ["spatial_query"],
            "status": "available",
        },
        {
            "id": "conservation_area",
            "name": "Conservation Areas",
            "organisation": "Historic England / Local Planning Authorities",
            "coverage": "England",
            "api_type": "arcgis_feature_service",
            "capabilities": ["spatial_query", "text_search", "feature_count"],
            "status": "available",
        },
        {
            "id": "heritage_at_risk",
            "name": "Heritage at Risk Register",
            "organisation": "Historic England",
            "coverage": "England",
            "api_type": "arcgis_feature_service",
            "capabilities": ["spatial_query", "text_search", "feature_count"],
            "status": "available",
        },
        {
            "id": "heritage_gateway",
            "name": "Heritage Gateway (Local HERs)",
            "organisation": "Historic England / Local HERs",
            "coverage": "England",
            "api_type": "web_scraper",
            "capabilities": ["text_search"],
            "status": "available",
            "note": "Scraper-based — best-effort access",
        },
        {
            "id": "scotland",
            "name": "Historic Environment Scotland",
            "organisation": "Historic Environment Scotland",
            "coverage": "Scotland",
            "api_type": "arcgis_map_service",
            "capabilities": ["spatial_query", "text_search", "attribute_filter"],
            "designation_types": [
                "listed_building",
                "scheduled_monument",
                "garden_designed_landscape",
                "battlefield",
                "world_heritage_site",
                "conservation_area",
                "historic_marine_protected_area",
            ],
            "status": "available",
        },
    ]

    # search_monuments / search_listed_buildings / search_designations
    registry.search_monuments = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_NHLE_FEATURES[1:],
            total_count=2,
            has_more=False,
        )
    )
    registry.search_listed_buildings = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_NHLE_FEATURES[:1],
            total_count=1,
            has_more=False,
        )
    )
    registry.search_designations = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_NHLE_FEATURES,
            total_count=3,
            has_more=False,
        )
    )

    # get_monument
    registry.get_monument = AsyncMock(return_value=SAMPLE_NHLE_FEATURES[0])

    # count_features
    registry.count_features = AsyncMock(
        return_value={
            "listed_building": 156,
            "scheduled_monument": 12,
            "park_and_garden": 2,
            "battlefield": 0,
            "protected_wreck": 0,
            "world_heritage_site": 0,
            "total": 170,
        }
    )

    # nearby
    registry.nearby = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_NHLE_FEATURES,
            total_count=3,
            has_more=False,
        )
    )

    # Aerial (AIM) tools
    registry.search_aerial = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_AIM_FEATURES,
            total_count=2,
            has_more=False,
        )
    )
    registry.get_aerial_feature = AsyncMock(return_value=SAMPLE_AIM_FEATURES[0])
    registry.count_aerial = AsyncMock(return_value=42)

    # Conservation Area tools
    registry.search_conservation_areas = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_CONSERVATION_AREA_FEATURES,
            total_count=2,
            has_more=False,
        )
    )
    registry.get_conservation_area = AsyncMock(return_value=SAMPLE_CONSERVATION_AREA_FEATURES[0])
    registry.count_conservation_areas = AsyncMock(return_value=25)

    # Heritage at Risk tools
    registry.search_heritage_at_risk = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_HERITAGE_AT_RISK_FEATURES,
            total_count=2,
            has_more=False,
        )
    )
    registry.get_heritage_at_risk = AsyncMock(return_value=SAMPLE_HERITAGE_AT_RISK_FEATURES[0])
    registry.count_heritage_at_risk = AsyncMock(return_value=15)

    # Heritage Gateway tools
    registry.search_heritage_gateway = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_GATEWAY_FEATURES,
            total_count=2,
            has_more=False,
        )
    )

    # Scotland tools
    registry.search_scotland = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_SCOTLAND_NRHE_FEATURES,
            total_count=2,
            has_more=False,
        )
    )
    registry.get_scotland_record = AsyncMock(return_value=SAMPLE_SCOTLAND_NRHE_FEATURES[0])
    registry.search_scotland_designations = AsyncMock(
        return_value=PaginatedResult(
            features=SAMPLE_SCOTLAND_DESIGNATION_FEATURES,
            total_count=1,
            has_more=False,
        )
    )

    # Gateway enrichment (returns tuple: enriched_records, total_searched)
    registry.enrich_gateway_records = AsyncMock(
        return_value=(
            [
                {
                    "record_id": "hg:MEX1001",
                    "name": "Red Hill, Goldhanger",
                    "source": "heritage_gateway",
                    "monument_type": "Red Hill",
                    "period": "Roman",
                    "easting": 590500.0,
                    "northing": 208500.0,
                    "grid_reference": "TL 9050 0850",
                    "url": "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001",
                },
            ],
            2,  # total_searched
        )
    )

    return registry


def make_mock_response(json_data: Any, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.text = json.dumps(json_data)
    resp.raise_for_status.return_value = None
    return resp
