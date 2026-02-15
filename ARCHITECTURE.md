# Architecture

This document describes the design principles, module structure, and key patterns
used in chuk-mcp-her.

## Design Principles

### 1. Async-First

All tool entry points are `async`. The `ArcGISClient` uses httpx's async client
with connection pooling, rate limiting, and exponential backoff retry. Multiple
ArcGIS layer queries (e.g. counting across all 6 designation types) run
concurrently via `asyncio.gather()`.

### 2. Single Responsibility

Each module has one job. Tool functions validate inputs, call `SourceRegistry`, and
format responses. `SourceRegistry` orchestrates adapter dispatch and query routing.
Individual source adapters own HTTP querying and feature normalisation. Models define
data shapes. Constants define identifiers and messages.

### 3. Pydantic v2 Native -- No Dict Goop

Response envelopes use `model_config = ConfigDict(extra="forbid")` to catch stale or
mistyped fields at serialisation time. Every response model carries a `to_text()`
method for dual-mode output (JSON or human-readable).

### 4. No Magic Strings

Every repeated string lives in `constants.py` as an enum, class attribute, or
module-level constant. Source IDs, layer IDs, designation types, error message
templates, and success message templates are all constants -- never inline strings.

### 5. Source-Agnostic

The `SourceRegistry` provides a unified query interface across all data sources.
Tool functions never interact with adapters directly -- they call registry methods
which route to the appropriate adapter. This means adding a new data source
(e.g. Scotland's Canmore) requires only a new adapter class, not changes to
any tool code.

### 6. Live API Queries

Unlike chuk-mcp-maritime-archives which loads from local JSON files, this server
queries live ArcGIS REST APIs for each request. The NHLE adapter sends HTTP
requests to Historic England's ArcGIS Feature Service hosted at
`services-eu1.arcgis.com`. This means the server requires network access to
function (though cached results work offline within TTL).

### 7. Spatial-First

Heritage data is inherently geographic. All primary query tools accept spatial
parameters (bounding box, point+radius) as the primary filter mechanism. Text
search is supported as a supplementary filter. The `her_count_features` tool
enables quick area estimation before committing to a full spatial query.

### 8. Filesystem Caching

A filesystem-based cache with per-source TTL reduces load on external APIs.
Cache keys are deterministic SHA256 hashes of query parameters. NHLE responses
are cached for 24 hours, AIM for 7 days, Heritage Gateway for 1 hour. The cache
directory defaults to `~/.cache/chuk-mcp-her` and is configurable via
`HER_CACHE_DIR`.

### 9. Read-Only

This server only reads from external heritage data sources. It does not create,
update, or delete any records. All data flows inward from ArcGIS Feature Services
and web sources. The only writes are to the local filesystem cache.

### 10. Test Coverage -- 667 Tests, 97% Coverage

All modules maintain 90%+ branch coverage (667 tests across 15 test modules, 97%
overall coverage). Tests use `pytest-asyncio` and mock at the HTTP boundary
(`ArcGISClient.query()`, `ArcGISClient.count()`, `GatewayClient` methods), not at
the registry level, to exercise the full data flow from tool to adapter to client.
No live API calls are made during testing.

---

## Architecture Diagram

```
                    MCP Client (Claude, mcp-cli, etc.)
                              |
                              | MCP protocol (stdio / HTTP)
                              v
                  +-------------------------------+
                  |       Tool Functions          |
                  | tools/discovery/         (3)  |
                  | tools/nhle/              (5)  |
                  | tools/aerial/            (3)  |
                  | tools/conservation_area/ (3)  |
                  | tools/heritage_at_risk/  (3)  |
                  | tools/gateway/           (1)  |
                  | tools/crossref/          (2)  |
                  | tools/export/            (2)  |
                  +-------------------------------+
                              |
                              | validate params, format response
                              v
                  +-------------------------------+
                  |       SourceRegistry          |
                  |  - search_monuments()         |
                  |  - search_listed_buildings()  |
                  |  - search_designations()      |
                  |  - search_aerial()            |
                  |  - search_conservation_areas()|
                  |  - search_heritage_at_risk()  |
                  |  - search_heritage_gateway()  |
                  |  - count_features()           |
                  |  - nearby()                   |
                  |  - enrich_gateway_records()   |
                  +-------------------------------+
                    |     |     |     |     |
            NHLEAdapter   |  CA     HAR    |
              AIMAdapter  |  Adapter Adapter|
                          |               GatewayAdapter
                  v       v       v             v
          +------------------+        +------------------+
          |  ArcGIS Client   |        |  Gateway Client  |
          | - query()        |        | - search()       |
          | - count()        |        | - get_record()   |
          | - query_all()    |        | - BeautifulSoup  |
          +------------------+        +------------------+
                  |                           |
                  | httpx AsyncClient         | httpx AsyncClient
                  v                           v
          +---------------------+    +-------------------+
          | HE ArcGIS Services  |    | Heritage Gateway  |
          | NHLE (layers 0-10)  |    | www.heritage      |
          | AIM (layer 1)       |    |   gateway.org.uk  |
          | Conservation Areas  |    +-------------------+
          | Heritage at Risk    |
          +---------------------+
                  |
          +------------------------------------------+
          | ResponseCache (filesystem, TTL-based)     |
          | ~/.cache/chuk-mcp-her/{source}/{hash}.json|
          +------------------------------------------+
```

---

## Module Dependency Graph

```
server.py                           # CLI entry point (sync)
  +-- async_server.py               # Async server setup, tool registration
  |     +-- tools/discovery/api.py            # her_status, her_list_sources, her_capabilities
  |     +-- tools/nhle/api.py                 # her_search_monuments, her_get_monument,
  |     |                                     #   her_search_listed_buildings, her_search_designations,
  |     |                                     #   her_count_features
  |     +-- tools/aerial/api.py               # her_search_aerial, her_count_aerial,
  |     |                                     #   her_get_aerial_feature
  |     +-- tools/conservation_area/api.py    # her_search_conservation_areas,
  |     |                                     #   her_count_conservation_areas,
  |     |                                     #   her_get_conservation_area
  |     +-- tools/heritage_at_risk/api.py     # her_search_heritage_at_risk,
  |     |                                     #   her_count_heritage_at_risk,
  |     |                                     #   her_get_heritage_at_risk
  |     +-- tools/gateway/api.py              # her_search_heritage_gateway
  |     +-- tools/crossref/api.py             # her_cross_reference, her_nearby, her_enrich_gateway
  |     |     +-- core/spatial_index.py      # Grid-based spatial index (O(n+m) nearest-neighbour)
  |     +-- tools/export/api.py               # her_export_geojson, her_export_for_lidar
  |     +-- core/source_registry.py           # Central orchestrator, adapter dispatch
  |           +-- core/adapters/nhle.py              # NHLE adapter (queries ArcGIS)
  |           |     +-- core/arcgis_client.py        # Async HTTP client (rate-limited)
  |           |     |     +-- core/cache.py          # Filesystem-based response cache
  |           |     +-- core/coordinates.py          # BNG <-> WGS84 conversion
  |           +-- core/adapters/aim.py               # AIM adapter (queries ArcGIS)
  |           +-- core/adapters/conservation_area.py # Conservation Areas (queries ArcGIS)
  |           +-- core/adapters/heritage_at_risk.py  # Heritage at Risk (queries ArcGIS)
  |           +-- core/adapters/heritage_gateway.py  # Heritage Gateway (web scraper)
  |                 +-- core/gateway_client.py       # httpx + BeautifulSoup scraper

models/responses.py             # Response envelopes (extra="forbid")
constants.py                    # Enums, constants, messages
```

---

## Module Structure

```
src/chuk_mcp_her/
+-- __init__.py
+-- server.py              # Sync entry point (CLI, .env loading)
+-- async_server.py        # Async setup (ChukMCPServer, tool registration)
+-- constants.py           # Enums, constants, error/success messages
+-- core/
|   +-- __init__.py
|   +-- source_registry.py     # Central orchestrator (analogous to ArchiveManager)
|   +-- arcgis_client.py       # Async ArcGIS Feature Service HTTP client
|   +-- gateway_client.py      # Async Heritage Gateway web scraper (httpx + bs4)
|   +-- cache.py               # Filesystem-based response cache with TTL
|   +-- coordinates.py         # BNG <-> WGS84 coordinate conversion
|   +-- spatial_index.py       # Grid-based spatial index for nearest-neighbour
|   +-- adapters/
|       +-- __init__.py
|       +-- base.py                # BaseSourceAdapter ABC, PaginatedResult, SourceCapabilities
|       +-- nhle.py                # NHLE adapter (queries ArcGIS)
|       +-- aim.py                 # AIM adapter (queries ArcGIS)
|       +-- conservation_area.py   # Conservation Areas adapter (queries ArcGIS)
|       +-- heritage_at_risk.py    # Heritage at Risk adapter (queries ArcGIS)
|       +-- heritage_gateway.py    # Heritage Gateway adapter (web scraper)
+-- models/
|   +-- __init__.py
|   +-- responses.py       # Response envelopes (extra="forbid", to_text())
+-- tools/
    +-- __init__.py        # Tool group registration exports
    +-- discovery/         # her_status, her_list_sources, her_capabilities
    |   +-- __init__.py
    |   +-- api.py
    +-- nhle/              # her_search_monuments, her_get_monument,
    |   +-- __init__.py    #   her_search_listed_buildings, her_search_designations,
    |   +-- api.py         #   her_count_features
    +-- aerial/            # her_search_aerial, her_count_aerial,
    |   +-- __init__.py    #   her_get_aerial_feature
    |   +-- api.py
    +-- conservation_area/ # her_search_conservation_areas,
    |   +-- __init__.py    #   her_count_conservation_areas,
    |   +-- api.py         #   her_get_conservation_area
    +-- heritage_at_risk/  # her_search_heritage_at_risk,
    |   +-- __init__.py    #   her_count_heritage_at_risk,
    |   +-- api.py         #   her_get_heritage_at_risk
    +-- gateway/           # her_search_heritage_gateway
    |   +-- __init__.py
    |   +-- api.py
    +-- crossref/          # her_cross_reference, her_nearby
    |   +-- __init__.py
    |   +-- api.py
    +-- export/            # her_export_geojson, her_export_for_lidar
        +-- __init__.py
        +-- api.py
```

---

## Component Responsibilities

### `server.py`

Synchronous entry point. Parses command-line arguments (`--mode`, `--port`), loads
`.env` via `python-dotenv`, and starts the MCP server. This is the only file that
touches `sys.argv` or `os.environ` directly.

### `async_server.py`

Creates the `ChukMCPServer` MCP instance, instantiates `SourceRegistry`, and registers
all tool groups (8 categories, 23 tools). Each tool module receives the MCP instance
and the shared `SourceRegistry`.

### `core/source_registry.py`

The central orchestrator, analogous to `ArchiveManager` in chuk-mcp-maritime-archives.
Manages:
- **Adapter registry**: 5 source adapters (NHLE, AIM, Conservation Areas, Heritage at Risk, Heritage Gateway) keyed by `SourceId`
- **Unified query interface**: `search_monuments()`, `search_listed_buildings()`,
  `search_designations()`, `count_features()`, `search_conservation_areas()`,
  `search_heritage_at_risk()`, `search_heritage_gateway()`, `get_monument()`, `nearby()`
- **Source listing**: `list_sources()` returns metadata for all registered sources
- **Adapter dispatch**: routes queries to the appropriate adapter based on source ID

At initialization, `_register_default_adapters()` creates one instance of each adapter
class and stores them in the `_adapters` dict keyed by source ID.

### `core/arcgis_client.py`

Async HTTP client for ArcGIS Feature Service REST APIs. Provides:
- `query(layer_id, where, geometry, ...)` -- returns GeoJSON FeatureCollection
- `count(layer_id, ...)` -- uses `returnCountOnly=true` for fast counts
- `query_all(...)` -- auto-pagination up to max_records
- `make_envelope(xmin, ymin, xmax, ymax)` -- static helper for geometry envelopes

Handles connection pooling, rate limiting (configurable req/sec), exponential backoff
retry (3 attempts), and ArcGIS-level error detection. Caches responses via `ResponseCache`.

### `core/cache.py`

Filesystem-based response cache. Stores API responses as JSON files at
`~/.cache/chuk-mcp-her/{source}/{hash}.json`. Cache keys are deterministic SHA256
hashes of sorted query parameters. TTL is per-source (24h NHLE, 7d AIM, 1h Gateway).
Read/write errors are logged and ignored (query proceeds without cache).

### `core/coordinates.py`

BNG (EPSG:27700) to WGS84 (EPSG:4326) coordinate conversion. Two implementations:
- **Helmert approximation**: ~5m accuracy, zero dependencies (stdlib math)
- **pyproj Transformer**: sub-metre accuracy, requires pyproj (optional dependency)

The module automatically uses pyproj if installed, falling back to the Helmert
transformation. Provides: `bng_to_wgs84()`, `wgs84_to_bng()`, `bbox_wgs84_to_bng()`,
`bbox_bng_to_wgs84()`, `point_buffer_bng()`, `distance_m()`, `bearing_deg()`.

### `core/adapters/base.py`

Abstract base class for all source adapters. Defines:
- `source_id` -- unique identifier property
- `capabilities` -- `SourceCapabilities` dataclass declaring supported features
- `search()` -- spatial/text search returning `PaginatedResult`
- `get_by_id()` -- single record retrieval
- `count()` -- fast count across layers

`PaginatedResult` is a dataclass with `features`, `total_count`, `has_more`, and
`next_offset` fields for offset-based pagination.

### `core/adapters/nhle.py`

Fully implemented adapter for the NHLE ArcGIS Feature Service. Queries across 7
layers (listed building points/polygons, scheduled monuments, parks and gardens,
battlefields, protected wrecks, world heritage sites). Key features:
- Multi-layer queries with parallel counting via `asyncio.gather()`
- WHERE clause construction from name, description, and grade filters
- BNG envelope construction from lat/lon + radius
- Feature normalisation: maps ArcGIS fields (ListEntry, Name, Grade, etc.) to
  standard schema with both BNG and WGS84 coordinates

### `core/adapters/aim.py`

Fully implemented adapter for the AIM ArcGIS Feature Service. Queries Historic
England's Aerial Investigation and Mapping layer for archaeological features from
aerial photographs and LiDAR. Supports monument type and period filtering, spatial
queries, and feature normalisation to standard schema.

### `core/adapters/conservation_area.py`

Adapter for Historic England's Conservation Areas ArcGIS Feature Service. Queries
8,000+ conservation areas designated by Local Planning Authorities across England.
Supports text search (NAME LIKE), LPA filtering, and spatial queries. Uses
ArcGIS Layer 0 with BNG SRID 27700.

### `core/adapters/heritage_at_risk.py`

Adapter for Historic England's Heritage at Risk Register ArcGIS Feature Service.
Queries at-risk heritage assets with heritage category filtering. The service
uses SRID 3857 (Web Mercator) natively, so the adapter sends `in_sr=27700` and
`out_sr=27700` to let ArcGIS handle reprojection server-side.

### `core/adapters/heritage_gateway.py`

Web scraper adapter for the Heritage Gateway website, providing best-effort access
to 60+ local HERs. Uses `GatewayClient` for ASP.NET WebForms scraping with
ViewState, form POST, and AJAX polling. Returns empty results gracefully when
the Gateway is unavailable.

### `core/gateway_client.py`

Async HTTP client for Heritage Gateway web scraping. Handles:
- ViewState capture from initial GET
- Form POST with search parameters
- AJAX polling for results (up to 10 attempts, 500ms delay)
- HTML parsing with BeautifulSoup for result and detail pages
- Rate limiting (1 req/sec) and response caching

### `models/responses.py`

Pydantic v2 response models for every tool. All use `extra="forbid"` to catch
serialisation errors early. Each model carries a `to_text()` method for
human-readable output. Includes: `ErrorResponse`, `StatusResponse`,
`MonumentSearchResponse`, `MonumentDetailResponse`, `DesignationSearchResponse`,
`FeatureCountResponse`, `AerialSearchResponse`, `GatewaySearchResponse`,
`CrossReferenceResponse`, `NearbyResponse`, `GeoJSONExportResponse`,
`LiDARExportResponse`, and others.

### `constants.py`

All magic strings, identifiers, and configuration values. Includes:
- `ServerConfig` -- server name, version, description
- `SourceId`, `SOURCE_METADATA` -- source identifiers and metadata
- `NHLELayer` -- ArcGIS layer ID enum (0, 1, 6, 7, 8, 9, 10)
- `DESIGNATION_LAYERS`, `LAYER_DESIGNATION` -- designation type to layer mapping
- `ALL_NHLE_POINT_LAYERS` -- all non-polygon layers for broad queries
- `ErrorMessages`, `SuccessMessages` -- format-string message templates

---

## Data Flows

### Search -> Cache -> Detail

```
1. her_search_monuments(name="red hill", bbox="586000,205000,602500,215000")
   +-- tool validates params, parses bbox
   +-- registry.search_monuments(query="red hill", bbox=(586000,205000,...))
       +-- nhle_adapter.search(query="red hill", designation_type="scheduled_monument")
           +-- _resolve_layers("scheduled_monument") -> [6]
           +-- _build_where("red hill", None) -> "Name LIKE '%red hill%'"
           +-- _build_geometry(bbox) -> envelope dict
           +-- arcgis_client.count(layer_id=6, where=..., geometry=...)
           |   +-- cache.get("nhle/abc123.json", ttl=86400)  <-- cache check
           |   +-- if miss: httpx GET ...FeatureServer/6/query?returnCountOnly=true
           |   +-- cache.put("nhle/abc123.json", data)
           +-- arcgis_client.query(layer_id=6, where=..., geometry=...)
           |   +-- cache.get("nhle/def456.json", ttl=86400)  <-- cache check
           |   +-- if miss: httpx GET ...FeatureServer/6/query?f=geojson
           |   +-- cache.put("nhle/def456.json", data)
           +-- _normalize_feature() for each result
               +-- bng_to_wgs84(easting, northing) -> (lat, lon)
   +-- tool formats MonumentSearchResponse

2. her_get_monument(nhle_id="1002345")
   +-- registry.get_monument("1002345")
       +-- nhle_adapter.get_by_id("1002345")
           +-- tries each layer (0, 1, 6, 7, 8, 9, 10) until found
           +-- WHERE "ListEntry = '1002345'"
           +-- returns first match
   +-- tool formats MonumentDetailResponse
```

### Nearby Search

```
her_nearby(lat=51.8895, lon=0.9020, radius_m=500)
  +-- tool validates: lat/lon provided
  +-- wgs84_to_bng(51.8895, 0.9020) -> (easting, northing)
  +-- registry.search_designations(bbox=buffer, max_results=20)
      +-- nhle_adapter.search(bbox=buffer)
          +-- queries ALL_NHLE_POINT_LAYERS (6 layers)
          +-- asyncio.gather() for parallel count across all layers
          +-- merge and normalise results
  +-- compute distance_m and bearing_deg from centre to each result
  +-- sort results by distance
  +-- tool formats NearbyResponse
```

### Cross-Reference (LiDAR)

```
her_cross_reference(candidates='[{"easting":590625,"northing":208193}]',
                    include_aim=True)
  +-- parse JSON candidates
  +-- derive bounding box from all candidates + near_radius_m
  +-- registry.search_designations(bbox=buffer) -> NHLE known assets
  +-- if include_aim: registry.search_aerial(bbox=buffer) -> AIM features
  +-- if gateway_sites: merge enriched Gateway records
  +-- build GridSpatialIndex (cell_size = near_radius_m)
  +-- for each candidate:
      +-- index.nearest(easting, northing, near_radius_m)
      +-- if distance <= match_radius_m: classify as "match"
      +-- if distance <= near_radius_m: classify as "near"
      +-- else: classify as "novel"
  +-- _build_asset_dict() -> enriched output (11 fields per asset)
  +-- tool formats CrossReferenceResponse
```

### GeoJSON Export

```
her_export_geojson(bbox="586000,205000,602500,215000", designation_type="scheduled_monument")
  +-- registry.search_designations(bbox=..., designation_type=..., max_results=500)
  +-- for each feature:
      +-- build GeoJSON Feature with Point geometry (lon, lat)
      +-- properties: record_id, name, designation_type, source
  +-- return FeatureCollection
  +-- tool formats GeoJSONExportResponse
```

---

## Key Patterns

### Source Adapter Pattern

All source adapters implement `BaseSourceAdapter`:

1. Declare `source_id` and `capabilities` properties
2. Implement `search()`, `get_by_id()`, `count()` abstract methods
3. Receive shared `ResponseCache` at construction
4. Return `PaginatedResult` from search operations

The NHLE adapter is the reference implementation. AIM, Conservation Areas, and
Heritage at Risk adapters follow the same pattern using ArcGIS. The Heritage
Gateway adapter uses a web scraper client instead of ArcGIS.

### Multi-Layer Query Pattern

The NHLE adapter queries multiple ArcGIS layers for broad searches:

1. `_resolve_layers(designation_type)` determines which layers to query
2. If a single layer, query it directly with offset-based pagination
3. If multiple layers, `asyncio.gather()` counts each layer in parallel
4. Layer results are normalised and merged, with `designation_type` set per layer

### Dual Output Mode

All tools accept an `output_mode` parameter (`"json"` or `"text"`). The
`format_response()` helper checks for a `to_text()` method on the response model.
In JSON mode, `model_dump_json(indent=2, exclude_none=True)` produces clean output.
In text mode, each response model's `to_text()` returns a human-readable summary.

### Error Handling

All error messages are defined as format-string templates in `constants.py`:

```python
class ErrorMessages:
    SOURCE_NOT_FOUND = "Source '{}' not found. Available: {}"
    MONUMENT_NOT_FOUND = "Monument '{}' not found"
    NO_RESULTS = "No results found matching search criteria"
    ARCGIS_ERROR = "ArcGIS query failed: {}"
    # ...
```

Tool functions wrap all operations in try/except and return `ErrorResponse` on
failure -- never unhandled exceptions or stack traces. The ArcGIS client handles
retries and rate limiting internally:

- **429 responses**: exponential backoff retry (2, 4, 8 seconds)
- **5xx responses**: exponential backoff retry with logging
- **Timeout/connection errors**: retry with exponential backoff
- **ArcGIS-level errors**: parsed from response JSON and raised as RuntimeError

### Coordinate Conversion

The NHLE ArcGIS Feature Service uses British National Grid (EPSG:27700). The
spatial query flow is:

1. User provides lat/lon + radius_m (or BNG bbox)
2. If lat/lon: convert to BNG via `wgs84_to_bng()`
3. Create BNG envelope (easting +/- radius_m, northing +/- radius_m)
4. Send envelope as `geometry` parameter to ArcGIS query
5. Results include BNG coordinates from ArcGIS
6. Convert result BNG coordinates back to WGS84 via `bng_to_wgs84()`
7. Return both coordinate systems in the response

Two conversion methods are supported:

| Method | Accuracy | Dependency |
|--------|----------|------------|
| Helmert approximation | ~5m | None (stdlib math) |
| pyproj Transformer | Sub-metre | pyproj (optional) |

The module automatically uses pyproj if installed, falling back to the Helmert
transformation. For most heritage queries, ~5m accuracy is more than sufficient.

### Filesystem Cache

The `ResponseCache` class stores API responses as JSON files on disk:

```
~/.cache/chuk-mcp-her/
+-- arcgis_0/
|   +-- abc123def456.json     # Layer 0 query result
|   +-- 789012345678.json
+-- arcgis_6/
|   +-- fed098cba765.json     # Layer 6 query result
```

Cache keys are deterministic: `sha256(sorted_params)[:16]` ensures the same
query parameters always produce the same cache key.

| Source | Default TTL | Rationale |
|--------|-------------|-----------|
| NHLE | 24 hours | Designations change infrequently |
| AIM | 7 days | Aerial mapping data is very stable |
| Heritage Gateway | 1 hour | Local HER data may update more often |

Cache behaviour:
- **Cache-first reads**: every ArcGIS query checks the cache before making an HTTP request
- **TTL expiry**: cached entries older than the source TTL are deleted and re-fetched
- **Deterministic keys**: `ResponseCache.make_key(source_id, **params)` produces consistent keys
- **Graceful degradation**: cache read/write errors are logged and ignored (query proceeds)
- **Configurable location**: `HER_CACHE_DIR` environment variable overrides the default

---

## Testing Strategy

Tests use `pytest-asyncio` and mock at the HTTP boundary. No live API calls
are made during testing. 667 tests across 15 test modules (97% overall coverage):

- **Unit tests**: `test_coordinates.py` (BNG/WGS84 conversion), `test_constants.py`
  (enum values, metadata completeness), `test_cache.py` (cache TTL, key generation),
  `test_spatial_index.py` (grid cell lookup, nearest-neighbour, edge cases)
- **Adapter tests**: `test_nhle_adapter.py` (search, get_by_id, normalisation),
  `test_aim_adapter.py`, `test_conservation_area_adapter.py`,
  `test_heritage_at_risk_adapter.py`, `test_gateway_adapter.py`,
  `test_arcgis_client.py` (HTTP retry, rate limiting, error handling),
  `test_gateway_client.py` (ViewState parsing, HTML scraping, rate limiting)
- **Integration tests**: `test_source_registry.py` (adapter dispatch, capabilities),
  `test_tools.py` (all 23 tools end-to-end with mocked registry)
- **Model tests**: `test_responses.py` (extra="forbid" enforcement, to_text() output)
- **Import tests**: `test_server.py` (package imports, server module structure)

Mock boundary: tests mock `ArcGISClient.query()`, `ArcGISClient.count()`,
`GatewayClient` methods, or `SourceRegistry` methods, exercising the full data
flow from tool to adapter to client.
