# chuk-mcp-her Specification

Version 0.3.0

## Overview

chuk-mcp-her is an MCP (Model Context Protocol) server that provides structured
access to Historic Environment Records across England. It queries live ArcGIS
REST APIs from Historic England for designated heritage assets -- listed buildings,
scheduled monuments, conservation areas, heritage at risk entries, registered parks
and gardens, battlefields, protected wrecks, and World Heritage Sites -- plus local
HER data via Heritage Gateway web scraping. Provides tools for cross-referencing,
nearby search, and export.

- **23 tools** across 8 categories (3 discovery, 5 NHLE, 3 aerial, 3 conservation area, 3 heritage at risk, 1 gateway, 3 cross-referencing, 2 export)
- **5 data sources**: NHLE, AIM, Conservation Areas, Heritage at Risk (all via ArcGIS), Heritage Gateway (web scraper)
- **Spatial-first queries** via ArcGIS Feature Service with BNG/WGS84 support
- **Async-first** -- tool entry points are async; httpx for all HTTP requests
- **Dual output mode** -- all tools return JSON (default) or human-readable text via `output_mode`
- **Source registry pattern** -- pluggable adapters for each data source

## Data Sources

| Source ID | Name | Organisation | Coverage | API Type | Status |
|-----------|------|-------------|----------|----------|--------|
| `nhle` | National Heritage List for England | Historic England | England | ArcGIS Feature Service | Active |
| `aim` | Aerial Investigation and Mapping | Historic England | England | ArcGIS Feature Service | Active |
| `conservation_area` | Conservation Areas | Historic England / LPAs | England | ArcGIS Feature Service | Active |
| `heritage_at_risk` | Heritage at Risk Register | Historic England | England | ArcGIS Feature Service | Active |
| `heritage_gateway` | Heritage Gateway (Local HERs) | Historic England / Local HERs | England | Web scraper | Active |

### NHLE Layer Configuration

| Layer ID | Designation Type | Geometry Type |
|----------|-----------------|---------------|
| 0 | Listed Building (Points) | Point |
| 1 | Listed Building (Polygons) | Polygon |
| 6 | Scheduled Monument | Point |
| 7 | Park and Garden | Point |
| 8 | Battlefield | Point |
| 9 | Protected Wreck | Point |
| 10 | World Heritage Site | Point |

### ArcGIS Feature Service Base URLs

| Source | Base URL |
|--------|----------|
| NHLE | `https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer` |
| AIM | `https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Aerial_Investigation_Mapping/FeatureServer` |
| Conservation Areas | `https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Conservation_Areas/FeatureServer` |
| Heritage at Risk | `https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Heritage_at_Risk_Register_2024/FeatureServer` |

---

## Tools

### Common Parameters

All tools accept the following optional parameter:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_mode` | `str` | `json` | Response format: `json` (structured) or `text` (human-readable) |

---

### Discovery Tools

#### `her_status`

Check server health and data source availability.

**Parameters:** `output_mode` only

**Response:** `StatusResponse`

| Field | Type | Description |
|-------|------|-------------|
| `server` | `str` | Server name |
| `version` | `str` | Server version |
| `sources` | `dict[str, StatusSourceInfo]` | Source status map |
| `tool_count` | `int` | Number of registered tools |
| `message` | `str` | Result message |

---

#### `her_list_sources`

List all registered heritage data sources and their capabilities.

**Parameters:** `output_mode` only

**Response:** `SourceListResponse`

| Field | Type | Description |
|-------|------|-------------|
| `sources` | `SourceInfo[]` | Source metadata entries |
| `count` | `int` | Number of sources |
| `message` | `str` | Result message |

**SourceInfo fields:**

| Field | Type | Description |
|-------|------|-------------|
| `source_id` | `str` | Unique identifier (e.g. `nhle`) |
| `name` | `str` | Human-readable name |
| `organisation` | `str?` | Organisation responsible |
| `coverage` | `str?` | Geographic coverage |
| `api_type` | `str?` | API type (e.g. `arcgis_feature_service`) |
| `description` | `str?` | Source description |
| `native_srid` | `int?` | Native spatial reference (e.g. 27700) |
| `capabilities` | `str[]` | Supported query types |
| `designation_types` | `str[]` | Supported designation types |
| `licence` | `str?` | Data licence |
| `status` | `str` | `available`, `stub`, or `unavailable` |
| `note` | `str?` | Additional notes |

---

#### `her_capabilities`

Full server capabilities for LLM workflow planning.

**Parameters:** `output_mode` only

**Response:** `CapabilitiesResponse`

| Field | Type | Description |
|-------|------|-------------|
| `server` | `str` | Server name |
| `version` | `str` | Server version |
| `sources` | `SourceInfo[]` | All registered sources |
| `tools` | `ToolInfo[]` | All registered tools with categories |
| `jurisdictions_available` | `str[]` | Active jurisdictions (e.g. `["England"]`) |
| `jurisdictions_roadmap` | `str[]` | Planned jurisdictions |
| `spatial_references` | `int[]` | Supported SRIDs |
| `max_results_per_query` | `int` | Maximum results per query (2000) |
| `tool_count` | `int` | Total tool count |
| `llm_guidance` | `str` | LLM query planning guidance |
| `message` | `str` | Result message |

---

### NHLE Query Tools

#### `her_search_monuments`

Search scheduled monuments by location, name, or description.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str?` | `None` | Monument name (partial match, case-insensitive) |
| `description` | `str?` | `None` | Full-text search on description |
| `bbox` | `str?` | `None` | Bounding box as `"xmin,ymin,xmax,ymax"` in BNG (EPSG:27700) |
| `lat` | `float?` | `None` | WGS84 latitude for radius search |
| `lon` | `float?` | `None` | WGS84 longitude for radius search |
| `radius_m` | `float?` | `None` | Search radius in metres (requires lat/lon) |
| `max_results` | `int` | `50` | Maximum results (1-2000) |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `MonumentSearchResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `source` | `str` | Source ID (`nhle`) |
| `count` | `int` | Number of monuments returned |
| `total_available` | `int?` | Total matching monuments |
| `monuments` | `MonumentInfo[]` | Monument records |
| `has_more` | `bool` | Whether more results are available |
| `next_offset` | `int?` | Offset for next page |
| `message` | `str` | Result message |

**MonumentInfo fields:**

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | `str` | Prefixed ID (e.g. `nhle:1002345`) |
| `nhle_id` | `str?` | NHLE list entry number |
| `name` | `str` | Monument name |
| `source` | `str` | Source ID |
| `designation_type` | `str?` | Designation type |
| `grade` | `str?` | Listing grade (listed buildings only) |
| `list_date` | `str?` | Date listed |
| `amendment_date` | `str?` | Last amendment date |
| `easting` | `float?` | BNG easting |
| `northing` | `float?` | BNG northing |
| `lat` | `float?` | WGS84 latitude |
| `lon` | `float?` | WGS84 longitude |
| `ngr` | `str?` | National Grid Reference |
| `url` | `str?` | Historic England listing page URL |

---

#### `her_get_monument`

Get full details for a specific monument.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `nhle_id` | `str` | *required* | NHLE list entry number (e.g. `"1002345"`) |

**Response:** `MonumentDetailResponse`

| Field | Type | Description |
|-------|------|-------------|
| `monument` | `dict` | Full monument record |
| `geometry` | `dict?` | GeoJSON geometry (if available) |
| `message` | `str` | Result message |

---

#### `her_search_listed_buildings`

Search listed buildings with grade filtering.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str?` | `None` | Building name (partial match) |
| `grade` | `str?` | `None` | Listing grade: `"I"`, `"II*"`, or `"II"` |
| `bbox` | `str?` | `None` | Bounding box in BNG |
| `lat` | `float?` | `None` | WGS84 latitude |
| `lon` | `float?` | `None` | WGS84 longitude |
| `radius_m` | `float?` | `None` | Search radius in metres |
| `max_results` | `int` | `50` | Maximum results (1-2000) |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `MonumentSearchResponse` (same as monument search)

---

#### `her_search_designations`

Generic search across all NHLE designation types.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `designation_type` | `str?` | `None` | Filter: `listed_building`, `scheduled_monument`, `park_and_garden`, `battlefield`, `protected_wreck`, `world_heritage_site` |
| `name` | `str?` | `None` | Name search (partial match) |
| `description` | `str?` | `None` | Description search |
| `bbox` | `str?` | `None` | Bounding box in BNG |
| `lat` | `float?` | `None` | WGS84 latitude |
| `lon` | `float?` | `None` | WGS84 longitude |
| `radius_m` | `float?` | `None` | Search radius in metres |
| `max_results` | `int` | `50` | Maximum results (1-2000) |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `DesignationSearchResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `source` | `str` | Source ID |
| `count` | `int` | Number of designations returned |
| `total_available` | `int?` | Total matching |
| `designations` | `DesignationInfo[]` | Designation records |
| `has_more` | `bool` | Whether more results are available |
| `next_offset` | `int?` | Offset for next page |
| `message` | `str` | Result message |

**DesignationInfo fields:**

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | `str` | Prefixed ID |
| `nhle_id` | `str?` | NHLE list entry number |
| `name` | `str` | Designation name |
| `designation_type` | `str` | Type of designation |
| `grade` | `str?` | Listing grade (listed buildings only) |
| `lat` | `float?` | WGS84 latitude |
| `lon` | `float?` | WGS84 longitude |
| `url` | `str?` | Historic England listing page URL |

---

#### `her_count_features`

Fast count of heritage features in an area without fetching full records.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `designation_type` | `str?` | `None` | Filter by type (None = count all types) |
| `bbox` | `str?` | `None` | Bounding box in BNG |

**Response:** `FeatureCountResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `counts` | `dict[str, int]` | Counts per designation type plus `total` |
| `source` | `str` | Source ID |
| `message` | `str` | Result message |

---

### Aerial Mapping Tools

#### `her_search_aerial`

Search aerial investigation mapping data.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `monument_type` | `str?` | `None` | Monument type keyword (e.g. `"saltern"`, `"enclosure"`) |
| `period` | `str?` | `None` | Period filter (e.g. `"Iron Age"`, `"Roman"`) |
| `bbox` | `str?` | `None` | Bounding box in BNG |
| `lat` | `float?` | `None` | WGS84 latitude |
| `lon` | `float?` | `None` | WGS84 longitude |
| `radius_m` | `float?` | `None` | Search radius in metres |
| `max_results` | `int` | `50` | Maximum results |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `AerialSearchResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `source` | `str` | `aim` |
| `count` | `int` | Number of features |
| `features` | `AerialFeatureInfo[]` | Aerial mapping features |
| `has_more` | `bool` | Whether more results are available |
| `message` | `str` | Result message |

---

#### `her_count_aerial`

Fast count of aerial mapping features in an area without fetching full records.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `monument_type` | `str?` | `None` | Monument type keyword |
| `period` | `str?` | `None` | Period filter |
| `bbox` | `str?` | `None` | Bounding box in BNG |

**Response:** `FeatureCountResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `counts` | `dict[str, int]` | Feature counts plus `total` |
| `source` | `str` | `aim` |
| `message` | `str` | Result message |

---

#### `her_get_aerial_feature`

Get full details of a specific aerial mapping feature.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `feature_id` | `str` | *required* | Aerial mapping feature identifier |

**Response:** `AerialFeatureDetailResponse`

| Field | Type | Description |
|-------|------|-------------|
| `feature` | `dict` | Full aerial mapping feature record |
| `geometry` | `dict?` | GeoJSON geometry (if available) |
| `message` | `str` | Result message |

---

### Conservation Area Tools

#### `her_search_conservation_areas`

Search conservation areas by name, Local Planning Authority, or location.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str?` | `None` | Name search (partial match, case-insensitive) |
| `lpa` | `str?` | `None` | Local Planning Authority name (partial match) |
| `bbox` | `str?` | `None` | Bounding box as `"xmin,ymin,xmax,ymax"` in BNG (EPSG:27700) |
| `lat` | `float?` | `None` | WGS84 latitude for radius search |
| `lon` | `float?` | `None` | WGS84 longitude for radius search |
| `radius_m` | `float?` | `None` | Search radius in metres (requires lat/lon) |
| `max_results` | `int` | `50` | Maximum results (1-2000) |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `ConservationAreaSearchResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `source` | `str` | `conservation_area` |
| `count` | `int` | Number of areas returned |
| `total_available` | `int?` | Total matching areas |
| `areas` | `ConservationAreaInfo[]` | Conservation area records |
| `has_more` | `bool` | Whether more results are available |
| `next_offset` | `int?` | Offset for next page |
| `message` | `str` | Result message |

**ConservationAreaInfo fields:**

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | `str` | Prefixed ID (e.g. `ca:8757`) |
| `name` | `str` | Conservation area name |
| `source` | `str` | Source ID |
| `lpa` | `str?` | Local Planning Authority |
| `designation_date` | `str?` | Date of designation |
| `easting` | `float?` | BNG easting |
| `northing` | `float?` | BNG northing |
| `lat` | `float?` | WGS84 latitude |
| `lon` | `float?` | WGS84 longitude |

---

#### `her_count_conservation_areas`

Fast count of conservation areas in an area without fetching full records.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bbox` | `str?` | `None` | Bounding box in BNG |
| `query` | `str?` | `None` | Name filter |
| `lpa` | `str?` | `None` | Local Planning Authority filter |

**Response:** `ConservationAreaCountResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `count` | `int` | Number of conservation areas |
| `source` | `str` | `conservation_area` |
| `message` | `str` | Result message |

---

#### `her_get_conservation_area`

Get full details of a specific conservation area.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `record_id` | `str` | *required* | Conservation area identifier (e.g. `"ca:8757"` or `"8757"`) |

**Response:** `ConservationAreaDetailResponse`

| Field | Type | Description |
|-------|------|-------------|
| `area` | `dict` | Full conservation area record |
| `geometry` | `dict?` | GeoJSON geometry (if available) |
| `message` | `str` | Result message |

---

### Heritage at Risk Tools

#### `her_search_heritage_at_risk`

Search the Heritage at Risk Register for at-risk heritage assets.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `query` | `str?` | `None` | Name search (partial match, case-insensitive) |
| `heritage_category` | `str?` | `None` | Heritage category filter (e.g. `"Listed Building"`, `"Scheduled Monument"`, `"Conservation Area"`, `"Registered Park and Garden"`) |
| `bbox` | `str?` | `None` | Bounding box as `"xmin,ymin,xmax,ymax"` in BNG (EPSG:27700) |
| `lat` | `float?` | `None` | WGS84 latitude for radius search |
| `lon` | `float?` | `None` | WGS84 longitude for radius search |
| `radius_m` | `float?` | `None` | Search radius in metres (requires lat/lon) |
| `max_results` | `int` | `50` | Maximum results (1-2000) |
| `offset` | `int` | `0` | Pagination offset |

**Response:** `HeritageAtRiskSearchResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `source` | `str` | `heritage_at_risk` |
| `count` | `int` | Number of entries returned |
| `total_available` | `int?` | Total matching entries |
| `entries` | `HeritageAtRiskInfo[]` | Heritage at risk records |
| `has_more` | `bool` | Whether more results are available |
| `next_offset` | `int?` | Offset for next page |
| `message` | `str` | Result message |

**HeritageAtRiskInfo fields:**

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | `str` | Prefixed ID (e.g. `har:1012707`) |
| `name` | `str` | Entry name |
| `source` | `str` | Source ID |
| `heritage_category` | `str?` | Heritage category (Listed Building, Scheduled Monument, etc.) |
| `risk_methodology` | `str?` | Risk methodology (Archaeology, Building or structure, etc.) |
| `easting` | `float?` | BNG easting |
| `northing` | `float?` | BNG northing |
| `lat` | `float?` | WGS84 latitude |
| `lon` | `float?` | WGS84 longitude |
| `url` | `str?` | Historic England HAR page URL |

---

#### `her_count_heritage_at_risk`

Fast count of heritage at risk entries in an area without fetching full records.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bbox` | `str?` | `None` | Bounding box in BNG |
| `heritage_category` | `str?` | `None` | Heritage category filter |

**Response:** `HeritageAtRiskCountResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `count` | `int` | Number of at-risk entries |
| `source` | `str` | `heritage_at_risk` |
| `message` | `str` | Result message |

---

#### `her_get_heritage_at_risk`

Get full details of a specific heritage at risk entry.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `record_id` | `str` | *required* | Heritage at risk identifier (e.g. `"har:1012707"` or `"1012707"`) |

**Response:** `HeritageAtRiskDetailResponse`

| Field | Type | Description |
|-------|------|-------------|
| `monument` | `dict` | Full heritage at risk record |
| `geometry` | `dict?` | GeoJSON geometry (if available) |
| `message` | `str` | Result message |

---

### Heritage Gateway Tools

#### `her_search_heritage_gateway`

Search local HER data via Heritage Gateway web scraping. Best-effort access to 60+
local Historic Environment Records. Returns empty results gracefully when Gateway
is unavailable.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `what` | `str?` | `None` | Monument type or keyword |
| `where` | `str?` | `None` | Place name or area |
| `when` | `str?` | `None` | Period |
| `max_results` | `int` | `50` | Maximum results |

**Response:** `GatewaySearchResponse`

| Field | Type | Description |
|-------|------|-------------|
| `query` | `dict?` | Query parameters applied |
| `source` | `str` | `heritage_gateway` |
| `count` | `int` | Number of records |
| `records` | `GatewayRecordInfo[]` | Heritage Gateway records |
| `note` | `str?` | Additional notes |
| `message` | `str` | Result message |

---

### Cross-Referencing Tools

#### `her_cross_reference`

Cross-reference candidate locations against known heritage assets.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `candidates` | `str` | `"[]"` | JSON array of `{"easting": x, "northing": y}` dicts |
| `match_radius_m` | `float` | `50.0` | Distance threshold for "match" classification |
| `near_radius_m` | `float` | `200.0` | Distance threshold for "near" classification |
| `designation_types` | `str?` | `None` | Comma-separated designation types to match against |
| `include_aim` | `bool` | `false` | Include AIM aerial mapping features in known-asset pool |
| `gateway_sites` | `str` | `"[]"` | JSON array of enriched Gateway records (output of `her_enrich_gateway`) |

**Response:** `CrossReferenceResponse`

| Field | Type | Description |
|-------|------|-------------|
| `candidates_submitted` | `int` | Number of candidates submitted |
| `classification` | `dict[str, int]` | Count per classification (match, near, novel) |
| `matches` | `CrossReferenceMatch[]` | Matched candidates |
| `near_misses` | `CrossReferenceMatch[]` | Near-miss candidates |
| `novel_count` | `int` | Number of novel candidates |
| `novel_summary` | `str?` | Summary of novel findings |
| `message` | `str` | Result message |

**CrossReferenceMatch fields:**

| Field | Type | Description |
|-------|------|-------------|
| `candidate` | `dict` | Candidate coordinates |
| `matched_asset` | `dict?` | Matched asset (for "match" classification) |
| `nearest_asset` | `dict?` | Nearest asset (for "near" classification) |
| `distance_m` | `float?` | Distance to nearest asset |
| `classification` | `str` | `match`, `near`, or `novel` |

**Matched/nearest asset fields** (enriched output, None fields excluded):

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | `str?` | Asset record ID |
| `name` | `str?` | Asset name |
| `source` | `str?` | Source ID (`nhle`, `aim`, `heritage_gateway`) |
| `designation_type` | `str?` | NHLE designation type |
| `grade` | `str?` | Listing grade (NHLE listed buildings) |
| `monument_type` | `str?` | Monument type (AIM, Gateway) |
| `period` | `str?` | Period (AIM, Gateway) |
| `form` | `str?` | Form (AIM) |
| `evidence` | `str?` | Evidence type (AIM) |
| `easting` | `float?` | BNG easting |
| `northing` | `float?` | BNG northing |

Candidate classification uses a grid-based spatial index (`GridSpatialIndex`)
for O(n+m) amortised nearest-neighbour lookup.

---

#### `her_nearby`

Find heritage assets near a single point.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `lat` | `float?` | `None` | WGS84 latitude |
| `lon` | `float?` | `None` | WGS84 longitude |
| `easting` | `float?` | `None` | BNG easting (alternative to lat/lon) |
| `northing` | `float?` | `None` | BNG northing |
| `radius_m` | `float` | `500.0` | Search radius in metres |
| `max_results` | `int` | `20` | Maximum results |

**Response:** `NearbyResponse`

| Field | Type | Description |
|-------|------|-------------|
| `centre_lat` | `float` | Centre point latitude |
| `centre_lon` | `float` | Centre point longitude |
| `radius_m` | `float` | Search radius used |
| `count` | `int` | Number of assets found |
| `assets` | `NearbyAssetInfo[]` | Nearby assets sorted by distance |
| `message` | `str` | Result message |

**NearbyAssetInfo fields:**

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | `str` | Prefixed ID |
| `nhle_id` | `str?` | NHLE list entry number |
| `name` | `str` | Asset name |
| `designation_type` | `str?` | Designation type |
| `grade` | `str?` | Listing grade |
| `distance_m` | `float?` | Distance from centre point |
| `bearing_deg` | `float?` | Bearing from centre point (0=N, 90=E) |
| `lat` | `float?` | WGS84 latitude |
| `lon` | `float?` | WGS84 longitude |
| `easting` | `float?` | BNG easting |
| `northing` | `float?` | BNG northing |

---

#### `her_enrich_gateway`

Fetch Heritage Gateway records with resolved BNG coordinates. Searches the
Heritage Gateway for local HER records and resolves their coordinates by parsing
grid references and/or fetching detail pages. Returns only records with valid
easting/northing, suitable for use as `gateway_sites` in `her_cross_reference`
or `her_export_for_lidar`.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `what` | `str?` | `None` | Monument type or keyword (e.g. `"red hill"`, `"saltern"`) |
| `where` | `str?` | `None` | Place name (e.g. `"Blackwater"`, `"Essex"`) |
| `when` | `str?` | `None` | Period (e.g. `"Roman"`, `"Iron Age"`) |
| `max_results` | `int` | `100` | Maximum records to return |
| `fetch_details` | `bool` | `true` | Fetch detail pages to resolve coordinates (slow but more accurate) |

**Response:** `GatewayEnrichResponse`

| Field | Type | Description |
|-------|------|-------------|
| `records` | `dict[]` | Records with resolved BNG coordinates |
| `count` | `int` | Number of resolved records |
| `resolved_count` | `int` | Records with valid easting/northing |
| `unresolved_count` | `int` | Records without coordinates |
| `fetch_details_used` | `bool` | Whether detail pages were fetched |
| `message` | `str` | Result message |

**Enriched record fields:**

| Field | Type | Description |
|-------|------|-------------|
| `record_id` | `str` | Heritage Gateway record ID |
| `name` | `str` | Record name |
| `monument_type` | `str?` | Monument type |
| `easting` | `float` | BNG easting (resolved) |
| `northing` | `float` | BNG northing (resolved) |
| `grid_reference` | `str?` | Grid reference (if available) |

---

### Export Tools

#### `her_export_geojson`

Export heritage assets as GeoJSON FeatureCollection.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bbox` | `str?` | `None` | Bounding box in BNG |
| `designation_type` | `str?` | `None` | Designation type filter |
| `name` | `str?` | `None` | Name filter |
| `max_results` | `int` | `500` | Maximum features (max 2000) |

**Response:** `GeoJSONExportResponse`

| Field | Type | Description |
|-------|------|-------------|
| `geojson` | `dict` | GeoJSON FeatureCollection |
| `feature_count` | `int` | Number of features exported |
| `message` | `str` | Result message |

**GeoJSON format:**

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "geometry": {
        "type": "Point",
        "coordinates": [-0.0759, 51.5081]
      },
      "properties": {
        "record_id": "nhle:1002345",
        "name": "Tower of London",
        "designation_type": "scheduled_monument",
        "source": "nhle"
      }
    }
  ]
}
```

---

#### `her_export_for_lidar`

Export known heritage sites for LiDAR cross-referencing.

**Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `bbox` | `str` | *required* | Bounding box in BNG |
| `include_aim` | `bool` | `true` | Include AIM aerial mapping features |
| `include_nhle` | `bool` | `true` | Include NHLE designations |
| `gateway_sites` | `str` | `"[]"` | JSON array of enriched Gateway records (output of `her_enrich_gateway`) |

**Response:** `LiDARExportResponse`

| Field | Type | Description |
|-------|------|-------------|
| `bbox` | `float[]` | Bounding box used |
| `known_sites` | `dict[]` | Known sites with BNG coordinates |
| `count` | `int` | Number of sites |
| `message` | `str` | Result message |

**Known site fields** (varies by source, None fields excluded):

| Field | Type | Source | Description |
|-------|------|--------|-------------|
| `id` | `str` | all | Record ID |
| `source` | `str` | all | Source ID (`nhle`, `aim`, `heritage_gateway`) |
| `name` | `str` | all | Site name |
| `type` | `str` | all | Designation/monument type |
| `grade` | `str?` | nhle | Listing grade (I, II*, II) |
| `monument_type` | `str?` | aim, gateway | Monument type |
| `period` | `str?` | aim, gateway | Period |
| `form` | `str?` | aim | Form |
| `evidence` | `str?` | aim | Evidence type |
| `easting` | `float` | all | BNG easting |
| `northing` | `float` | all | BNG northing |

---

### Phase 2+ Tools (Planned)

#### `her_search_canmore` (Phase 2.0)

Search Historic Environment Scotland's Canmore database.

#### `her_search_coflein` (Phase 2.1)

Search the Royal Commission on the Ancient and Historical Monuments of Wales.

#### `her_search_rce` (Phase 3.0)

Search the Dutch Rijksdienst voor het Cultureel Erfgoed.

---

## Domain Reference Data

### Designation Types

| Type | Description | ArcGIS Layer(s) |
|------|-------------|----------------|
| `listed_building` | Listed buildings (Grades I, II*, II) | 0 (points), 1 (polygons) |
| `scheduled_monument` | Scheduled monuments | 6 |
| `park_and_garden` | Registered parks and gardens | 7 |
| `battlefield` | Registered battlefields | 8 |
| `protected_wreck` | Protected wreck sites | 9 |
| `world_heritage_site` | World Heritage Sites | 10 |

### Listing Grades

| Grade | Description | Approximate % |
|-------|-------------|--------------|
| `I` | Exceptional interest (highest significance) | ~2% |
| `II*` | Particularly important (more than special) | ~6% |
| `II` | Nationally important (special interest) | ~92% |

### Supported Spatial References

| SRID | Name | Usage |
|------|------|-------|
| 27700 | British National Grid | Native for NHLE, AIM, Conservation Areas |
| 3857 | Web Mercator | Native for Heritage at Risk (adapter sends in_sr=27700) |
| 4326 | WGS84 | User-facing lat/lon |
| 29903 | Irish Grid | Planned (Phase 3.1) |
| 28992 | Amersfoort / RD New | Planned (Phase 3.0) |

### Query Limits

| Parameter | Value | Description |
|-----------|-------|-------------|
| `MAX_RESULTS` | 100 | Default max results per query |
| `MAX_PAGE_SIZE` | 2000 | ArcGIS maximum per request |
| `DEFAULT_RADIUS_M` | 500 | Default nearby search radius |
| `MAX_RADIUS_M` | 50000 | Maximum search radius |
| `MAX_BBOX_AREA_KM2` | 100 | Maximum bounding box area |

---

## Error Handling

All tools return `ErrorResponse` on failure:

```json
{
  "error": "No results found matching search criteria",
  "error_type": "no_data",
  "message": "",
  "suggestion": "Expand search radius or check coordinate system"
}
```

### Error Message Templates

| Scenario | Error Message Template |
|----------|----------------------|
| Source not found | `"Source '{}' not found. Available: {}"` |
| Monument not found | `"Monument '{}' not found"` |
| No results | `"No results found matching search criteria"` |
| Service unavailable | `"Source '{}' temporarily unavailable: {}"` |
| Invalid SRID | `"Unsupported SRID {}. Use 27700 (BNG) or 4326 (WGS84)"` |
| Invalid coordinates | `"Invalid coordinates: {}"` |
| Invalid bbox | `"Invalid bounding box: expected 'xmin,ymin,xmax,ymax'"` |
| Bbox too large | `"Bounding box exceeds maximum area ({}km2)..."` |
| Not implemented | `"Source '{}' is not yet implemented (roadmap)"` |
| ArcGIS error | `"ArcGIS query failed: {}"` |
| Export failed | `"Export failed: {}"` |
| Spatial required | `"At least one spatial parameter required..."` |
| Rate limited | `"Rate limited. Wait {}s before retrying"` |
| Timeout | `"Request timed out after {}s"` |
| Invalid grade | `"Invalid grade '{}'. Use: I, II*, or II"` |
| Invalid designation | `"Invalid designation type '{}'. Available: {}"` |

---

## Caching Strategy

### Filesystem Cache

Responses are cached as JSON files at `~/.cache/chuk-mcp-her/{source}/{hash}.json`.

| Source | Default TTL | Rationale |
|--------|-------------|-----------|
| NHLE | 86400s (24 hours) | Designations change infrequently |
| AIM | 604800s (7 days) | Aerial mapping data is very stable |
| Conservation Areas | 86400s (24 hours) | Designation changes are infrequent |
| Heritage at Risk | 86400s (24 hours) | Register updated annually |
| Heritage Gateway | 3600s (1 hour) | Local HER data may update more often |

### Cache Key Generation

```python
cache_key = f"{source_id}/{sha256(sorted_params)[:16]}"
```

---

## Build Phases

| Phase | Focus | New Tools | Cumulative |
|-------|-------|-----------|------------|
| 1.0 | NHLE Core | 14 | 14 |
| 1.1 | Aerial Investigation Mapping | 2 | 16 |
| 1.2 | Conservation Areas, Heritage at Risk, Heritage Gateway | 7 | 23 |
| 1.3 | Cross-Referencing Enhancements | 0 | 23 |
| 2.0 | Scotland (Canmore) | 1 | 23 |
| 2.1 | Wales (Coflein) | 1 | 24 |
| 2.2 | New Heritage Gateway API | 0 | 24 |
| 3.0 | Netherlands (RCE) | 1 | 25 |

---

## Integration Points

### chuk-mcp-lidar

The LiDAR export format (`her_export_for_lidar`) is designed for direct use with
chuk-mcp-lidar's spatial matching tools. Known site centroids with BNG coordinates
enable cross-referencing LiDAR-derived anomalies against heritage records.

### chuk-mcp-maritime-archives

Protected wreck designations in the NHLE can be cross-referenced with wreck
records in chuk-mcp-maritime-archives. The `protected_wreck` designation type
in NHLE corresponds to wrecks that have been given legal protection under the
Protection of Wrecks Act 1973.

### GIS Tools

`her_export_geojson` produces standard GeoJSON FeatureCollections compatible with:
- QGIS (drag and drop)
- Leaflet / Mapbox (direct JSON loading)
- ArcGIS Online (import as feature layer)
- PostGIS (ogr2ogr import)

---

## Demo Scripts

| Script | Tools Demonstrated | Network |
|--------|-------------------|---------|
| `capabilities_demo.py` | `her_capabilities`, `her_list_sources`, `her_status` | No |
| `quick_start.py` | `her_status`, `her_count_features`, `her_search_monuments`, `her_get_monument`, `her_nearby` | Yes |
| `nhle_search_demo.py` | `her_search_monuments`, `her_get_monument`, `her_search_listed_buildings`, `her_search_designations`, `her_count_features` | Yes |
| `aerial_search_demo.py` | `her_search_aerial`, `her_count_aerial`, `her_get_aerial_feature` | Yes |
| `conservation_area_demo.py` | `her_search_conservation_areas`, `her_count_conservation_areas`, `her_get_conservation_area` | Yes |
| `heritage_at_risk_demo.py` | `her_search_heritage_at_risk`, `her_count_heritage_at_risk`, `her_get_heritage_at_risk` | Yes |
| `nearby_demo.py` | `her_nearby` | Yes |
| `export_demo.py` | `her_export_geojson`, `her_export_for_lidar` | Yes |
| `gateway_search_demo.py` | `her_search_heritage_gateway` | Yes |
| `cross_reference_demo.py` | `her_cross_reference` (with `include_aim`) | Yes |
| `enrichment_pipeline_demo.py` | `her_enrich_gateway`, `her_search_heritage_gateway`, `her_cross_reference`, `her_count_features` | Yes |
| `blackwater_estuary_scenario.py` | Multi-source scenario using NHLE, AIM, Conservation Areas, Heritage at Risk | Yes |

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_STDIO` | - | Force stdio transport mode |
| `HER_CACHE_DIR` | `~/.cache/chuk-mcp-her` | Cache directory path |
| `HER_NHLE_CACHE_TTL` | `86400` | NHLE cache TTL (seconds) |
| `HER_AIM_CACHE_TTL` | `604800` | AIM cache TTL (seconds) |
| `HER_HG_CACHE_TTL` | `3600` | Heritage Gateway cache TTL (seconds) |
| `HER_RATE_LIMIT` | `5.0` | Max requests/sec to ArcGIS |
| `HER_TIMEOUT` | `30.0` | HTTP timeout (seconds) |

### Server Modes

| Mode | Port | Usage |
|------|------|-------|
| stdio | - | MCP clients (Claude Desktop, mcp-cli) |
| http | 8010 | HTTP-based MCP clients |

---

## References

- [Historic England NHLE](https://historicengland.org.uk/listing/the-list/) -- National Heritage List for England
- [NHLE ArcGIS Feature Service](https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer) -- Live data endpoint
- [AIM ArcGIS Feature Service](https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/Aerial_Investigation_Mapping/FeatureServer) -- Aerial mapping endpoint
- [Heritage Gateway](https://www.heritagegateway.org.uk/) -- Federated HER search
- [ArcGIS REST API Query](https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/) -- Query specification
- [EPSG:27700](https://epsg.io/27700) -- British National Grid
- [Protection of Wrecks Act 1973](https://www.legislation.gov.uk/ukpga/1973/33) -- Legal basis for protected wreck designations
- [Model Context Protocol](https://modelcontextprotocol.io/) -- MCP specification
