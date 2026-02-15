# Roadmap

Development roadmap for chuk-mcp-her.

---

## Completed

### Phase 1.0 -- NHLE Core

Core MCP server with 14 tools across 6 categories querying live ArcGIS REST APIs.

**ArcGIS Feature Service client:**
- Async HTTP client with httpx connection pooling
- Rate limiting (5 req/sec default) with exponential backoff on 429/5xx
- Automatic retry on timeout and connection errors (3 attempts)
- Filesystem-based response cache with per-source TTL
- Support for query, count, and paginated query_all operations
- GeoJSON output format for spatial features

**NHLE queries (5 tools):**
- `her_search_monuments` -- scheduled monuments by location, name, or description
- `her_get_monument` -- full details for a specific monument by NHLE ID
- `her_search_listed_buildings` -- listed buildings with grade filter (I, II*, II)
- `her_search_designations` -- generic search across all 6 designation types
- `her_count_features` -- fast count of features in an area without fetching records

**Discovery tools (3 tools):**
- `her_status` -- server health and source availability
- `her_list_sources` -- list registered data sources with capabilities
- `her_capabilities` -- full server capability listing for LLM planning

**Cross-referencing (2 tools):**
- `her_cross_reference` -- classify candidate locations as match/near/novel against known assets
- `her_nearby` -- find heritage assets near a point with distance and bearing

**Export (2 tools):**
- `her_export_geojson` -- export as GeoJSON FeatureCollection for QGIS/Leaflet
- `her_export_for_lidar` -- export known site centroids in LiDAR cross-reference format

**Stubbed tools (2 tools, registered but not yet functional):**
- `her_search_aerial` -- aerial investigation mapping (returns NotImplementedError)
- `her_search_heritage_gateway` -- Heritage Gateway local HER search (returns NotImplementedError)

**BNG/WGS84 coordinate handling:**
- Helmert transformation (~5m accuracy) with optional pyproj fallback (sub-metre)
- Automatic conversion between WGS84 lat/lon and BNG easting/northing
- Bounding box conversion, point buffering, distance and bearing calculations

**Infrastructure:**
- Source registry pattern with pluggable adapters
- Pydantic v2 response models with `extra="forbid"` and `to_text()`
- Error messages from `ErrorMessages` constants -- no hardcoded strings
- Filesystem cache at `~/.cache/chuk-mcp-her` with configurable TTL per source
- 4 example demos (capabilities, NHLE search, nearby, export)
- Tests with mocked HTTP (no live API calls)

**Deliverables:**
- 14 registered tools (12 active, 2 stubbed)
- 3 data sources (NHLE active, AIM stubbed, Heritage Gateway stubbed)
- 6 NHLE designation types (listed buildings, scheduled monuments, parks/gardens, battlefields, protected wrecks, World Heritage Sites)

### Phase 1.1 -- Aerial Investigation and Mapping

AIM adapter fully implemented. 16 tools across 6 categories (2 new aerial tools).

- **AIM adapter** fully implemented querying Historic England's ArcGIS Feature Service
- **Monument type filtering** -- cropmarks, earthworks, enclosures, field systems
- **Period filtering** -- Iron Age, Roman, Medieval, Post-Medieval, etc.
- **Feature normalisation** -- map AIM field names to standard monument format
- `her_search_aerial` becomes fully functional (was a stub)
- `her_count_aerial` -- fast count of aerial mapping features in an area
- `her_get_aerial_feature` -- get full details of an aerial mapping feature
- Tests for AIM adapter with mocked ArcGIS responses

**Deliverables:**
- 16 registered tools (14 active, 1 aerial stub activated, 2 new aerial tools, 1 gateway stub remaining)
- 3 data sources (NHLE active, AIM active, Heritage Gateway stubbed)

### Phase 1.2 -- Conservation Areas, Heritage at Risk, Heritage Gateway

Three new data sources. 23 tools across 8 categories.

**Conservation Areas adapter (3 tools):**
- `her_search_conservation_areas` -- search 8,000+ conservation areas by name, LPA, or location
- `her_count_conservation_areas` -- fast count without fetching records
- `her_get_conservation_area` -- full details by UID
- ArcGIS Feature Service via Historic England's Conservation_Areas endpoint
- LPA (Local Planning Authority) filtering

**Heritage at Risk adapter (3 tools):**
- `her_search_heritage_at_risk` -- search annual register of at-risk heritage assets
- `her_count_heritage_at_risk` -- fast count with optional category filter
- `her_get_heritage_at_risk` -- full details by List Entry number
- ArcGIS Feature Service via Historic England's Heritage_at_Risk_Register_2024 endpoint
- Heritage category filtering (Listed Building, Scheduled Monument, etc.)
- SRID handling: service uses 3857, adapter sends BNG with in_sr=27700

**Heritage Gateway adapter (1 tool, rewritten from stub):**
- `her_search_heritage_gateway` -- search 60+ local HERs via web scraping
- ASP.NET WebForms scraping with ViewState, form POST, AJAX polling
- BeautifulSoup HTML parsing for search results and detail pages
- Best-effort access -- returns empty results gracefully on failure
- Rate limiting (1 req/sec) and response caching

**Deliverables:**
- 23 registered tools (all active, including `her_enrich_gateway` for Gateway coordinate resolution)
- 5 data sources (NHLE, AIM, Conservation Areas, Heritage at Risk, Heritage Gateway)
- 529 tests, 11 demo scripts

---

### Phase 1.3 -- Cross-Referencing Enhancements

Spatial indexing, AIM integration, enriched output for cross-referencing and LiDAR export.

**Grid spatial index (`core/spatial_index.py`):**
- Pure Python `GridSpatialIndex` — grid-cell nearest-neighbour search
- Replaces O(n×m) brute-force with O(n+m) amortised lookup
- Configurable cell size (defaults to `near_radius_m` so 3×3 neighbourhood covers search)

**Enhanced cross-referencing (`tools/crossref/api.py`):**
- `include_aim` parameter — merge AIM aerial features into known-asset pool
- `designation_types` filter — single type pushed to API, comma-separated post-filtered
- Enriched match output — 11 fields per matched asset (record_id, name, source,
  designation_type, grade, monument_type, period, form, evidence, easting, northing)
- Uses `GridSpatialIndex` for all candidate classification

**Enhanced LiDAR export (`tools/export/api.py`):**
- `include_aim=True` now functional — merges AIM aerial features into known sites
- NHLE sites enriched with `grade`
- AIM sites include `monument_type`, `period`, `form`, `evidence`
- Gateway sites include `monument_type`, `period`

**Deliverables:**
- 23 tools (no new tools — internal enhancements only)
- 5 data sources
- 667 tests (529 → 667), 97% overall coverage, 12 demos

---

## Planned

---

### Phase 2.0 -- Scotland (Canmore)

Integrate Historic Environment Scotland's Canmore database.

- New `CanmoreAdapter` querying Canmore's online API
- Scottish Grid (EPSG:27700) coordinates (same as BNG for most of Scotland)
- Monument types, periods, and HER records specific to Scottish heritage
- `her_search_canmore` tool
- Coverage expanded from England to England + Scotland

### Phase 2.1 -- Wales (Coflein)

Integrate the Royal Commission on the Ancient and Historical Monuments of Wales.

- New `CofleinAdapter` for the Coflein database
- Welsh monument types and period classifications
- `her_search_coflein` tool
- Coverage expanded to England + Scotland + Wales

### Phase 2.2 -- New Heritage Gateway API

When the HBSMR Gateway 2.0 API becomes available, replace the web scraper
adapter with a proper REST API client.

- Structured JSON responses instead of HTML parsing
- Full pagination support
- Richer metadata per record
- Deprecate scraper-based adapter

---

### Phase 3.0 -- European Sources (Netherlands)

Integrate Rijksdienst voor het Cultureel Erfgoed (RCE) data.

- New `RCEAdapter` for Dutch heritage records
- Amersfoort / RD New (EPSG:28992) coordinate support
- `her_search_rce` tool
- Multi-jurisdiction dispatch: query England, Scotland, Wales, and Netherlands

### Phase 3.1 -- European Sources (Ireland)

Integrate the National Monuments Service (Republic of Ireland) and NIEA
(Northern Ireland).

- Irish Grid (EPSG:29903) coordinate support
- `her_search_nms` and `her_search_niea` tools

### Phase 3.2 -- European Sources (France)

Integrate the Merimee database (Monuments Historiques) from the French Ministry of Culture.

- `her_search_merimee` tool
- French coordinate system support

---

## Future Considerations

These are ideas being tracked but not yet committed to a specific version.

### LiDAR Integration

Deep integration with chuk-mcp-lidar for automated feature detection:
- Upload LiDAR-derived anomaly candidates for batch cross-referencing
- Overlay known heritage assets on hillshade/DTM visualisations
- Automated "new discovery" classification pipeline

### Multi-Source Cross-Referencing

Cross-reference heritage assets across multiple jurisdictions:
- Match English NHLE records with Scottish Canmore entries near the border
- Match Heritage Gateway local HER records with NHLE designations
- Entity resolution scoring across sources

### Temporal Queries

Support for historical states of the heritage register:
- When was a building listed? When was a monument scheduled?
- Track designation changes over time
- Amendment history for listed buildings

### Spatial Statistics

Server-side spatial analysis:
- Density mapping (heritage assets per km2)
- Clustering analysis (hot spots of heritage activity)
- Distribution by period and monument type

---

## Related Servers (Ecosystem)

This server is part of a composable stack of MCP servers:

| Server | Tools | Role |
|--------|-------|------|
| chuk-mcp-her | 23 | Historic Environment Records (England) |
| chuk-mcp-maritime-archives | 36 | Historical maritime shipping records |
| chuk-mcp-tides | 17 | Tidal data and harmonic prediction |
| chuk-mcp-dem | 4 | Bathymetry and elevation data |
| chuk-mcp-stac | 5 | Satellite imagery via STAC catalogues |

All servers follow the same patterns: Pydantic v2 models, dual output mode, async-first.

**Example heritage investigation pipeline:**
1. `her_search_monuments` -- find scheduled monuments in an area
2. `her_count_features` -- assess heritage density before detailed search
3. `her_export_for_lidar` -- get known sites for LiDAR cross-reference
4. `her_cross_reference` -- classify LiDAR anomalies against known assets
5. `her_nearby` -- check what other heritage assets are near a discovery
6. `her_export_geojson` -- export findings for GIS visualisation

---

## Data Sources

### Active

| Source | API Type | Endpoint | Status |
|--------|----------|----------|--------|
| NHLE | ArcGIS Feature Service | `services-eu1.arcgis.com/.../NHLE_v02_VIEW/FeatureServer` | Active |
| AIM | ArcGIS Feature Service | `services-eu1.arcgis.com/.../HE_AIM_data/FeatureServer` | Active |
| Conservation Areas | ArcGIS Feature Service | `services-eu1.arcgis.com/.../Conservation_Areas/FeatureServer` | Active |
| Heritage at Risk | ArcGIS Feature Service | `services-eu1.arcgis.com/.../Heritage_at_Risk_Register_2024/FeatureServer` | Active |
| Heritage Gateway | Web scraper | `www.heritagegateway.org.uk` | Active |

### Planned

| Source | Jurisdiction | API Type | Target Phase |
|--------|-------------|----------|-------------|
| Canmore | Scotland | REST API | 2.0 |
| Coflein | Wales | REST API | 2.1 |
| HBSMR Gateway 2.0 | England (local HERs) | REST API | 2.2 |
| RCE | Netherlands | REST API | 3.0 |
| NMS / NIEA | Ireland | REST API | 3.1 |
| Merimee | France | REST API | 3.2 |

---

## Contributing

See [README.md](README.md#development) for development setup. Key areas where help is welcome:

- **Heritage Gateway improvements** -- improving scraper resilience and adding detail page parsing
- **Test coverage** -- expanding test cases for coordinate edge cases and multi-layer queries
- **Documentation** -- improving tool descriptions and LLM guidance notes
- **New jurisdictions** -- adding adapters for Scotland, Wales, or European heritage databases
