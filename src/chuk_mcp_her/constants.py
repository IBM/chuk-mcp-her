"""
Constants for chuk-mcp-her.

All magic strings, configuration values, error messages, and domain
constants are defined here. No hardcoded strings in tool code.
"""

from __future__ import annotations

from enum import Enum
from typing import Literal


# ============================================================================
# Server Configuration
# ============================================================================


class ServerConfig(str, Enum):
    NAME = "chuk-mcp-her"
    VERSION = "0.3.0"
    DESCRIPTION = "Historic Environment Records"


class EnvVar:
    MCP_STDIO = "MCP_STDIO"
    HER_CACHE_DIR = "HER_CACHE_DIR"
    HER_NHLE_CACHE_TTL = "HER_NHLE_CACHE_TTL"
    HER_AIM_CACHE_TTL = "HER_AIM_CACHE_TTL"
    HER_HG_CACHE_TTL = "HER_HG_CACHE_TTL"
    HER_RATE_LIMIT = "HER_RATE_LIMIT"
    HER_TIMEOUT = "HER_TIMEOUT"


# ============================================================================
# Source Registry
# ============================================================================


class SourceId(str, Enum):
    NHLE = "nhle"
    AIM = "aim"
    CONSERVATION_AREA = "conservation_area"
    HERITAGE_AT_RISK = "heritage_at_risk"
    HERITAGE_GATEWAY = "heritage_gateway"


SOURCE_METADATA: dict[str, dict] = {
    "nhle": {
        "name": "National Heritage List for England",
        "organisation": "Historic England",
        "description": (
            "Designated heritage assets: listed buildings, scheduled monuments, "
            "registered parks and gardens, battlefields, protected wrecks, "
            "and World Heritage Sites"
        ),
        "coverage": "England",
        "api_type": "arcgis_feature_service",
        "base_url": (
            "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/"
            "National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer"
        ),
        "native_srid": 27700,
        "capabilities": [
            "spatial_query",
            "text_search",
            "feature_count",
            "attribute_filter",
            "pagination",
        ],
        "designation_types": [
            "listed_building",
            "scheduled_monument",
            "park_and_garden",
            "battlefield",
            "protected_wreck",
            "world_heritage_site",
        ],
        "licence": "Open Government Licence",
        "cache_ttl_seconds": 86400,
    },
    "aim": {
        "name": "Aerial Investigation and Mapping",
        "organisation": "Historic England",
        "description": (
            "Archaeological features identified from aerial photographs "
            "and LiDAR interpretation. Includes cropmarks, earthworks, "
            "and features not in the NHLE"
        ),
        "coverage": "England",
        "api_type": "arcgis_feature_service",
        "base_url": (
            "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/"
            "HE_AIM_data/FeatureServer"
        ),
        "native_srid": 27700,
        "capabilities": ["spatial_query", "text_search", "feature_count"],
        "licence": "Open Government Licence",
        "cache_ttl_seconds": 604800,
    },
    "conservation_area": {
        "name": "Conservation Areas",
        "organisation": "Historic England / Local Planning Authorities",
        "description": (
            "Conservation areas designated by Local Planning Authorities. "
            "8,000+ areas of special architectural or historic interest "
            "across England"
        ),
        "coverage": "England",
        "api_type": "arcgis_feature_service",
        "base_url": (
            "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/"
            "Conservation_Areas/FeatureServer"
        ),
        "native_srid": 27700,
        "capabilities": [
            "spatial_query",
            "text_search",
            "feature_count",
            "pagination",
        ],
        "licence": "Open Government Licence",
        "cache_ttl_seconds": 86400,
    },
    "heritage_at_risk": {
        "name": "Heritage at Risk Register",
        "organisation": "Historic England",
        "description": (
            "Annual register of heritage assets at risk of loss through "
            "neglect, decay, or inappropriate development. Includes at-risk "
            "listed buildings, scheduled monuments, conservation areas, "
            "parks and gardens, battlefields, and protected wrecks"
        ),
        "coverage": "England",
        "api_type": "arcgis_feature_service",
        "base_url": (
            "https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/"
            "Historic_England_Heritage_at_Risk_Register_2024/FeatureServer"
        ),
        "native_srid": 3857,
        "capabilities": [
            "spatial_query",
            "text_search",
            "feature_count",
            "attribute_filter",
            "pagination",
        ],
        "heritage_categories": [
            "Scheduled Monument",
            "Listed Building",
            "Conservation Area",
            "Registered Park and Garden",
            "Registered Battlefield",
            "Protected Wreck Site",
        ],
        "licence": "Open Government Licence",
        "cache_ttl_seconds": 86400,
    },
    "heritage_gateway": {
        "name": "Heritage Gateway (Local HERs)",
        "organisation": "Historic England / Local HERs",
        "description": (
            "Federated search across local Historic Environment Records. "
            "Includes undesignated sites, findspots, and HER monument entries "
            "not in the NHLE"
        ),
        "coverage": "England",
        "api_type": "web_scraper",
        "base_url": "https://www.heritagegateway.org.uk",
        "capabilities": ["text_search"],
        "note": (
            "Scraper-based — best-effort access to 60+ local HERs. "
            "Returns empty results gracefully when Gateway is unavailable."
        ),
        "cache_ttl_seconds": 3600,
    },
}


# ============================================================================
# NHLE Layer Configuration
# ============================================================================


class NHLELayer(int, Enum):
    """ArcGIS Feature Service layer indices for NHLE."""

    LISTED_BUILDING_POINTS = 0
    LISTED_BUILDING_POLYGONS = 1
    SCHEDULED_MONUMENTS = 6
    PARKS_AND_GARDENS = 7
    BATTLEFIELDS = 8
    PROTECTED_WRECKS = 9
    WORLD_HERITAGE_SITES = 10


# Mapping from designation type to NHLE layer ID(s)
DESIGNATION_LAYERS: dict[str, list[int]] = {
    "listed_building": [NHLELayer.LISTED_BUILDING_POINTS],
    "scheduled_monument": [NHLELayer.SCHEDULED_MONUMENTS],
    "park_and_garden": [NHLELayer.PARKS_AND_GARDENS],
    "battlefield": [NHLELayer.BATTLEFIELDS],
    "protected_wreck": [NHLELayer.PROTECTED_WRECKS],
    "world_heritage_site": [NHLELayer.WORLD_HERITAGE_SITES],
}

ALL_NHLE_POINT_LAYERS: list[int] = [
    NHLELayer.LISTED_BUILDING_POINTS,
    NHLELayer.SCHEDULED_MONUMENTS,
    NHLELayer.PARKS_AND_GARDENS,
    NHLELayer.BATTLEFIELDS,
    NHLELayer.PROTECTED_WRECKS,
    NHLELayer.WORLD_HERITAGE_SITES,
]

# Reverse mapping: layer ID -> designation type
LAYER_DESIGNATION: dict[int, str] = {
    NHLELayer.LISTED_BUILDING_POINTS: "listed_building",
    NHLELayer.LISTED_BUILDING_POLYGONS: "listed_building",
    NHLELayer.SCHEDULED_MONUMENTS: "scheduled_monument",
    NHLELayer.PARKS_AND_GARDENS: "park_and_garden",
    NHLELayer.BATTLEFIELDS: "battlefield",
    NHLELayer.PROTECTED_WRECKS: "protected_wreck",
    NHLELayer.WORLD_HERITAGE_SITES: "world_heritage_site",
}

DESIGNATION_TYPES: list[str] = [
    "listed_building",
    "scheduled_monument",
    "park_and_garden",
    "battlefield",
    "protected_wreck",
    "world_heritage_site",
]


# ============================================================================
# AIM Layer Configuration
# ============================================================================


class AIMLayer(int, Enum):
    """ArcGIS Feature Service layer indices for AIM (HE_AIM_data)."""

    DETAILED_MAPPING = 1
    MONUMENT_EXTENTS = 2
    PROJECT_AREA = 3


AIM_DEFAULT_SEARCH_LAYER = AIMLayer.DETAILED_MAPPING


# ============================================================================
# Heritage Gateway Configuration
# ============================================================================


class GatewayConfig:
    """Heritage Gateway URL and scraping configuration."""

    BASE_URL = "https://www.heritagegateway.org.uk"
    SEARCH_URL = f"{BASE_URL}/gateway/advanced_search.aspx"
    RESULTS_URL = f"{BASE_URL}/gateway/Results.aspx"
    DETAIL_URL = f"{BASE_URL}/gateway/Results_Single.aspx"
    POLL_INTERVAL_S = 0.5
    POLL_MAX_ATTEMPTS = 10
    RATE_LIMIT_PER_SEC = 1.0


# ============================================================================
# Heritage at Risk Categories
# ============================================================================


HAR_CATEGORIES: list[str] = [
    "Scheduled Monument",
    "Listed Building",
    "Conservation Area",
    "Registered Park and Garden",
    "Registered Battlefield",
    "Protected Wreck Site",
]


# ============================================================================
# Listed Building Grades
# ============================================================================


LISTING_GRADES: list[str] = ["I", "II*", "II"]


# ============================================================================
# Spatial References
# ============================================================================


DEFAULT_SRID = 27700  # British National Grid
WGS84_SRID = 4326

SUPPORTED_SRIDS: dict[int, str] = {
    27700: "British National Grid",
    4326: "WGS84",
    29903: "Irish Grid",
    28992: "Amersfoort / RD New",
}


# ============================================================================
# Query Limits
# ============================================================================


MAX_RESULTS = 100
MAX_PAGE_SIZE = 2000  # ArcGIS limit per request
DEFAULT_RADIUS_M = 500
MAX_RADIUS_M = 50000
MAX_BBOX_AREA_KM2 = 100


# ============================================================================
# Type Literals
# ============================================================================


SourceName = Literal["nhle", "aim", "conservation_area", "heritage_at_risk", "heritage_gateway"]


# ============================================================================
# Error Messages (no hardcoded strings in tool code)
# ============================================================================


class ErrorMessages:
    SOURCE_NOT_FOUND = "Source '{}' not found. Available: {}"
    MONUMENT_NOT_FOUND = "Monument '{}' not found"
    NO_RESULTS = "No results found matching search criteria"
    SERVICE_UNAVAILABLE = "Source '{}' temporarily unavailable: {}"
    INVALID_SRID = "Unsupported SRID {}. Use 27700 (BNG) or 4326 (WGS84)"
    INVALID_COORDINATES = "Invalid coordinates: {}"
    INVALID_BBOX = "Invalid bounding box: expected 'xmin,ymin,xmax,ymax'"
    BBOX_TOO_LARGE = (
        "Bounding box exceeds maximum area ({}km2). "
        "Reduce search area or use her_count_features first"
    )
    NOT_IMPLEMENTED = "Source '{}' is not yet implemented (roadmap)"
    ARCGIS_ERROR = "ArcGIS query failed: {}"
    GATEWAY_SEARCH_FAILED = "Heritage Gateway search failed: {}"
    GATEWAY_TIMEOUT = "Heritage Gateway timed out after {}s"
    GATEWAY_PARSE_ERROR = "Failed to parse Heritage Gateway response: {}"
    GRID_REF_INVALID = "Invalid grid reference: {}"
    EXPORT_FAILED = "Export failed: {}"
    SPATIAL_REQUIRED = "At least one spatial parameter required (bbox or lat/lon with radius_m)"
    RATE_LIMITED = "Rate limited. Wait {}s before retrying"
    TIMEOUT = "Request timed out after {}s"
    INVALID_GRADE = "Invalid grade '{}'. Use: I, II*, or II"
    INVALID_DESIGNATION = "Invalid designation type '{}'. Available: {}"


class SuccessMessages:
    SOURCES_LISTED = "{} heritage data sources available"
    MONUMENTS_FOUND = "Found {} scheduled monuments"
    BUILDINGS_FOUND = "Found {} listed buildings"
    DESIGNATIONS_FOUND = "{} designations returned ({} total in area)"
    FEATURES_COUNTED = "{} designated heritage assets in area"
    AERIAL_FOUND = "Found {} aerial mapping features"
    AERIAL_COUNTED = "{} aerial mapping features in area"
    AERIAL_FEATURE_RETRIEVED = "Aerial feature record retrieved"
    CONSERVATION_AREAS_FOUND = "Found {} conservation areas"
    CONSERVATION_AREA_COUNTED = "{} conservation areas in area"
    CONSERVATION_AREA_RETRIEVED = "Conservation area record retrieved"
    HAR_FOUND = "Found {} heritage at risk entries"
    HAR_COUNTED = "{} heritage at risk entries in area"
    HAR_RETRIEVED = "Heritage at risk record retrieved"
    GATEWAY_FOUND = "Found {} Heritage Gateway records"
    GATEWAY_ENRICHED = "Resolved coordinates for {} of {} Gateway records"
    CROSS_REF_COMPLETE = "Cross-reference complete: {} matches, {} near, {} novel"
    NEARBY_FOUND = "{} heritage assets within {}m"
    EXPORT_COMPLETE = "Exported {} features as GeoJSON"
    LIDAR_EXPORT_COMPLETE = "{} known sites exported for LiDAR cross-reference"
    MONUMENT_RETRIEVED = "Monument record retrieved"
    SERVER_OK = "Server operational with {} sources ({})"
