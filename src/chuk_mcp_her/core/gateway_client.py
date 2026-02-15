"""
Async client for Heritage Gateway web scraping.

Handles form submission and ASP.NET AJAX result polling for the
Heritage Gateway advanced search.  Best-effort access — returns
empty results gracefully when the Gateway is unavailable.

The Heritage Gateway is an ASP.NET WebForms application.  After
POSTing the search form, results load asynchronously via a
ScriptManager Timer that triggers UpdatePanel partial postbacks.
We replicate this AJAX mechanism to retrieve results.
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx
from bs4 import BeautifulSoup

from ..constants import GatewayConfig
from .cache import ResponseCache

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (compatible; chuk-mcp-her/0.3.0; +https://github.com/chuk-ai/chuk-mcp-her)"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-GB,en;q=0.5",
}


# ============================================================================
# ASP.NET AJAX constants for Results.aspx polling
# ============================================================================

_TIMER_CONTROL = "ctl00$ContentPlaceHolder1$TabContainer1$TabPanel1$AJAX_Timer"
_AJAX_PANEL = "ctl00$ContentPlaceHolder1$TabContainer1$TabPanel1$AJAX_panel"
_SCRIPT_MANAGER = "ctl00$ScriptManager1"


# ============================================================================
# Period dropdown values (Heritage Gateway advanced search)
# ============================================================================

PERIOD_MAP: dict[str, str] = {
    "roman": "43|410|ROMAN",
    "iron age": "-800|43|IRON AGE",
    "medieval": "1066|1540|MEDIEVAL",
    "post medieval": "1540|1901|POST MEDIEVAL",
    "post-medieval": "1540|1901|POST MEDIEVAL",
    "neolithic": "-4000|-2200|NEOLITHIC",
    "bronze age": "-2600|-700|BRONZE AGE",
    "saxon": "410|1066|EARLY MEDIEVAL",
    "early medieval": "410|1066|EARLY MEDIEVAL",
    "modern": "1901|2050|MODERN",
    "prehistoric": "-500000|43|PREHISTORIC",
}


class GatewayClient:
    """Async client for Heritage Gateway form scraping.

    Workflow:
    1. POST search form to advanced_search.aspx (no ViewState)
    2. Follow redirect to Results.aspx
    3. Parse Results.aspx for ViewState (needed for AJAX callbacks)
    4. POST AJAX Timer callbacks to poll for results
    5. Parse ASP.NET AJAX delta responses for result HTML
    6. Extract records from result HTML
    """

    def __init__(
        self,
        cache: ResponseCache | None = None,
        cache_ttl: int = 3600,
        timeout: float = 30.0,
    ) -> None:
        self._cache = cache
        self._cache_ttl = cache_ttl
        self._timeout = timeout
        self._min_interval = 1.0 / GatewayConfig.RATE_LIMIT_PER_SEC
        self._last_request_time = 0.0
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout),
                headers=_HEADERS,
                follow_redirects=True,
                limits=httpx.Limits(max_connections=5, max_keepalive_connections=2),
            )
        return self._client

    async def _rate_limit(self) -> None:
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_interval:
            await asyncio.sleep(self._min_interval - elapsed)
        self._last_request_time = time.monotonic()

    @staticmethod
    def _parse_hidden_fields(html: str) -> dict[str, str]:
        """Extract all hidden form fields from HTML.

        Captures __VIEWSTATE, __VIEWSTATEGENERATOR, and any other
        hidden inputs needed for AJAX postback.
        """
        soup = BeautifulSoup(html, "html.parser")
        fields: dict[str, str] = {}
        for inp in soup.find_all("input", {"type": "hidden"}):
            name = inp.get("name")
            if name and isinstance(name, str):
                val = inp.get("value", "")
                fields[name] = val if isinstance(val, str) else ""
        return fields

    @staticmethod
    def _resolve_period(when: str | None) -> str:
        """Map human-readable period name to dropdown value.

        Returns ``"0"`` (All Periods) if the period is not recognised.
        """
        if not when:
            return "0"
        return PERIOD_MAP.get(when.lower().strip(), "0")

    def _build_search_form(
        self,
        what: str | None = None,
        where: str | None = None,
        when: str | None = None,
    ) -> dict[str, str]:
        """Build POST form data for advanced_search.aspx.

        Uses the current form field names (discovered Feb 2026).
        Does NOT include ViewState — omitting it causes the server
        to dispatch the search to all 71+ HER resources automatically.
        """
        data: dict[str, str] = {
            "__EVENTTARGET": "",
            "__EVENTARGUMENT": "",
            "ctl00$jsCheck": "1",
        }

        if what:
            data["ctl00$ContentPlaceHolder1$ctl03$txtWhat"] = what
        if where:
            data["ctl00$ContentPlaceHolder1$ctl01$TabContainer1$Tab2$txtLocation"] = where

        period_val = self._resolve_period(when)
        if period_val != "0":
            data["ctl00$ContentPlaceHolder1$ctl05$ddlWhenPeriods"] = period_val

        data["ctl00$ContentPlaceHolder1$btnSubmit"] = "Search"
        return data

    @staticmethod
    def _build_ajax_callback(
        hidden_fields: dict[str, str],
    ) -> tuple[dict[str, str], dict[str, str]]:
        """Build AJAX Timer callback POST data for Results.aspx.

        Returns ``(form_data, extra_headers)`` for the ASP.NET AJAX
        partial postback triggered by the Timer control.
        """
        data: dict[str, str] = {}
        data.update(hidden_fields)
        data[_SCRIPT_MANAGER] = f"{_AJAX_PANEL}|{_TIMER_CONTROL}"
        data["__EVENTTARGET"] = _TIMER_CONTROL
        data["__EVENTARGUMENT"] = ""
        data["__ASYNCPOST"] = "true"

        extra_headers = {
            "X-Requested-With": "XMLHttpRequest",
            "X-MicrosoftAjax": "Delta=true",
        }
        return data, extra_headers

    @staticmethod
    def _parse_ajax_delta(text: str) -> dict[str, str]:
        """Parse ASP.NET AJAX delta response.

        Format: ``length|type|id|content|length|type|id|content|...``

        The *length* field tells how many characters the *content*
        spans, which handles pipe characters inside content correctly.

        Returns dict mapping panel IDs to HTML content for
        ``updatePanel`` entries, and ``__hidden__{name}`` to value
        for ``hiddenField`` entries.
        """
        panels: dict[str, str] = {}
        pos = 0
        text_len = len(text)

        while pos < text_len:
            # Field 1: content length (integer)
            pipe1 = text.find("|", pos)
            if pipe1 == -1:
                break
            try:
                content_length = int(text[pos:pipe1])
            except ValueError:
                break

            # Field 2: type
            pipe2 = text.find("|", pipe1 + 1)
            if pipe2 == -1:
                break
            dtype = text[pipe1 + 1 : pipe2]

            # Field 3: id
            pipe3 = text.find("|", pipe2 + 1)
            if pipe3 == -1:
                break
            panel_id = text[pipe2 + 1 : pipe3]

            # Field 4: content (exactly content_length chars)
            content_start = pipe3 + 1
            content_end = content_start + content_length
            if content_end > text_len:
                break
            content = text[content_start:content_end]

            # Move past content + trailing |
            pos = content_end + 1

            if dtype == "updatePanel":
                panels[panel_id] = content
            elif dtype == "hiddenField":
                panels[f"__hidden__{panel_id}"] = content

        return panels

    # ================================================================
    # Search
    # ================================================================

    async def search(
        self,
        what: str | None = None,
        where: str | None = None,
        when: str | None = None,
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Execute a Heritage Gateway search.

        Returns dict with keys: ``records``, ``total_count``, ``has_more``.
        Returns empty results gracefully on any error.
        """
        cache_key = None
        if self._cache is not None:
            cache_key = ResponseCache.make_key(
                "gateway_search",
                what=what or "",
                where=where or "",
                when=when or "",
                max_results=max_results,
            )
            cached = self._cache.get(cache_key, self._cache_ttl)
            if cached is not None:
                logger.debug("Cache hit for Gateway search")
                return cached

        try:
            client = await self._get_client()

            # POST search form (no ViewState — dispatches to all resources)
            form_data = self._build_search_form(what=what, where=where, when=when)
            await self._rate_limit()

            # POST follows redirect to Results.aspx
            response = await client.post(
                GatewayConfig.SEARCH_URL,
                data=form_data,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Referer": GatewayConfig.SEARCH_URL,
                    "Origin": GatewayConfig.BASE_URL,
                },
            )

            results_html = response.text

            # Try immediate parse (results may load without AJAX)
            records = self._parse_results_html(results_html)
            if records:
                return self._build_result(records, max_results, cache_key)

            # Poll via AJAX Timer callbacks
            records = await self._poll_with_ajax(results_html)
            return self._build_result(records, max_results, cache_key)

        except (httpx.TimeoutException, httpx.HTTPStatusError, httpx.ConnectError) as e:
            logger.warning("Heritage Gateway search failed: %s", e)
            return {"records": [], "total_count": 0, "has_more": False}
        except Exception as e:
            logger.warning("Heritage Gateway unexpected error: %s", e)
            return {"records": [], "total_count": 0, "has_more": False}

    def _build_result(
        self,
        records: list[dict[str, Any]],
        max_results: int,
        cache_key: str | None,
    ) -> dict[str, Any]:
        """Package records into the standard search result dict."""
        result = {
            "records": records[:max_results],
            "total_count": len(records),
            "has_more": len(records) > max_results,
        }
        if cache_key and self._cache is not None:
            self._cache.put(cache_key, result)
        return result

    async def _poll_with_ajax(self, initial_html: str) -> list[dict[str, Any]]:
        """Poll Results.aspx using ASP.NET AJAX Timer callbacks.

        The Heritage Gateway Results page uses a ScriptManager Timer
        to check whether federated searches across 71+ HER resources
        have completed.  We replicate the Timer's partial postback.
        """
        client = await self._get_client()
        hidden_fields = self._parse_hidden_fields(initial_html)

        if not hidden_fields.get("__VIEWSTATE"):
            logger.debug("No ViewState in Results page — cannot poll")
            return []

        for attempt in range(GatewayConfig.POLL_MAX_ATTEMPTS):
            await asyncio.sleep(GatewayConfig.POLL_INTERVAL_S)
            await self._rate_limit()

            form_data, extra_headers = self._build_ajax_callback(hidden_fields)

            try:
                response = await client.post(
                    GatewayConfig.RESULTS_URL,
                    data=form_data,
                    headers={
                        **extra_headers,
                        "Content-Type": "application/x-www-form-urlencoded",
                        "Referer": GatewayConfig.RESULTS_URL,
                    },
                )
            except (httpx.TimeoutException, httpx.ConnectError) as e:
                logger.debug("AJAX poll %d failed: %s", attempt + 1, e)
                continue

            if response.status_code != 200:
                logger.debug("AJAX poll %d: status %d", attempt + 1, response.status_code)
                continue

            response_text = response.text

            # Try parsing as AJAX delta response
            panels = self._parse_ajax_delta(response_text)

            # Update ViewState from delta for next poll iteration
            for key, value in panels.items():
                if key.startswith("__hidden__"):
                    field_name = key[len("__hidden__") :]
                    hidden_fields[field_name] = value

            # Check UpdatePanel content for result links
            for key, html in panels.items():
                if key.startswith("__hidden__"):
                    continue
                records = self._parse_results_html(html)
                if records:
                    return records

            # Fallback: try parsing full response as HTML
            records = self._parse_results_html(response_text)
            if records:
                return records

            # Check for completion indicators
            text_lower = response_text.lower()
            if "no results" in text_lower or "0 results" in text_lower:
                logger.debug("Gateway returned no results")
                return []

        logger.debug(
            "AJAX polling exhausted after %d attempts",
            GatewayConfig.POLL_MAX_ATTEMPTS,
        )
        return []

    # ================================================================
    # Results parsing
    # ================================================================

    @staticmethod
    def _parse_results_html(html: str) -> list[dict[str, Any]]:
        soup = BeautifulSoup(html, "html.parser")
        records: list[dict[str, Any]] = []

        links = soup.find_all("a", href=lambda h: h and "Results_Single" in h)
        for link in links:
            record = _extract_record_from_link(link)
            if record:
                records.append(record)

        if not records:
            rows = soup.find_all("tr", class_=lambda c: c and "result" in c.lower()) if soup else []
            for row in rows:
                record = _extract_record_from_row(row)
                if record:
                    records.append(record)

        return records

    # ================================================================
    # Detail page
    # ================================================================

    async def get_record(self, url: str) -> dict[str, Any] | None:
        cache_key = None
        if self._cache is not None:
            cache_key = ResponseCache.make_key("gateway_detail", url=url)
            cached = self._cache.get(cache_key, self._cache_ttl)
            if cached is not None:
                return cached

        try:
            client = await self._get_client()
            await self._rate_limit()
            response = await client.get(url)
            response.raise_for_status()
            record = self._parse_detail(response.text, url)
            if record and cache_key and self._cache is not None:
                self._cache.put(cache_key, record)
            return record
        except (httpx.TimeoutException, httpx.HTTPStatusError) as e:
            logger.warning("Failed to fetch Gateway record %s: %s", url, e)
            return None

    @staticmethod
    def _parse_detail(html: str, url: str) -> dict[str, Any] | None:
        soup = BeautifulSoup(html, "html.parser")
        record: dict[str, Any] = {"url": url}

        for table in soup.find_all("table"):
            for row in table.find_all("tr"):
                cells = row.find_all(["td", "th"])
                if len(cells) >= 2:
                    label = cells[0].get_text(strip=True).rstrip(":")
                    value = cells[1].get_text(strip=True)
                    if label and value:
                        _map_detail_field(record, label, value)

        for dl in soup.find_all("dl"):
            dts = dl.find_all("dt")
            dds = dl.find_all("dd")
            for dt, dd in zip(dts, dds):
                label = dt.get_text(strip=True).rstrip(":")
                value = dd.get_text(strip=True)
                if label and value:
                    _map_detail_field(record, label, value)

        if "name" not in record:
            title_tag = soup.find("title")
            if title_tag:
                text = title_tag.get_text(strip=True)
                if " - " in text:
                    record["name"] = text.split(" - ", 1)[-1]
                else:
                    record["name"] = text

        return record if len(record) > 1 else None

    async def close(self) -> None:
        if self._client is not None and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


# ============================================================================
# Record extraction helpers (unchanged from v0.3.0)
# ============================================================================


def _extract_record_from_link(link: Any) -> dict[str, Any] | None:
    href = link.get("href", "")
    name = link.get_text(strip=True)
    if not name:
        return None

    record: dict[str, Any] = {"name": name}

    if href.startswith("/"):
        record["url"] = f"{GatewayConfig.BASE_URL}{href}"
    elif href.startswith("http"):
        record["url"] = href
    else:
        record["url"] = f"{GatewayConfig.BASE_URL}/gateway/{href}"

    if "uid=" in href:
        for part in href.split("?")[-1].split("&"):
            if part.startswith("uid="):
                record["record_id"] = part.split("=")[1]
            elif part.startswith("resourceID="):
                record["resource_id"] = part.split("=")[1]

    parent = link.parent
    if parent:
        text = parent.get_text(" ", strip=True)
        _extract_metadata_from_text(record, text)

    return record


def _extract_record_from_row(row: Any) -> dict[str, Any] | None:
    cells = row.find_all("td")
    if not cells:
        return None

    record: dict[str, Any] = {}

    link = row.find("a", href=lambda h: h and "Results_Single" in h)
    if link:
        record["name"] = link.get_text(strip=True)
        href = link.get("href", "")
        if href.startswith("/"):
            record["url"] = f"{GatewayConfig.BASE_URL}{href}"
        elif href.startswith("http"):
            record["url"] = href

    for i, cell in enumerate(cells):
        text = cell.get_text(strip=True)
        if i == 0 and "name" not in record:
            record["name"] = text
        elif text:
            _extract_metadata_from_text(record, text)

    return record if record.get("name") else None


def _extract_metadata_from_text(record: dict[str, Any], text: str) -> None:
    text_lower = text.lower()
    periods = [
        "Prehistoric",
        "Mesolithic",
        "Neolithic",
        "Bronze Age",
        "Iron Age",
        "Roman",
        "Saxon",
        "Medieval",
        "Post Medieval",
        "Post-Medieval",
        "Modern",
        "Multi-period",
        "Unknown",
    ]
    for period in periods:
        if period.lower() in text_lower and "period" not in record:
            record["period"] = period
            break

    types = [
        "red hill",
        "saltern",
        "mound",
        "enclosure",
        "ditch",
        "findspot",
        "settlement",
        "church",
        "manor",
        "farm",
        "earthwork",
        "cropmark",
        "ring ditch",
        "field system",
    ]
    for mtype in types:
        if mtype in text_lower and "monument_type" not in record:
            record["monument_type"] = mtype.title()
            break


def _map_detail_field(record: dict[str, Any], label: str, value: str) -> None:
    label_lower = label.lower().strip()
    field_map = {
        "name": "name",
        "site name": "name",
        "monument name": "name",
        "monument type": "monument_type",
        "type": "monument_type",
        "period": "period",
        "date": "period",
        "description": "description",
        "summary": "description",
        "grid reference": "grid_reference",
        "grid ref": "grid_reference",
        "ngr": "grid_reference",
        "national grid reference": "grid_reference",
        "easting": "easting",
        "northing": "northing",
        "district": "district",
        "parish": "parish",
        "county": "county",
        "her number": "her_number",
        "her no": "her_number",
        "mon uid": "record_id",
        "uid": "record_id",
        "designation": "designation",
        "protected status": "designation",
        "source": "source_her",
        "data source": "source_her",
    }
    mapped = field_map.get(label_lower)
    if mapped and mapped not in record:
        if mapped in ("easting", "northing"):
            try:
                record[mapped] = float(value.replace(",", ""))
            except ValueError:
                pass
        else:
            record[mapped] = value
