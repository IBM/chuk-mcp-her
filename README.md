# chuk-mcp-her

**Historic Environment Records MCP Server** -- A Model Context Protocol (MCP) server for querying Historic Environment Records across England and Scotland. Searches listed buildings, scheduled monuments, registered parks, battlefields, protected wrecks, and World Heritage Sites via live ArcGIS REST APIs from Historic England and Historic Environment Scotland.

> This is a demonstration project provided as-is for learning and testing purposes.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green.svg)](LICENSE)

## Features

This MCP server provides structured access to Historic Environment Records through **26 tools** across **9 categories**, querying **6 data sources** via live ArcGIS REST APIs and Heritage Gateway web scraping.

**Key capabilities:**
- **Source registry pattern** -- pluggable adapters for NHLE, AIM, Conservation Areas, Heritage at Risk, Heritage Gateway, and Scotland (HES) with unified query interface
- **England + Scotland coverage** -- English heritage via Historic England, Scottish heritage via Historic Environment Scotland (320,000+ NRHE records + designated assets)
- **Spatial-first queries** -- bounding box, point+radius, and area searches via ArcGIS Feature/Map Services
- **BNG/WGS84 coordinate support** -- automatic conversion between British National Grid (EPSG:27700) and WGS84 (EPSG:4326)
- **All tools return fully-typed Pydantic v2 models** for type safety, validation, and excellent IDE support
- **All tools support `output_mode="text"`** for human-readable output alongside the default JSON

### 1. Server Discovery (`her_status`, `her_list_sources`, `her_capabilities`)

Check server health, list registered data sources, and get full capabilities:
- Source availability and status
- Supported query types per source
- LLM guidance for query planning

### 2. NHLE Queries (`her_search_monuments`, `her_get_monument`, `her_search_listed_buildings`, `her_search_designations`, `her_count_features`)

Search the National Heritage List for England:
- Scheduled monuments by location, name, or description
- Listed buildings with grade filtering (I, II*, II)
- Generic designation search across all 6 designation types
- Fast feature counts without fetching full records
- Pagination with offset-based paging

### 3. Aerial Mapping (`her_search_aerial`, `her_count_aerial`, `her_get_aerial_feature`)

Search aerial investigation mapping data:
- Archaeological features from aerial photographs and LiDAR
- Cropmarks, earthworks, and features not in the NHLE
- Monument type and period filtering
- Fast feature counts without fetching full records
- Full details for individual aerial mapping features

### 4. Conservation Areas (`her_search_conservation_areas`, `her_count_conservation_areas`, `her_get_conservation_area`)

Search Historic England's 8,000+ conservation areas:
- Search by name, Local Planning Authority, or location
- Bounding box and point+radius spatial queries
- Fast counts without fetching full records
- Full details including designation date and area

### 5. Heritage at Risk (`her_search_heritage_at_risk`, `her_count_heritage_at_risk`, `her_get_heritage_at_risk`)

Search the Heritage at Risk Register:
- Annual register of heritage assets at risk of loss
- Filter by heritage category (Listed Building, Scheduled Monument, etc.)
- Spatial search by bounding box or point+radius
- Risk methodology details for each entry

### 6. Heritage Gateway (`her_search_heritage_gateway`)

Search local Historic Environment Records via Heritage Gateway:
- Best-effort access to 60+ local HERs via web scraping
- Undesignated sites, findspots, and HER monument entries
- Returns empty results gracefully when Gateway unavailable

### 7. Scotland (`her_search_scotland`, `her_get_scotland_record`, `her_search_scotland_designations`)

Search Historic Environment Scotland records:
- 320,000+ National Record of the Historic Environment (NRHE) records via Canmore Points
- Designated assets: listed buildings, scheduled monuments, gardens and designed landscapes, battlefields, world heritage sites, conservation areas, historic marine protected areas
- Site type, broad class, and council area filtering
- Full details for individual records by Canmore ID

### 8. Cross-Referencing (`her_cross_reference`, `her_enrich_gateway`, `her_nearby`)

Spatial matching, enrichment, and proximity search:
- Cross-reference candidate locations against known heritage assets
- Classify candidates as match, near, or novel
- Grid-based spatial indexing for efficient batch processing (O(n+m) amortised)
- Optional AIM aerial feature integration (`include_aim` parameter)
- Designation type filtering (single type or comma-separated)
- Enriched match output with 11 fields per asset (source, grade, monument_type, period, form, evidence)
- Enrich Gateway records with resolved BNG coordinates for cross-referencing
- Find nearby heritage assets with distance and bearing
- Accepts both WGS84 and BNG coordinates

### 9. Export (`her_export_geojson`, `her_export_for_lidar`)

Export and format results:
- GeoJSON FeatureCollection for QGIS, Leaflet, or other GIS tools
- LiDAR cross-reference format with enriched metadata per source:
  - NHLE sites with grade
  - AIM aerial features with monument_type, period, form, evidence
  - Gateway sites with monument_type and period
- Optional AIM integration (`include_aim`) and Gateway sites (`gateway_sites`) for LiDAR export

## Tool Reference

All tools accept an optional `output_mode` parameter (`"json"` default, or `"text"` for human-readable output).

| Tool | Category | Description | Status |
|------|----------|-------------|--------|
| `her_status` | Discovery | Server health and source availability | Active |
| `her_list_sources` | Discovery | List registered data sources with capabilities | Active |
| `her_capabilities` | Discovery | Full server capability listing for LLM planning | Active |
| `her_search_monuments` | NHLE | Search scheduled monuments by location or name | Active |
| `her_get_monument` | NHLE | Get full details for a specific monument | Active |
| `her_search_listed_buildings` | NHLE | Search listed buildings with grade filter | Active |
| `her_search_designations` | NHLE | Search across all designation types | Active |
| `her_count_features` | NHLE | Fast count of features in an area | Active |
| `her_search_aerial` | Aerial | Search aerial investigation mapping data | Active |
| `her_count_aerial` | Aerial | Count aerial mapping features in an area | Active |
| `her_get_aerial_feature` | Aerial | Get full details of an aerial mapping feature | Active |
| `her_search_conservation_areas` | Conservation | Search conservation areas by name, LPA, or location | Active |
| `her_count_conservation_areas` | Conservation | Count conservation areas in an area | Active |
| `her_get_conservation_area` | Conservation | Get full details of a conservation area | Active |
| `her_search_heritage_at_risk` | At Risk | Search heritage at risk register entries | Active |
| `her_count_heritage_at_risk` | At Risk | Count heritage at risk entries in an area | Active |
| `her_get_heritage_at_risk` | At Risk | Get full details of a heritage at risk entry | Active |
| `her_search_heritage_gateway` | Gateway | Search local HER data via Heritage Gateway | Active |
| `her_search_scotland` | Scotland | Search Scottish NRHE records (320K+ sites) | Active |
| `her_get_scotland_record` | Scotland | Get full details of a Scottish NRHE record | Active |
| `her_search_scotland_designations` | Scotland | Search Scottish designated heritage assets | Active |
| `her_cross_reference` | Cross-Ref | Cross-reference candidates against known assets | Active |
| `her_enrich_gateway` | Cross-Ref | Resolve Gateway record coordinates for cross-referencing | Active |
| `her_nearby` | Cross-Ref | Find heritage assets near a point | Active |
| `her_export_geojson` | Export | Export results as GeoJSON FeatureCollection | Active |
| `her_export_for_lidar` | Export | Export known sites for LiDAR cross-referencing | Active |

## Data Sources

| Source | Name | Organisation | Coverage | API Type | Status |
|--------|------|-------------|----------|----------|--------|
| `nhle` | National Heritage List for England | Historic England | England | ArcGIS Feature Service | Active |
| `aim` | Aerial Investigation and Mapping | Historic England | England | ArcGIS Feature Service | Active |
| `conservation_area` | Conservation Areas | Historic England / LPAs | England | ArcGIS Feature Service | Active |
| `heritage_at_risk` | Heritage at Risk Register | Historic England | England | ArcGIS Feature Service | Active |
| `heritage_gateway` | Heritage Gateway (Local HERs) | Historic England / Local HERs | England | Web scraper | Active |
| `scotland` | Historic Environment Scotland | Historic Environment Scotland | Scotland | ArcGIS Map Service | Active |

### NHLE Designation Types

| Type | Description |
|------|-------------|
| `listed_building` | Listed buildings (Grades I, II*, II) |
| `scheduled_monument` | Scheduled monuments |
| `park_and_garden` | Registered parks and gardens |
| `battlefield` | Registered battlefields |
| `protected_wreck` | Protected wreck sites |
| `world_heritage_site` | World Heritage Sites |

## Installation

### Using uvx (Recommended -- No Installation Required!)

```bash
uvx chuk-mcp-her
```

### Using uv (Recommended for Development)

```bash
# Install from PyPI
uv pip install chuk-mcp-her

# Or clone and install from source
git clone <repository-url>
cd chuk-mcp-her
uv sync --dev
```

### Using pip (Traditional)

```bash
pip install chuk-mcp-her
```

### Optional: Sub-metre Coordinate Accuracy

```bash
# Install pyproj for sub-metre BNG<->WGS84 conversion
# Without pyproj, Helmert approximation (~5m accuracy) is used
pip install chuk-mcp-her[pyproj]
```

## Usage

### With Claude Desktop

#### Option 1: Run Locally with uvx

**MacOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "her": {
      "command": "uvx",
      "args": ["chuk-mcp-her"]
    }
  }
}
```

#### Option 2: Run Locally with pip

```json
{
  "mcpServers": {
    "her": {
      "command": "chuk-mcp-her"
    }
  }
}
```

### With Python SDK

```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

server_params = StdioServerParameters(
    command="uvx",
    args=["chuk-mcp-her"],
)

async with stdio_client(server_params) as (read, write):
    async with ClientSession(read, write) as session:
        await session.initialize()
        result = await session.call_tool(
            "her_search_monuments",
            {"name": "Stonehenge", "max_results": 5},
        )
```

### Standalone

```bash
# STDIO mode (default, for MCP clients)
chuk-mcp-her stdio

# HTTP mode (for web access)
chuk-mcp-her http
chuk-mcp-her http --port 8010

# Auto-detect mode
chuk-mcp-her
```

**STDIO mode** is for MCP clients like Claude Desktop and mcp-cli.
**HTTP mode** runs a web server on http://localhost:8010 for HTTP-based MCP clients.

### CLI (mcp-cli)

```bash
mcp-cli chat --server her
```

## Example Usage

Once configured, you can ask questions like:

- "List the available heritage data sources"
- "Search for scheduled monuments near Stonehenge"
- "Find Grade I listed buildings in central London"
- "How many heritage assets are in this bounding box?"
- "Get the full record for monument 1002345"
- "What heritage assets are within 500m of the Tower of London?"
- "Export all scheduled monuments in the Maldon area as GeoJSON"
- "Cross-reference these LiDAR survey points against known heritage assets"
- "Search for protected wrecks along the English coast"
- "Find registered parks and gardens near Bath"
- "Search for all red hills along the north bank of the Blackwater estuary between Heybridge Basin and Tollesbury"
- "Find castles in the Scottish Highlands"
- "Search for brochs near Inverness"
- "What scheduled monuments are in Edinburgh?"

**Multi-source queries:** The tool descriptions guide LLM agents to combine
multiple sources automatically. A query like "find all red hills near the
Blackwater" will prompt the agent to search NHLE (designated monuments), AIM
(aerial mapping features), and Heritage Gateway (local HER records), then
merge the results for comprehensive coverage.

**Model-agnostic:** The MCP server works with any LLM provider that supports
function calling -- Claude, GPT, Gemini, or any other MCP-compatible client.
The same tools work identically through Claude Desktop, mcp-cli, or the
Python SDK.

### Running the Examples

```bash
cd examples

python capabilities_demo.py          # server capabilities, sources, tools
python quick_start.py                # quick intro: status, count, search, nearby
python nhle_search_demo.py           # scheduled monument and listed building search
python aerial_search_demo.py         # aerial investigation mapping features
python conservation_area_demo.py     # conservation area search
python heritage_at_risk_demo.py      # heritage at risk register
python nearby_demo.py                # find heritage assets near a point
python export_demo.py                  # GeoJSON export
python gateway_search_demo.py          # Heritage Gateway local HER search
python cross_reference_demo.py         # cross-reference candidates (with AIM)
python enrichment_pipeline_demo.py     # Gateway enrichment + cross-reference
python blackwater_estuary_scenario.py  # multi-source scenario
```

| Script | Network | Tools Demonstrated |
|--------|---------|-------------------|
| `capabilities_demo.py` | No | `her_capabilities`, `her_list_sources`, `her_status` |
| `quick_start.py` | Yes | `her_status`, `her_count_features`, `her_search_monuments`, `her_get_monument`, `her_nearby` |
| `nhle_search_demo.py` | Yes | `her_search_monuments`, `her_get_monument`, `her_search_listed_buildings`, `her_search_designations`, `her_count_features` |
| `aerial_search_demo.py` | Yes | `her_search_aerial`, `her_count_aerial`, `her_get_aerial_feature` |
| `conservation_area_demo.py` | Yes | `her_search_conservation_areas`, `her_count_conservation_areas`, `her_get_conservation_area` |
| `heritage_at_risk_demo.py` | Yes | `her_search_heritage_at_risk`, `her_count_heritage_at_risk`, `her_get_heritage_at_risk` |
| `nearby_demo.py` | Yes | `her_nearby` |
| `export_demo.py` | Yes | `her_export_geojson`, `her_export_for_lidar` |
| `gateway_search_demo.py` | Yes | `her_search_heritage_gateway` |
| `cross_reference_demo.py` | Yes | `her_cross_reference` (with `include_aim`) |
| `enrichment_pipeline_demo.py` | Yes | `her_enrich_gateway`, `her_search_heritage_gateway`, `her_cross_reference`, `her_count_features` |
| `blackwater_estuary_scenario.py` | Yes | Multi-source scenario using NHLE, AIM, Conservation Areas, Heritage at Risk |

## Architecture

```
                    MCP Client (Claude, mcp-cli, etc.)
                              |
                              | MCP protocol (stdio / HTTP)
                              v
                  +-------------------------------+
                  |       Tool Functions          |
                  | discovery/ nhle/ aerial/      |
                  | conservation_area/ scotland/  |
                  | heritage_at_risk/ gateway/    |
                  | crossref/ export/             |
                  +-------------------------------+
                              |
                              | validate params, format response
                              v
                  +-------------------------------+
                  |       SourceRegistry          |
                  |   (unified query interface)   |
                  +-------------------------------+
                  |     |     |     |     |     |
          NHLEAdapter   |  CA     HAR    |  ScotlandAdapter
            AIMAdapter  |  Adapter Adapter|  (2 clients)
                        |               GatewayAdapter
                v       v       v             v           v
        +------------------+  +------------------+  +------------------+
        |  ArcGIS Client   |  |  Gateway Client  |  |  ArcGIS Client   |
        | (HE FeatureSvr)  |  | (httpx, bs4)     |  | (HES MapServer)  |
        +------------------+  +------------------+  +------------------+
                |                      |                      |
                v                      v                      v
        +------------------+  +------------------+  +------------------+
        | HE ArcGIS Svc    |  | Heritage Gateway |  | inspire.hes.scot |
        | NHLE,AIM,CA,HAR  |  | (60+ local HERs) |  | Canmore, HES Des |
        +------------------+  +------------------+  +------------------+
```

Built on top of chuk-mcp-server, this server uses:

- **Async-First**: Native async/await with httpx for all HTTP requests
- **Type-Safe**: Pydantic v2 models with `extra="forbid"` for all responses
- **Source Registry Pattern**: Pluggable adapters registered at startup, queried through unified interface
- **BNG/WGS84 Conversion**: Helmert transformation with optional pyproj for sub-metre accuracy
- **Filesystem Cache**: TTL-based per-source caching to reduce API load
- **Rate Limiting**: Per-client rate limiting with exponential backoff on 429/5xx
- **Dual Output**: All 26 tools support `output_mode="text"` for human-readable responses
- **Error Messages**: All error strings from `ErrorMessages` constants -- no hardcoded strings

See [ARCHITECTURE.md](ARCHITECTURE.md) for design principles and data flow diagrams.
See [SPEC.md](SPEC.md) for the full tool specification with parameter tables.
See [ROADMAP.md](ROADMAP.md) for the development roadmap and planned features.

## Development

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd chuk-mcp-her

# Install with uv (recommended)
uv sync --dev

# Or with pip
pip install -e ".[dev]"
```

### Running Tests

```bash
# Run tests
pytest tests/

# Run tests with coverage
pytest tests/ --cov=src/chuk_mcp_her --cov-report=term-missing

# Run a specific test file
pytest tests/test_coordinates.py -v
```

### Code Quality

```bash
# Lint and format with ruff
ruff check src/ tests/
ruff format src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/ -x tests/
```

### Building

```bash
# Build package
python -m build

# Or with uv
uv build
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MCP_STDIO` | - | Set to any value to force stdio mode |
| `HER_CACHE_DIR` | `~/.cache/chuk-mcp-her` | Filesystem cache directory |
| `HER_NHLE_CACHE_TTL` | `86400` | NHLE cache TTL in seconds (24 hours) |
| `HER_AIM_CACHE_TTL` | `604800` | AIM cache TTL in seconds (7 days) |
| `HER_HG_CACHE_TTL` | `3600` | Heritage Gateway cache TTL in seconds (1 hour) |
| `HER_RATE_LIMIT` | `5.0` | Max requests per second to ArcGIS |
| `HER_TIMEOUT` | `30.0` | HTTP request timeout in seconds |

## License

Apache License 2.0 -- See [LICENSE](LICENSE) for details.

## References

- [Historic England](https://historicengland.org.uk/) -- National Heritage List for England
- [NHLE ArcGIS Feature Service](https://services-eu1.arcgis.com/ZOdPfBS3aqqDYPUQ/arcgis/rest/services/National_Heritage_List_for_England_NHLE_v02_VIEW/FeatureServer) -- Live data endpoint
- [ArcGIS REST API](https://developers.arcgis.com/rest/services-reference/enterprise/query-feature-service-layer/) -- Query specification
- [Historic Environment Scotland](https://www.historicenvironment.scot/) -- National Record of the Historic Environment
- [HES ArcGIS MapServer](https://inspire.hes.scot/arcgis/rest/services) -- Scottish heritage data endpoints
- [Heritage Gateway](https://www.heritagegateway.org.uk/) -- Federated HER search
- [Model Context Protocol](https://modelcontextprotocol.io/) -- MCP specification
- [Anthropic](https://www.anthropic.com/) -- Claude and MCP support
- [British National Grid](https://epsg.io/27700) -- EPSG:27700 coordinate reference system
