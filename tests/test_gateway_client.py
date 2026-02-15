"""Tests for chuk_mcp_her.core.gateway_client — Heritage Gateway scraper client."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest

from chuk_mcp_her.core.gateway_client import (
    PERIOD_MAP,
    GatewayClient,
    _extract_metadata_from_text,
    _extract_record_from_link,
    _extract_record_from_row,
    _map_detail_field,
)


# ============================================================================
# Sample HTML constants
# ============================================================================

SAMPLE_SEARCH_HTML = """
<html><body>
<input type="hidden" name="__VIEWSTATE" value="ABC123" />
<input type="hidden" name="__VIEWSTATEGENERATOR" value="DEF456" />
<input type="hidden" name="__EVENTVALIDATION" value="GHI789" />
</body></html>
"""

SAMPLE_SEARCH_HTML_PARTIAL = """
<html><body>
<input type="hidden" name="__VIEWSTATE" value="ABC123" />
</body></html>
"""

SAMPLE_RESULTS_HTML = """
<html><body>
<div>
  <a href="/gateway/Results_Single.aspx?uid=MEX1001&resourceID=1">Red Hill, Goldhanger</a>
  <span>Roman red hill mound</span>
</div>
<div>
  <a href="/gateway/Results_Single.aspx?uid=MEX1002&resourceID=1">Saltern mound, Tollesbury</a>
  <span>Iron Age saltern</span>
</div>
</body></html>
"""

SAMPLE_RESULTS_NO_LINKS = """
<html><body>
<table>
  <tr class="result-row">
    <td>Cropmark enclosure, Heybridge</td>
    <td>Iron Age cropmark enclosure near the river</td>
  </tr>
  <tr class="result-item">
    <td>Roman settlement, Maldon</td>
    <td>Remains of Roman period settlement</td>
  </tr>
</table>
</body></html>
"""

SAMPLE_RESULTS_EMPTY = """
<html><body>
<div>No results found</div>
</body></html>
"""

SAMPLE_RESULTS_WITH_VIEWSTATE = """
<html><body>
<input type="hidden" name="__VIEWSTATE" value="RESULTS_VS" />
<input type="hidden" name="__VIEWSTATEGENERATOR" value="RESULTS_VSG" />
<div>Please wait while we compile the results...</div>
</body></html>
"""

SAMPLE_DETAIL_HTML = """
<html><body>
<title>Heritage Gateway - Red Hill, Goldhanger</title>
<table>
<tr><td>Name</td><td>Red Hill, Goldhanger</td></tr>
<tr><td>Monument Type</td><td>Red Hill</td></tr>
<tr><td>Period</td><td>Roman</td></tr>
<tr><td>Grid Reference</td><td>TL 9050 0850</td></tr>
<tr><td>Easting</td><td>590,500</td></tr>
<tr><td>Northing</td><td>208,500</td></tr>
<tr><td>Description</td><td>A red hill mound indicating salt production</td></tr>
<tr><td>County</td><td>Essex</td></tr>
<tr><td>Parish</td><td>Goldhanger</td></tr>
<tr><td>Source</td><td>Essex HER</td></tr>
</table>
</body></html>
"""

SAMPLE_DETAIL_DL_HTML = """
<html><body>
<title>Heritage Gateway - Saltern, Tollesbury</title>
<dl>
  <dt>Name:</dt><dd>Saltern mound, Tollesbury</dd>
  <dt>Monument Type:</dt><dd>Saltern</dd>
  <dt>Period:</dt><dd>Iron Age</dd>
  <dt>Grid Reference:</dt><dd>TL 9610 1185</dd>
  <dt>Description:</dt><dd>Remains of salt production site</dd>
</dl>
</body></html>
"""

SAMPLE_DETAIL_NO_NAME_HTML = """
<html><body>
<title>Heritage Gateway - Enclosure near Heybridge</title>
<table>
<tr><td>Monument Type</td><td>Enclosure</td></tr>
<tr><td>Period</td><td>Iron Age</td></tr>
</table>
</body></html>
"""

SAMPLE_DETAIL_EMPTY_HTML = """
<html><body>
</body></html>
"""

# Sample ASP.NET AJAX delta response containing an UpdatePanel with results
SAMPLE_AJAX_DELTA = (
    "118|updatePanel|panel1|"
    '<div><a href="/gateway/Results_Single.aspx?uid=MEX1001&resourceID=1">'
    "Red Hill, Goldhanger</a> <span>Roman</span></div>"
    "|8|hiddenField|__VIEWSTATE|NEWVS123|"
)

SAMPLE_AJAX_DELTA_EMPTY = "15|updatePanel|panel1|No results found|"


# ============================================================================
# Helpers
# ============================================================================


def _make_mock_response(text: str, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response with text content."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text
    resp.raise_for_status.return_value = None
    return resp


# ============================================================================
# TestParseHiddenFields
# ============================================================================


class TestParseHiddenFields:
    def test_extracts_viewstate(self):
        result = GatewayClient._parse_hidden_fields(SAMPLE_SEARCH_HTML)
        assert result["__VIEWSTATE"] == "ABC123"
        assert result["__VIEWSTATEGENERATOR"] == "DEF456"
        assert result["__EVENTVALIDATION"] == "GHI789"

    def test_handles_missing_fields(self):
        result = GatewayClient._parse_hidden_fields(SAMPLE_SEARCH_HTML_PARTIAL)
        assert result["__VIEWSTATE"] == "ABC123"
        assert "__VIEWSTATEGENERATOR" not in result
        assert "__EVENTVALIDATION" not in result

    def test_handles_empty_html(self):
        result = GatewayClient._parse_hidden_fields("")
        assert result == {}

    def test_captures_empty_value_fields(self):
        """Empty-value hidden fields are captured (needed for AJAX postback)."""
        html = '<input type="hidden" name="__VIEWSTATE" value="" />'
        result = GatewayClient._parse_hidden_fields(html)
        assert "__VIEWSTATE" in result
        assert result["__VIEWSTATE"] == ""

    def test_ignores_non_hidden_inputs(self):
        """Text inputs are correctly filtered out by type=hidden."""
        html = '<input type="text" name="__VIEWSTATE" value="SHOULD_IGNORE" />'
        fields = GatewayClient._parse_hidden_fields(html)
        assert "__VIEWSTATE" not in fields

    def test_captures_all_hidden_inputs(self):
        """All hidden inputs are captured, not just standard ASP.NET fields."""
        html = """
        <input type="hidden" name="__VIEWSTATE" value="VS" />
        <input type="hidden" name="customField" value="custom" />
        <input type="hidden" name="anotherField" value="42" />
        """
        result = GatewayClient._parse_hidden_fields(html)
        assert result["__VIEWSTATE"] == "VS"
        assert result["customField"] == "custom"
        assert result["anotherField"] == "42"


# ============================================================================
# TestResolvePeriod
# ============================================================================


class TestResolvePeriod:
    def test_none_returns_all_periods(self):
        assert GatewayClient._resolve_period(None) == "0"

    def test_empty_string_returns_all_periods(self):
        assert GatewayClient._resolve_period("") == "0"

    def test_roman(self):
        assert GatewayClient._resolve_period("Roman") == "43|410|ROMAN"

    def test_iron_age(self):
        assert GatewayClient._resolve_period("Iron Age") == "-800|43|IRON AGE"

    def test_medieval(self):
        assert GatewayClient._resolve_period("Medieval") == "1066|1540|MEDIEVAL"

    def test_case_insensitive(self):
        assert GatewayClient._resolve_period("ROMAN") == "43|410|ROMAN"
        assert GatewayClient._resolve_period("iron age") == "-800|43|IRON AGE"

    def test_whitespace_stripped(self):
        assert GatewayClient._resolve_period("  Roman  ") == "43|410|ROMAN"

    def test_unknown_period_returns_all(self):
        assert GatewayClient._resolve_period("Jurassic") == "0"

    def test_all_mapped_periods(self):
        for period_name, dropdown_value in PERIOD_MAP.items():
            assert GatewayClient._resolve_period(period_name) == dropdown_value


# ============================================================================
# TestBuildSearchForm
# ============================================================================


class TestBuildSearchForm:
    def setup_method(self):
        self.client = GatewayClient()

    def test_includes_what(self):
        result = self.client._build_search_form(what="red hill")
        assert result["ctl00$ContentPlaceHolder1$ctl03$txtWhat"] == "red hill"

    def test_includes_where(self):
        result = self.client._build_search_form(where="Essex")
        key = "ctl00$ContentPlaceHolder1$ctl01$TabContainer1$Tab2$txtLocation"
        assert result[key] == "Essex"

    def test_includes_when_as_dropdown_value(self):
        result = self.client._build_search_form(when="Roman")
        assert result["ctl00$ContentPlaceHolder1$ctl05$ddlWhenPeriods"] == "43|410|ROMAN"

    def test_when_all_periods_not_included(self):
        """'All Periods' (value 0) is not sent — server defaults to all."""
        result = self.client._build_search_form(when=None)
        assert "ctl00$ContentPlaceHolder1$ctl05$ddlWhenPeriods" not in result

    def test_optional_params_excluded_when_none(self):
        result = self.client._build_search_form()
        assert "ctl00$ContentPlaceHolder1$ctl03$txtWhat" not in result
        key = "ctl00$ContentPlaceHolder1$ctl01$TabContainer1$Tab2$txtLocation"
        assert key not in result
        assert "ctl00$ContentPlaceHolder1$ctl05$ddlWhenPeriods" not in result

    def test_always_includes_js_check_and_submit(self):
        result = self.client._build_search_form()
        assert result["ctl00$jsCheck"] == "1"
        assert result["ctl00$ContentPlaceHolder1$btnSubmit"] == "Search"

    def test_always_includes_event_target_and_argument(self):
        result = self.client._build_search_form()
        assert result["__EVENTTARGET"] == ""
        assert result["__EVENTARGUMENT"] == ""

    def test_no_viewstate_in_form_data(self):
        """Search form must NOT include ViewState (breaks the POST)."""
        result = self.client._build_search_form(what="test")
        assert "__VIEWSTATE" not in result

    def test_all_params(self):
        result = self.client._build_search_form(what="church", where="London", when="Medieval")
        assert result["ctl00$ContentPlaceHolder1$ctl03$txtWhat"] == "church"
        key = "ctl00$ContentPlaceHolder1$ctl01$TabContainer1$Tab2$txtLocation"
        assert result[key] == "London"
        assert result["ctl00$ContentPlaceHolder1$ctl05$ddlWhenPeriods"] == "1066|1540|MEDIEVAL"


# ============================================================================
# TestBuildAjaxCallback
# ============================================================================


class TestBuildAjaxCallback:
    def test_includes_hidden_fields(self):
        hidden = {"__VIEWSTATE": "ABC", "__VIEWSTATEGENERATOR": "DEF"}
        data, headers = GatewayClient._build_ajax_callback(hidden)
        assert data["__VIEWSTATE"] == "ABC"
        assert data["__VIEWSTATEGENERATOR"] == "DEF"

    def test_sets_event_target_to_timer(self):
        hidden = {"__VIEWSTATE": "ABC"}
        data, _ = GatewayClient._build_ajax_callback(hidden)
        assert "AJAX_Timer" in data["__EVENTTARGET"]

    def test_sets_async_post(self):
        hidden = {"__VIEWSTATE": "ABC"}
        data, _ = GatewayClient._build_ajax_callback(hidden)
        assert data["__ASYNCPOST"] == "true"

    def test_sets_script_manager(self):
        hidden = {"__VIEWSTATE": "ABC"}
        data, _ = GatewayClient._build_ajax_callback(hidden)
        key = "ctl00$ScriptManager1"
        assert key in data
        assert "AJAX_panel" in data[key]
        assert "AJAX_Timer" in data[key]

    def test_extra_headers(self):
        hidden = {}
        _, headers = GatewayClient._build_ajax_callback(hidden)
        assert headers["X-Requested-With"] == "XMLHttpRequest"
        assert headers["X-MicrosoftAjax"] == "Delta=true"


# ============================================================================
# TestParseAjaxDelta
# ============================================================================


class TestParseAjaxDelta:
    def test_parses_update_panel(self):
        delta = "11|updatePanel|panel1|Hello World|"
        result = GatewayClient._parse_ajax_delta(delta)
        assert result["panel1"] == "Hello World"

    def test_parses_hidden_field(self):
        delta = "5|hiddenField|__VIEWSTATE|ABCDE|"
        result = GatewayClient._parse_ajax_delta(delta)
        assert result["__hidden____VIEWSTATE"] == "ABCDE"

    def test_parses_multiple_segments(self):
        delta = "5|updatePanel|p1|Hello|3|hiddenField|vs|ABC|"
        result = GatewayClient._parse_ajax_delta(delta)
        assert result["p1"] == "Hello"
        assert result["__hidden__vs"] == "ABC"

    def test_handles_pipe_in_content(self):
        # Content is "a|b|c" which is 5 chars, but contains pipes
        delta = "5|updatePanel|p1|a|b|c|"
        result = GatewayClient._parse_ajax_delta(delta)
        assert result["p1"] == "a|b|c"

    def test_handles_empty_content(self):
        delta = "0|updatePanel|p1||"
        result = GatewayClient._parse_ajax_delta(delta)
        assert result["p1"] == ""

    def test_handles_empty_string(self):
        result = GatewayClient._parse_ajax_delta("")
        assert result == {}

    def test_handles_malformed_input(self):
        result = GatewayClient._parse_ajax_delta("not a valid delta")
        assert result == {}

    def test_ignores_non_panel_types(self):
        delta = "3|scriptBlock|s1|foo|5|updatePanel|p1|Hello|"
        result = GatewayClient._parse_ajax_delta(delta)
        assert "s1" not in result
        assert result["p1"] == "Hello"

    def test_sample_ajax_delta(self):
        result = GatewayClient._parse_ajax_delta(SAMPLE_AJAX_DELTA)
        assert "panel1" in result
        assert "Results_Single" in result["panel1"]
        assert result["__hidden____VIEWSTATE"] == "NEWVS123"


# ============================================================================
# TestParseResultsHtml
# ============================================================================


class TestParseResultsHtml:
    def test_extracts_records_from_links(self):
        records = GatewayClient._parse_results_html(SAMPLE_RESULTS_HTML)
        assert len(records) == 2
        assert records[0]["name"] == "Red Hill, Goldhanger"
        assert records[1]["name"] == "Saltern mound, Tollesbury"

    def test_extracts_record_id_from_uid(self):
        records = GatewayClient._parse_results_html(SAMPLE_RESULTS_HTML)
        assert records[0]["record_id"] == "MEX1001"
        assert records[0]["resource_id"] == "1"
        assert records[1]["record_id"] == "MEX1002"

    def test_extracts_url_from_href(self):
        records = GatewayClient._parse_results_html(SAMPLE_RESULTS_HTML)
        assert "Results_Single.aspx?uid=MEX1001" in records[0]["url"]

    def test_extracts_metadata_from_text(self):
        records = GatewayClient._parse_results_html(SAMPLE_RESULTS_HTML)
        assert records[0]["period"] == "Roman"
        assert records[0]["monument_type"] == "Red Hill"
        assert records[1]["period"] == "Iron Age"
        assert records[1]["monument_type"] == "Saltern"

    def test_returns_empty_for_no_matches(self):
        records = GatewayClient._parse_results_html(SAMPLE_RESULTS_EMPTY)
        assert records == []

    def test_fallback_to_row_parsing(self):
        records = GatewayClient._parse_results_html(SAMPLE_RESULTS_NO_LINKS)
        assert len(records) == 2
        assert records[0]["name"] == "Cropmark enclosure, Heybridge"
        assert records[1]["name"] == "Roman settlement, Maldon"

    def test_row_parsing_extracts_metadata(self):
        records = GatewayClient._parse_results_html(SAMPLE_RESULTS_NO_LINKS)
        # Second cell text contains "Iron Age" and "enclosure"
        assert records[0].get("period") == "Iron Age"
        assert records[0].get("monument_type") == "Enclosure"

    def test_empty_html(self):
        records = GatewayClient._parse_results_html("")
        assert records == []


# ============================================================================
# TestParseDetail
# ============================================================================


class TestParseDetail:
    def test_extracts_table_fields(self):
        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001"
        record = GatewayClient._parse_detail(SAMPLE_DETAIL_HTML, url)
        assert record is not None
        assert record["name"] == "Red Hill, Goldhanger"
        assert record["monument_type"] == "Red Hill"
        assert record["period"] == "Roman"
        assert record["grid_reference"] == "TL 9050 0850"
        assert record["easting"] == 590500.0
        assert record["northing"] == 208500.0
        assert record["description"] == "A red hill mound indicating salt production"
        assert record["county"] == "Essex"
        assert record["parish"] == "Goldhanger"
        assert record["source_her"] == "Essex HER"
        assert record["url"] == url

    def test_extracts_dl_fields(self):
        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1002"
        record = GatewayClient._parse_detail(SAMPLE_DETAIL_DL_HTML, url)
        assert record is not None
        assert record["name"] == "Saltern mound, Tollesbury"
        assert record["monument_type"] == "Saltern"
        assert record["period"] == "Iron Age"
        assert record["grid_reference"] == "TL 9610 1185"

    def test_extracts_name_from_title(self):
        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1003"
        record = GatewayClient._parse_detail(SAMPLE_DETAIL_NO_NAME_HTML, url)
        assert record is not None
        assert record["name"] == "Enclosure near Heybridge"

    def test_returns_none_for_empty_page(self):
        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=EMPTY"
        record = GatewayClient._parse_detail(SAMPLE_DETAIL_EMPTY_HTML, url)
        # Only url in record, so len == 1, returns None
        assert record is None


# ============================================================================
# TestExtractMetadataFromText
# ============================================================================


class TestExtractMetadataFromText:
    def test_period_detection_roman(self):
        record: dict = {}
        _extract_metadata_from_text(record, "A Roman red hill mound")
        assert record["period"] == "Roman"

    def test_period_detection_iron_age(self):
        record: dict = {}
        _extract_metadata_from_text(record, "An Iron Age settlement site")
        assert record["period"] == "Iron Age"

    def test_period_detection_medieval(self):
        record: dict = {}
        _extract_metadata_from_text(record, "Medieval church remains")
        assert record["period"] == "Medieval"

    def test_period_detection_neolithic(self):
        record: dict = {}
        _extract_metadata_from_text(record, "Neolithic flint scatter")
        assert record["period"] == "Neolithic"

    def test_period_detection_bronze_age(self):
        record: dict = {}
        _extract_metadata_from_text(record, "Bronze Age ring ditch")
        assert record["period"] == "Bronze Age"

    def test_monument_type_detection_red_hill(self):
        record: dict = {}
        _extract_metadata_from_text(record, "A red hill near the coast")
        assert record["monument_type"] == "Red Hill"

    def test_monument_type_detection_enclosure(self):
        record: dict = {}
        _extract_metadata_from_text(record, "Cropmark enclosure visible")
        assert record["monument_type"] == "Enclosure"

    def test_monument_type_detection_saltern(self):
        record: dict = {}
        _extract_metadata_from_text(record, "Iron Age saltern remains")
        assert record["monument_type"] == "Saltern"

    def test_monument_type_detection_settlement(self):
        record: dict = {}
        _extract_metadata_from_text(record, "Roman settlement evidence")
        assert record["monument_type"] == "Settlement"

    def test_does_not_overwrite_existing_period(self):
        record: dict = {"period": "Bronze Age"}
        _extract_metadata_from_text(record, "Roman settlement site")
        assert record["period"] == "Bronze Age"

    def test_does_not_overwrite_existing_monument_type(self):
        record: dict = {"monument_type": "Mound"}
        _extract_metadata_from_text(record, "Iron Age enclosure near a saltern")
        assert record["monument_type"] == "Mound"

    def test_no_match(self):
        record: dict = {}
        _extract_metadata_from_text(record, "Some unrelated text")
        assert "period" not in record
        assert "monument_type" not in record


# ============================================================================
# TestMapDetailField
# ============================================================================


class TestMapDetailField:
    def test_maps_name(self):
        record: dict = {}
        _map_detail_field(record, "Name", "Test Monument")
        assert record["name"] == "Test Monument"

    def test_maps_site_name(self):
        record: dict = {}
        _map_detail_field(record, "Site Name", "Test Site")
        assert record["name"] == "Test Site"

    def test_maps_monument_type(self):
        record: dict = {}
        _map_detail_field(record, "Monument Type", "Red Hill")
        assert record["monument_type"] == "Red Hill"

    def test_maps_period(self):
        record: dict = {}
        _map_detail_field(record, "Period", "Roman")
        assert record["period"] == "Roman"

    def test_maps_grid_reference(self):
        record: dict = {}
        _map_detail_field(record, "Grid Reference", "TL 9050 0850")
        assert record["grid_reference"] == "TL 9050 0850"

    def test_maps_grid_ref_alias(self):
        record: dict = {}
        _map_detail_field(record, "Grid Ref", "TL 9050 0850")
        assert record["grid_reference"] == "TL 9050 0850"

    def test_maps_ngr_alias(self):
        record: dict = {}
        _map_detail_field(record, "NGR", "TL 9050 0850")
        assert record["grid_reference"] == "TL 9050 0850"

    def test_easting_parsed_as_float(self):
        record: dict = {}
        _map_detail_field(record, "Easting", "590,500")
        assert record["easting"] == 590500.0

    def test_northing_parsed_as_float(self):
        record: dict = {}
        _map_detail_field(record, "Northing", "208,500")
        assert record["northing"] == 208500.0

    def test_easting_invalid_value_skipped(self):
        record: dict = {}
        _map_detail_field(record, "Easting", "not a number")
        assert "easting" not in record

    def test_unknown_field_ignored(self):
        record: dict = {}
        _map_detail_field(record, "Colour", "Red")
        assert "colour" not in record
        assert len(record) == 0

    def test_does_not_overwrite_existing(self):
        record: dict = {"name": "Original Name"}
        _map_detail_field(record, "Name", "New Name")
        assert record["name"] == "Original Name"

    def test_maps_description(self):
        record: dict = {}
        _map_detail_field(record, "Description", "A detailed description")
        assert record["description"] == "A detailed description"

    def test_maps_summary_to_description(self):
        record: dict = {}
        _map_detail_field(record, "Summary", "A summary text")
        assert record["description"] == "A summary text"

    def test_maps_her_number(self):
        record: dict = {}
        _map_detail_field(record, "HER Number", "MEX12345")
        assert record["her_number"] == "MEX12345"

    def test_maps_designation(self):
        record: dict = {}
        _map_detail_field(record, "Designation", "Scheduled Monument")
        assert record["designation"] == "Scheduled Monument"

    def test_maps_source(self):
        record: dict = {}
        _map_detail_field(record, "Source", "Essex HER")
        assert record["source_her"] == "Essex HER"

    def test_maps_data_source(self):
        record: dict = {}
        _map_detail_field(record, "Data Source", "Suffolk HER")
        assert record["source_her"] == "Suffolk HER"

    def test_label_case_insensitive(self):
        record: dict = {}
        _map_detail_field(record, "PERIOD", "Saxon")
        assert record["period"] == "Saxon"

    def test_label_with_trailing_whitespace(self):
        record: dict = {}
        _map_detail_field(record, "Period  ", "Medieval")
        assert record["period"] == "Medieval"


# ============================================================================
# TestSearch (async)
# ============================================================================


class TestSearch:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = GatewayClient()

    async def test_search_returns_records_immediate(self):
        """POST returns results page with links — no AJAX polling needed."""
        mock_http = AsyncMock()
        # POST to search → follows redirect → returns results with links
        post_resp = _make_mock_response(SAMPLE_RESULTS_HTML)
        mock_http.post = AsyncMock(return_value=post_resp)
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        result = await self.client.search(what="red hill")
        assert len(result["records"]) == 2
        assert result["records"][0]["name"] == "Red Hill, Goldhanger"
        assert result["total_count"] == 2

    async def test_search_via_ajax_polling(self):
        """POST returns 'please wait' page, AJAX poll returns results."""
        mock_http = AsyncMock()

        # Initial POST → "please wait" page with ViewState
        initial_resp = _make_mock_response(SAMPLE_RESULTS_WITH_VIEWSTATE)
        # AJAX poll → delta response with results
        ajax_resp = _make_mock_response(SAMPLE_AJAX_DELTA)

        mock_http.post = AsyncMock(side_effect=[initial_resp, ajax_resp])
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        result = await self.client.search(what="red hill")
        assert len(result["records"]) >= 1
        assert result["records"][0]["name"] == "Red Hill, Goldhanger"

    async def test_search_returns_empty_on_timeout(self):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        result = await self.client.search(what="test")
        assert result["records"] == []
        assert result["total_count"] == 0
        assert result["has_more"] is False

    async def test_search_returns_empty_on_connect_error(self):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=httpx.ConnectError("connection refused"))
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        result = await self.client.search(what="test")
        assert result["records"] == []
        assert result["total_count"] == 0

    async def test_search_returns_empty_on_unexpected_error(self):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=RuntimeError("unexpected"))
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        result = await self.client.search(what="test")
        assert result["records"] == []

    async def test_search_caches_results(self):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        client = GatewayClient(cache=mock_cache)

        mock_http = AsyncMock()
        post_resp = _make_mock_response(SAMPLE_RESULTS_HTML)
        mock_http.post = AsyncMock(return_value=post_resp)
        mock_http.is_closed = False

        client._client = mock_http
        client._last_request_time = 0.0

        await client.search(what="red hill")
        mock_cache.put.assert_called_once()
        cached_data = mock_cache.put.call_args[0][1]
        assert len(cached_data["records"]) == 2

    async def test_search_returns_cached_result(self):
        cached_result = {
            "records": [{"name": "Cached Record"}],
            "total_count": 1,
            "has_more": False,
        }
        mock_cache = MagicMock()
        mock_cache.get.return_value = cached_result

        client = GatewayClient(cache=mock_cache)
        result = await client.search(what="red hill")
        assert result == cached_result

    async def test_search_respects_max_results(self):
        mock_http = AsyncMock()
        post_resp = _make_mock_response(SAMPLE_RESULTS_HTML)
        mock_http.post = AsyncMock(return_value=post_resp)
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        result = await self.client.search(what="red hill", max_results=1)
        assert len(result["records"]) == 1
        assert result["has_more"] is True


# ============================================================================
# TestPollWithAjax (async)
# ============================================================================


class TestPollWithAjax:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = GatewayClient()

    async def test_returns_empty_without_viewstate(self):
        """Cannot poll without ViewState in the initial HTML."""
        records = await self.client._poll_with_ajax("<html></html>")
        assert records == []

    async def test_returns_records_from_delta(self):
        mock_http = AsyncMock()
        ajax_resp = _make_mock_response(SAMPLE_AJAX_DELTA)
        mock_http.post = AsyncMock(return_value=ajax_resp)
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        records = await self.client._poll_with_ajax(SAMPLE_RESULTS_WITH_VIEWSTATE)
        assert len(records) >= 1
        assert records[0]["name"] == "Red Hill, Goldhanger"

    async def test_returns_empty_on_no_results_delta(self):
        mock_http = AsyncMock()
        ajax_resp = _make_mock_response(SAMPLE_AJAX_DELTA_EMPTY)
        mock_http.post = AsyncMock(return_value=ajax_resp)
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        records = await self.client._poll_with_ajax(SAMPLE_RESULTS_WITH_VIEWSTATE)
        assert records == []

    async def test_handles_poll_timeout(self):
        mock_http = AsyncMock()
        mock_http.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        records = await self.client._poll_with_ajax(SAMPLE_RESULTS_WITH_VIEWSTATE)
        assert records == []

    async def test_updates_viewstate_between_polls(self):
        """ViewState from delta response is used in subsequent polls."""
        mock_http = AsyncMock()

        # First poll: delta with updated ViewState but no results
        delta_no_results = "8|hiddenField|__VIEWSTATE|UPDATED!|"
        # Second poll: delta with results
        call_count = 0

        async def mock_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_mock_response(delta_no_results)
            return _make_mock_response(SAMPLE_AJAX_DELTA)

        mock_http.post = mock_post
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        records = await self.client._poll_with_ajax(SAMPLE_RESULTS_WITH_VIEWSTATE)
        assert len(records) >= 1


# ============================================================================
# TestBuildResult
# ============================================================================


class TestBuildResult:
    def setup_method(self):
        self.client = GatewayClient()

    def test_builds_basic_result(self):
        records = [{"name": "A"}, {"name": "B"}]
        result = self.client._build_result(records, 50, None)
        assert result["records"] == records
        assert result["total_count"] == 2
        assert result["has_more"] is False

    def test_truncates_to_max_results(self):
        records = [{"name": "A"}, {"name": "B"}, {"name": "C"}]
        result = self.client._build_result(records, 2, None)
        assert len(result["records"]) == 2
        assert result["total_count"] == 3
        assert result["has_more"] is True

    def test_caches_result(self):
        mock_cache = MagicMock()
        client = GatewayClient(cache=mock_cache)
        records = [{"name": "A"}]
        client._build_result(records, 50, "test_key")
        mock_cache.put.assert_called_once_with(
            "test_key",
            {
                "records": records,
                "total_count": 1,
                "has_more": False,
            },
        )

    def test_no_cache_when_key_is_none(self):
        mock_cache = MagicMock()
        client = GatewayClient(cache=mock_cache)
        client._build_result([{"name": "A"}], 50, None)
        mock_cache.put.assert_not_called()


# ============================================================================
# TestGetRecord (async)
# ============================================================================


class TestGetRecord:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.client = GatewayClient()

    async def test_get_record_returns_detail(self):
        mock_http = AsyncMock()
        detail_resp = _make_mock_response(SAMPLE_DETAIL_HTML)
        mock_http.get = AsyncMock(return_value=detail_resp)
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001"
        record = await self.client.get_record(url)
        assert record is not None
        assert record["name"] == "Red Hill, Goldhanger"
        assert record["monument_type"] == "Red Hill"

    async def test_get_record_returns_none_on_timeout(self):
        mock_http = AsyncMock()
        mock_http.get = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
        mock_http.is_closed = False

        self.client._client = mock_http
        self.client._last_request_time = 0.0

        result = await self.client.get_record("https://example.com/detail")
        assert result is None

    async def test_get_record_caches_result(self):
        mock_cache = MagicMock()
        mock_cache.get.return_value = None

        client = GatewayClient(cache=mock_cache)

        mock_http = AsyncMock()
        detail_resp = _make_mock_response(SAMPLE_DETAIL_HTML)
        mock_http.get = AsyncMock(return_value=detail_resp)
        mock_http.is_closed = False

        client._client = mock_http
        client._last_request_time = 0.0

        url = "https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001"
        await client.get_record(url)
        mock_cache.put.assert_called_once()


# ============================================================================
# TestRateLimit (async)
# ============================================================================


class TestRateLimit:
    async def test_rate_limiting_delays_requests(self):
        client = GatewayClient()
        # Set last request time to now so the next call must wait
        client._last_request_time = time.monotonic()

        start = time.monotonic()
        await client._rate_limit()
        elapsed = time.monotonic() - start

        # Should have waited at least close to _min_interval
        assert elapsed >= client._min_interval * 0.5

    async def test_no_delay_when_enough_time_elapsed(self):
        client = GatewayClient()
        # Set last request far in the past
        client._last_request_time = time.monotonic() - 10.0

        start = time.monotonic()
        await client._rate_limit()
        elapsed = time.monotonic() - start

        # Should return almost immediately
        assert elapsed < 0.1


# ============================================================================
# TestClose (async)
# ============================================================================


class TestClose:
    async def test_close_closes_client(self):
        client = GatewayClient()
        mock_http = AsyncMock()
        mock_http.is_closed = False
        mock_http.aclose = AsyncMock()
        client._client = mock_http

        await client.close()
        mock_http.aclose.assert_called_once()
        assert client._client is None

    async def test_close_when_no_client(self):
        client = GatewayClient()
        # Should not raise
        await client.close()

    async def test_close_when_already_closed(self):
        client = GatewayClient()
        mock_http = MagicMock()
        mock_http.is_closed = True
        client._client = mock_http

        await client.close()
        # aclose should not be called on already-closed client


# ============================================================================
# TestExtractRecordFromLink
# ============================================================================


class TestExtractRecordFromLink:
    def test_extracts_name_and_url(self):
        from bs4 import BeautifulSoup

        html = '<div><a href="/gateway/Results_Single.aspx?uid=MEX1001&resourceID=1">Red Hill</a></div>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        record = _extract_record_from_link(link)
        assert record is not None
        assert record["name"] == "Red Hill"
        assert "MEX1001" in record["url"]
        assert record["record_id"] == "MEX1001"
        assert record["resource_id"] == "1"

    def test_returns_none_for_empty_text(self):
        from bs4 import BeautifulSoup

        html = '<a href="/gateway/Results_Single.aspx?uid=MEX1001"></a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        record = _extract_record_from_link(link)
        assert record is None

    def test_handles_absolute_url(self):
        from bs4 import BeautifulSoup

        html = '<a href="https://www.heritagegateway.org.uk/gateway/Results_Single.aspx?uid=MEX1001">Test</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        record = _extract_record_from_link(link)
        assert record["url"].startswith("https://")

    def test_handles_relative_url_without_slash(self):
        from bs4 import BeautifulSoup

        html = '<a href="Results_Single.aspx?uid=MEX1001">Test</a>'
        soup = BeautifulSoup(html, "html.parser")
        link = soup.find("a")
        record = _extract_record_from_link(link)
        assert "gateway/Results_Single.aspx" in record["url"]


# ============================================================================
# TestExtractRecordFromRow
# ============================================================================


class TestExtractRecordFromRow:
    def test_extracts_from_row_with_link(self):
        from bs4 import BeautifulSoup

        html = """
        <tr class="result-row">
          <td><a href="/gateway/Results_Single.aspx?uid=MEX1001">Red Hill</a></td>
          <td>Roman mound</td>
        </tr>
        """
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find("tr")
        record = _extract_record_from_row(row)
        assert record is not None
        assert record["name"] == "Red Hill"
        assert "MEX1001" in record["url"]

    def test_extracts_from_row_without_link(self):
        from bs4 import BeautifulSoup

        html = """
        <tr class="result-row">
          <td>Cropmark site</td>
          <td>Iron Age enclosure</td>
        </tr>
        """
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find("tr")
        record = _extract_record_from_row(row)
        assert record is not None
        assert record["name"] == "Cropmark site"

    def test_returns_none_for_empty_row(self):
        from bs4 import BeautifulSoup

        html = "<tr></tr>"
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find("tr")
        record = _extract_record_from_row(row)
        assert record is None

    def test_returns_none_for_no_name(self):
        from bs4 import BeautifulSoup

        html = "<tr><td></td></tr>"
        soup = BeautifulSoup(html, "html.parser")
        row = soup.find("tr")
        record = _extract_record_from_row(row)
        assert record is None


# ============================================================================
# TestGetClient (async)
# ============================================================================


class TestGetClient:
    async def test_creates_client_on_first_call(self):
        client = GatewayClient()
        assert client._client is None
        http_client = await client._get_client()
        assert http_client is not None
        assert isinstance(http_client, httpx.AsyncClient)
        await client.close()

    async def test_reuses_existing_client(self):
        client = GatewayClient()
        http1 = await client._get_client()
        http2 = await client._get_client()
        assert http1 is http2
        await client.close()

    async def test_recreates_closed_client(self):
        client = GatewayClient()
        http1 = await client._get_client()
        await http1.aclose()
        http2 = await client._get_client()
        assert http2 is not http1
        assert not http2.is_closed
        await client.close()
