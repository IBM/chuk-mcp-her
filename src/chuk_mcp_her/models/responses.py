"""
Response models for chuk-mcp-her.

All response envelopes use Pydantic v2 with extra="forbid" and
provide a to_text() method for human-readable output.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


# ============================================================================
# Shared
# ============================================================================


class ErrorResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    error: str
    error_type: str = "error"
    message: str = ""
    suggestion: str | None = None

    def to_text(self) -> str:
        parts = [f"Error: {self.error}"]
        if self.suggestion:
            parts.append(f"Suggestion: {self.suggestion}")
        return "\n".join(parts)


def format_response(response: BaseModel, output_mode: str = "json") -> str:
    """Format a response model as JSON or text."""
    if output_mode == "text":
        if hasattr(response, "to_text"):
            return response.to_text()
        return response.model_dump_json(indent=2, exclude_none=True)
    return response.model_dump_json(indent=2, exclude_none=True)


# ============================================================================
# Discovery
# ============================================================================


class SourceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: str
    name: str
    organisation: str | None = None
    coverage: str | None = None
    api_type: str | None = None
    description: str | None = None
    native_srid: int | None = None
    capabilities: list[str] = Field(default_factory=list)
    designation_types: list[str] = Field(default_factory=list)
    licence: str | None = None
    status: str = "available"
    note: str | None = None


class SourceListResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sources: list[SourceInfo]
    count: int
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for s in self.sources:
            status = f" [{s.status}]" if s.status != "available" else ""
            lines.append(f"  {s.source_id}: {s.name}{status}")
            if s.coverage:
                lines.append(f"    Coverage: {s.coverage}")
            if s.capabilities:
                lines.append(f"    Capabilities: {', '.join(s.capabilities)}")
        return "\n".join(lines)


class ToolInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    category: str
    description: str


class StatusSourceInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: str
    note: str | None = None


class StatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: str
    version: str
    sources: dict[str, StatusSourceInfo] = Field(default_factory=dict)
    tool_count: int
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, f"  Server: {self.server} v{self.version}", ""]
        for sid, info in self.sources.items():
            lines.append(f"  {sid}: {info.status}")
        return "\n".join(lines)


class CapabilitiesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    server: str
    version: str
    sources: list[SourceInfo]
    tools: list[ToolInfo]
    jurisdictions_available: list[str] = Field(default_factory=list)
    jurisdictions_roadmap: list[str] = Field(default_factory=list)
    spatial_references: list[int] = Field(default_factory=list)
    max_results_per_query: int = 2000
    tool_count: int = 0
    llm_guidance: str = ""
    message: str = ""

    def to_text(self) -> str:
        lines = [
            self.message,
            f"  Server: {self.server} v{self.version}",
            f"  Sources: {len(self.sources)}",
            f"  Tools: {self.tool_count}",
            "",
        ]
        for t in self.tools:
            lines.append(f"  {t.name}: {t.description}")
        if self.llm_guidance:
            lines.extend(["", f"  Guidance: {self.llm_guidance}"])
        return "\n".join(lines)


# ============================================================================
# Monument / Heritage Asset
# ============================================================================


class MonumentInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    nhle_id: str | None = None
    name: str
    source: str
    designation_type: str | None = None
    grade: str | None = None
    list_date: str | None = None
    amendment_date: str | None = None
    easting: float | None = None
    northing: float | None = None
    lat: float | None = None
    lon: float | None = None
    ngr: str | None = None
    url: str | None = None


class MonumentSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str | None = None
    count: int
    total_available: int | None = None
    monuments: list[MonumentInfo]
    has_more: bool = False
    next_offset: int | None = None
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for m in self.monuments:
            grade = f" (Grade {m.grade})" if m.grade else ""
            lines.append(f"  {m.record_id}: {m.name}{grade}")
            if m.designation_type:
                lines.append(f"    Type: {m.designation_type}")
            if m.lat is not None:
                lines.append(f"    Location: {m.lat}, {m.lon}")
        if self.has_more:
            lines.append(
                f"\n  Showing {self.count} of {self.total_available}. "
                f"Use offset={self.next_offset} for next page."
            )
        return "\n".join(lines)


class MonumentDetailResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    monument: dict[str, Any]
    geometry: dict[str, Any] | None = None
    message: str = ""

    def to_text(self) -> str:
        m = self.monument
        lines = [
            f"Monument: {m.get('nhle_id', '?')}",
            f"Name: {m.get('name', '?')}",
            f"Designation: {m.get('designation_type', '?')}",
        ]
        if m.get("grade"):
            lines.append(f"Grade: {m['grade']}")
        if m.get("lat"):
            lines.append(f"Location: {m['lat']}, {m['lon']}")
        if m.get("list_date"):
            lines.append(f"Listed: {m['list_date']}")
        if m.get("url"):
            lines.append(f"URL: {m['url']}")
        return "\n".join(lines)


# ============================================================================
# Designation Search
# ============================================================================


class DesignationInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    nhle_id: str | None = None
    name: str
    designation_type: str
    grade: str | None = None
    lat: float | None = None
    lon: float | None = None
    url: str | None = None


class DesignationSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str | None = None
    count: int
    total_available: int | None = None
    designations: list[DesignationInfo]
    has_more: bool = False
    next_offset: int | None = None
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for d in self.designations:
            grade = f" (Grade {d.grade})" if d.grade else ""
            lines.append(f"  {d.record_id}: {d.name} [{d.designation_type}]{grade}")
        if self.has_more:
            lines.append(
                f"\n  Showing {self.count} of {self.total_available}. "
                f"Use offset={self.next_offset} for next page."
            )
        return "\n".join(lines)


# ============================================================================
# Feature Count
# ============================================================================


class FeatureCountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    counts: dict[str, int]
    source: str = "nhle"
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for dtype, count in self.counts.items():
            if dtype != "total":
                lines.append(f"  {dtype}: {count}")
        lines.append(f"  Total: {self.counts.get('total', 0)}")
        return "\n".join(lines)


# ============================================================================
# Aerial Investigation Mapping
# ============================================================================


class AerialFeatureInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    aim_id: str | None = None
    name: str | None = None
    monument_type: str | None = None
    broad_type: str | None = None
    narrow_type: str | None = None
    period: str | None = None
    form: str | None = None
    evidence: str | None = None
    project: str | None = None
    her_no: str | None = None
    source_ref: str | None = None
    easting: float | None = None
    northing: float | None = None
    lat: float | None = None
    lon: float | None = None
    description: str | None = None
    url: str | None = None


class AerialSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str = "aim"
    count: int
    total_available: int | None = None
    features: list[AerialFeatureInfo]
    has_more: bool = False
    next_offset: int | None = None
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for f in self.features:
            loc = ""
            if f.lat is not None:
                loc = f" [{f.lat:.4f}, {f.lon:.4f}]"
            lines.append(f"  {f.aim_id or f.record_id}: {f.monument_type} ({f.period}){loc}")
        if self.has_more:
            lines.append(
                f"\n  Showing {self.count} of {self.total_available}. "
                f"Use offset={self.next_offset} for next page."
            )
        return "\n".join(lines)


class AerialCountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    count: int
    source: str = "aim"
    message: str = ""

    def to_text(self) -> str:
        return self.message


# ============================================================================
# Conservation Areas
# ============================================================================


class ConservationAreaInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    uid: int | None = None
    name: str | None = None
    lpa: str | None = None
    designation_date: str | None = None
    easting: float | None = None
    northing: float | None = None
    lat: float | None = None
    lon: float | None = None
    area_sqm: float | None = None


class ConservationAreaSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str = "conservation_area"
    count: int
    total_available: int | None = None
    areas: list[ConservationAreaInfo]
    has_more: bool = False
    next_offset: int | None = None
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for a in self.areas:
            lpa = f" [{a.lpa}]" if a.lpa else ""
            lines.append(f"  {a.record_id}: {a.name}{lpa}")
            if a.designation_date:
                lines.append(f"    Designated: {a.designation_date}")
        if self.has_more:
            lines.append(
                f"\n  Showing {self.count} of {self.total_available}. "
                f"Use offset={self.next_offset} for next page."
            )
        return "\n".join(lines)


class ConservationAreaCountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    count: int
    source: str = "conservation_area"
    message: str = ""

    def to_text(self) -> str:
        return self.message


# ============================================================================
# Heritage at Risk
# ============================================================================


class HeritageAtRiskInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    list_entry: int | None = None
    name: str | None = None
    heritage_category: str | None = None
    risk_methodology: str | None = None
    lat: float | None = None
    lon: float | None = None
    area_sqm: float | None = None
    url: str | None = None


class HeritageAtRiskSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str = "heritage_at_risk"
    count: int
    total_available: int | None = None
    entries: list[HeritageAtRiskInfo]
    has_more: bool = False
    next_offset: int | None = None
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for e in self.entries:
            cat = f" [{e.heritage_category}]" if e.heritage_category else ""
            lines.append(f"  {e.record_id}: {e.name}{cat}")
            if e.risk_methodology:
                lines.append(f"    Risk: {e.risk_methodology}")
        if self.has_more:
            lines.append(
                f"\n  Showing {self.count} of {self.total_available}. "
                f"Use offset={self.next_offset} for next page."
            )
        return "\n".join(lines)


class HeritageAtRiskCountResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    count: int
    source: str = "heritage_at_risk"
    message: str = ""

    def to_text(self) -> str:
        return self.message


# ============================================================================
# Heritage Gateway
# ============================================================================


class GatewayRecordInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_her: str | None = None
    record_id: str | None = None
    name: str | None = None
    monument_type: str | None = None
    period: str | None = None
    description: str | None = None
    grid_reference: str | None = None
    easting: float | None = None
    northing: float | None = None
    lat: float | None = None
    lon: float | None = None
    designation: str | None = None
    url: str | None = None


class GatewaySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str = "heritage_gateway"
    count: int
    total_available: int | None = None
    records: list[GatewayRecordInfo]
    has_more: bool = False
    note: str | None = None
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for r in self.records:
            loc = ""
            if r.grid_reference:
                loc = f" [{r.grid_reference}]"
            period = f" ({r.period})" if r.period else ""
            lines.append(f"  {r.record_id}: {r.name}")
            if r.monument_type:
                lines.append(f"    Type: {r.monument_type}{period}{loc}")
            if r.source_her:
                lines.append(f"    HER: {r.source_her}")
        if self.has_more:
            lines.append(
                f"\n  Showing {self.count} of {self.total_available}. "
                "More results may be available on Heritage Gateway."
            )
        if self.note:
            lines.extend(["", f"  Note: {self.note}"])
        return "\n".join(lines)


class GatewayEnrichResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    records: list[dict[str, Any]]
    count: int
    resolved_count: int
    unresolved_count: int
    fetch_details_used: bool
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        lines.append(f"  Resolved: {self.resolved_count}")
        lines.append(f"  Unresolved: {self.unresolved_count}")
        if self.records:
            lines.append("")
        for r in self.records[:10]:
            e = r.get("easting", "?")
            n = r.get("northing", "?")
            lines.append(f"  {r.get('record_id', '?')}: {r.get('name', '?')} [E={e}, N={n}]")
        if self.count > 10:
            lines.append(f"  ... and {self.count - 10} more")
        return "\n".join(lines)


# ============================================================================
# Scotland (NRHE + Designations)
# ============================================================================


class ScotlandRecordInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    canmore_id: str | None = None
    site_number: str | None = None
    name: str | None = None
    alt_name: str | None = None
    broad_class: str | None = None
    site_type: str | None = None
    form: str | None = None
    county: str | None = None
    council: str | None = None
    parish: str | None = None
    grid_reference: str | None = None
    easting: float | None = None
    northing: float | None = None
    lat: float | None = None
    lon: float | None = None
    url: str | None = None


class ScotlandSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str = "scotland"
    count: int
    total_available: int | None = None
    records: list[ScotlandRecordInfo]
    has_more: bool = False
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for r in self.records:
            site_type = f" [{r.site_type}]" if r.site_type else ""
            lines.append(f"  {r.record_id}: {r.name}{site_type}")
            if r.broad_class:
                lines.append(f"    Class: {r.broad_class}")
            if r.lat is not None:
                lines.append(f"    Location: {r.lat}, {r.lon}")
        if self.has_more:
            lines.append(f"\n  Showing {self.count}. More results may be available.")
        return "\n".join(lines)


class ScotlandDesignationInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str | None = None
    designation_reference: str | None = None
    name: str | None = None
    designation_type: str | None = None
    category: str | None = None
    designated_date: str | None = None
    local_authority: str | None = None
    easting: float | None = None
    northing: float | None = None
    lat: float | None = None
    lon: float | None = None
    url: str | None = None


class ScotlandDesignationSearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: dict[str, Any] | None = None
    source: str = "scotland"
    count: int
    total_available: int | None = None
    designations: list[ScotlandDesignationInfo]
    has_more: bool = False
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for d in self.designations:
            cat = f" ({d.category})" if d.category else ""
            lines.append(f"  {d.record_id}: {d.name} [{d.designation_type}]{cat}")
            if d.local_authority:
                lines.append(f"    Authority: {d.local_authority}")
            if d.lat is not None:
                lines.append(f"    Location: {d.lat}, {d.lon}")
        if self.has_more:
            lines.append(f"\n  Showing {self.count}. More results may be available.")
        return "\n".join(lines)


# ============================================================================
# Cross-Referencing
# ============================================================================


class CrossReferenceMatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidate: dict[str, float]
    matched_asset: dict[str, Any] | None = None
    nearest_asset: dict[str, Any] | None = None
    distance_m: float | None = None
    classification: str  # "match", "near", "novel"


class CrossReferenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    candidates_submitted: int
    classification: dict[str, int]
    matches: list[CrossReferenceMatch] = Field(default_factory=list)
    near_misses: list[CrossReferenceMatch] = Field(default_factory=list)
    novel_count: int = 0
    novel_summary: str | None = None
    message: str = ""

    def to_text(self) -> str:
        lines = [
            self.message,
            f"  Submitted: {self.candidates_submitted}",
            f"  Matches: {self.classification.get('match', 0)}",
            f"  Near: {self.classification.get('near', 0)}",
            f"  Novel: {self.classification.get('novel', 0)}",
        ]
        return "\n".join(lines)


# ============================================================================
# Nearby
# ============================================================================


class NearbyAssetInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    record_id: str
    nhle_id: str | None = None
    name: str
    designation_type: str | None = None
    grade: str | None = None
    distance_m: float | None = None
    bearing_deg: float | None = None
    lat: float | None = None
    lon: float | None = None
    easting: float | None = None
    northing: float | None = None


class NearbyResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    centre_lat: float
    centre_lon: float
    radius_m: float
    count: int
    assets: list[NearbyAssetInfo]
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for a in self.assets:
            dist = f" ({a.distance_m:.0f}m)" if a.distance_m is not None else ""
            lines.append(f"  {a.record_id}: {a.name}{dist}")
        return "\n".join(lines)


# ============================================================================
# Export
# ============================================================================


class GeoJSONExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    geojson: dict[str, Any]
    feature_count: int
    message: str = ""

    def to_text(self) -> str:
        return f"{self.message}\n  {self.feature_count} features in GeoJSON FeatureCollection"


class LiDARExportResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    bbox: list[float]
    known_sites: list[dict[str, Any]]
    count: int
    message: str = ""

    def to_text(self) -> str:
        lines = [self.message, ""]
        for s in self.known_sites[:10]:
            lines.append(f"  {s.get('id', '?')}: {s.get('name', '?')} [{s.get('type', '?')}]")
        if self.count > 10:
            lines.append(f"  ... and {self.count - 10} more")
        return "\n".join(lines)
