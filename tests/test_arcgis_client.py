"""Tests for chuk_mcp_her.core.arcgis_client."""

from __future__ import annotations

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from chuk_mcp_her.core.arcgis_client import ArcGISClient

BASE_URL = "https://services-eu1.arcgis.com/test/FeatureServer"


def _make_mock_response(data: dict, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    resp = MagicMock(spec=httpx.Response)
    resp.status_code = status_code
    resp.json.return_value = data
    resp.text = json.dumps(data)
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            message=f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


class TestArcGISClientQuery:
    @pytest.fixture
    def client(self):
        return ArcGISClient(
            base_url=BASE_URL,
            cache=None,
            timeout=5.0,
            max_retries=1,
            rate_limit_per_sec=0,
        )

    async def test_query_builds_correct_url(self, client, mocker):
        """Verify query() calls the correct URL with expected params."""
        geojson_response = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"ListEntry": "1000001", "Name": "Test Church"},
                    "geometry": {"type": "Point", "coordinates": [533500, 180500]},
                }
            ],
        }
        mock_get = AsyncMock(return_value=_make_mock_response(geojson_response))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query(layer_id=0, where="Name LIKE '%Church%'")

        assert result["type"] == "FeatureCollection"
        assert len(result["features"]) == 1

        # Verify URL contains the correct layer path
        call_args = mock_get.call_args
        url = call_args[0][0] if call_args[0] else call_args[1].get("url", "")
        assert "/0/query" in url

    async def test_query_with_geometry(self, client, mocker):
        """Verify query() passes geometry parameters correctly."""
        response_data = {"type": "FeatureCollection", "features": []}
        mock_get = AsyncMock(return_value=_make_mock_response(response_data))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        envelope = ArcGISClient.make_envelope(530000, 170000, 540000, 190000)
        await client.query(layer_id=6, geometry=envelope)

        call_args = mock_get.call_args
        params = call_args[1].get("params", {}) if call_args[1] else {}
        assert "geometry" in params
        assert "geometryType" in params
        assert params["geometryType"] == "esriGeometryEnvelope"

    async def test_query_returns_features(self, client, mocker):
        """Verify parsed response contains features."""
        response_data = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"ListEntry": "1000001"},
                    "geometry": {"type": "Point", "coordinates": [0, 0]},
                },
                {
                    "type": "Feature",
                    "properties": {"ListEntry": "1000002"},
                    "geometry": {"type": "Point", "coordinates": [1, 1]},
                },
            ],
        }
        mock_get = AsyncMock(return_value=_make_mock_response(response_data))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query(layer_id=0)
        assert len(result["features"]) == 2


class TestArcGISClientCount:
    async def test_count_returns_count(self, mocker):
        client = ArcGISClient(
            base_url=BASE_URL,
            cache=None,
            timeout=5.0,
            max_retries=1,
            rate_limit_per_sec=0,
        )
        response_data = {"count": 42}
        mock_get = AsyncMock(return_value=_make_mock_response(response_data))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.count(layer_id=6)
        assert result == 42

    async def test_count_returns_zero_when_missing(self, mocker):
        client = ArcGISClient(
            base_url=BASE_URL,
            cache=None,
            timeout=5.0,
            max_retries=1,
            rate_limit_per_sec=0,
        )
        response_data = {}
        mock_get = AsyncMock(return_value=_make_mock_response(response_data))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.count(layer_id=6)
        assert result == 0


class TestArcGISClientMakeEnvelope:
    def test_make_envelope(self):
        env = ArcGISClient.make_envelope(100, 200, 300, 400)
        assert env == {"xmin": 100, "ymin": 200, "xmax": 300, "ymax": 400}

    def test_make_envelope_floats(self):
        env = ArcGISClient.make_envelope(100.5, 200.5, 300.5, 400.5)
        assert env["xmin"] == 100.5
        assert env["ymax"] == 400.5


class TestArcGISClientErrorHandling:
    async def test_arcgis_error_in_response(self, mocker):
        """ArcGIS returns 200 but with error in JSON body."""
        client = ArcGISClient(
            base_url=BASE_URL,
            cache=None,
            timeout=5.0,
            max_retries=1,
            rate_limit_per_sec=0,
        )
        error_response = {
            "error": {
                "code": 400,
                "message": "Invalid query parameters",
                "details": [],
            }
        }
        mock_get = AsyncMock(return_value=_make_mock_response(error_response))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        with pytest.raises(RuntimeError, match="ArcGIS error"):
            await client.query(layer_id=0)

    async def test_retry_on_500_error(self, mocker):
        """Server 500 errors should be retried."""
        client = ArcGISClient(
            base_url=BASE_URL,
            cache=None,
            timeout=5.0,
            max_retries=1,
            rate_limit_per_sec=0,
        )
        # First call returns 500, retries exhausted
        mock_get = AsyncMock(
            return_value=_make_mock_response({"error": "Internal Server Error"}, status_code=500)
        )
        mocker.patch("httpx.AsyncClient.get", mock_get)
        # Patch asyncio.sleep to avoid real delays
        mocker.patch("asyncio.sleep", new_callable=AsyncMock)

        with pytest.raises((RuntimeError, httpx.HTTPStatusError)):
            await client.query(layer_id=0)

        # Should have been called at least once (initial attempt)
        assert mock_get.call_count >= 1


class TestArcGISClientCaching:
    async def test_cached_response_returned(self, mocker, tmp_path):
        """Verify cached response is returned without making HTTP request."""
        from chuk_mcp_her.core.cache import ResponseCache

        cache = ResponseCache(cache_dir=str(tmp_path))
        client = ArcGISClient(
            base_url=BASE_URL,
            cache=cache,
            cache_ttl=3600,
            timeout=5.0,
            max_retries=1,
            rate_limit_per_sec=0,
        )

        # First call populates cache
        response_data = {"type": "FeatureCollection", "features": []}
        mock_get = AsyncMock(return_value=_make_mock_response(response_data))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result1 = await client.query(layer_id=0, where="1=1")
        first_call_count = mock_get.call_count

        # Second call should use cache
        result2 = await client.query(layer_id=0, where="1=1")
        assert mock_get.call_count == first_call_count  # No additional HTTP call
        assert result2 == result1


class TestArcGISClientLazyCreation:
    async def test_recreates_closed_client(self):
        """Client should be recreated if the previous one was closed."""
        client = ArcGISClient(base_url=BASE_URL, rate_limit_per_sec=0)
        c1 = await client._get_client()
        await c1.aclose()
        c2 = await client._get_client()
        assert c1 is not c2
        await client.close()


class TestArcGISClientRateLimit:
    async def test_no_delay_when_zero_rate(self):
        """Rate limit of 0 means no delay."""
        client = ArcGISClient(base_url=BASE_URL, rate_limit_per_sec=0)
        await client._rate_limit()  # Should return immediately

    @patch("chuk_mcp_her.core.arcgis_client.asyncio.sleep", new_callable=AsyncMock)
    async def test_rate_limit_sleeps_when_too_fast(self, mock_sleep):
        """Rate limiter should sleep when requests are too close together."""
        client = ArcGISClient(base_url=BASE_URL, rate_limit_per_sec=1.0)
        client._last_request_time = time.monotonic()
        await client._rate_limit()
        mock_sleep.assert_called_once()


class TestArcGISClient429Retry:
    async def test_retries_on_429_then_succeeds(self, mocker):
        """429 response should trigger retry, succeed on second attempt."""
        mocker.patch("asyncio.sleep", new_callable=AsyncMock)
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=3, rate_limit_per_sec=0)
        resp_429 = _make_mock_response({}, 429)
        resp_ok = _make_mock_response({"features": [{"id": 1}]})
        mock_get = AsyncMock(side_effect=[resp_429, resp_ok])
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query(layer_id=0)
        assert result["features"] == [{"id": 1}]
        assert mock_get.call_count == 2


class TestArcGISClient400Error:
    async def test_non_5xx_error_raises_immediately(self, mocker):
        """Non-5xx HTTP errors (e.g. 400) should raise, not retry."""
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=3, rate_limit_per_sec=0)
        mock_get = AsyncMock(return_value=_make_mock_response({}, 400))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        with pytest.raises(httpx.HTTPStatusError):
            await client.query(layer_id=0)
        assert mock_get.call_count == 1  # No retries


class TestArcGISClient5xxRetrySuccess:
    async def test_5xx_retry_then_succeeds(self, mocker):
        """5xx response retried, succeeds on second attempt."""
        mocker.patch("asyncio.sleep", new_callable=AsyncMock)
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=3, rate_limit_per_sec=0)
        resp_500 = _make_mock_response({}, 500)
        resp_ok = _make_mock_response({"count": 42})
        mock_get = AsyncMock(side_effect=[resp_500, resp_ok])
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query(layer_id=0, return_count_only=True)
        assert result["count"] == 42
        assert mock_get.call_count == 2


class TestArcGISClientTimeoutRetry:
    async def test_timeout_retried_then_succeeds(self, mocker):
        """Timeout errors should be retried."""
        mocker.patch("asyncio.sleep", new_callable=AsyncMock)
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=3, rate_limit_per_sec=0)
        resp_ok = _make_mock_response({"features": []})
        mock_get = AsyncMock(side_effect=[httpx.TimeoutException("timeout"), resp_ok])
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query(layer_id=0)
        assert result == {"features": []}
        assert mock_get.call_count == 2

    async def test_connect_error_retried(self, mocker):
        """Connection errors should be retried."""
        mocker.patch("asyncio.sleep", new_callable=AsyncMock)
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=3, rate_limit_per_sec=0)
        resp_ok = _make_mock_response({"features": []})
        mock_get = AsyncMock(side_effect=[httpx.ConnectError("refused"), resp_ok])
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query(layer_id=0)
        assert result == {"features": []}


class TestArcGISClientExhaustedRetries:
    async def test_raises_after_all_retries(self, mocker):
        """Should raise RuntimeError after exhausting all retries."""
        mocker.patch("asyncio.sleep", new_callable=AsyncMock)
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=2, rate_limit_per_sec=0)
        mock_get = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        with pytest.raises(RuntimeError, match="failed after 2 attempts"):
            await client.query(layer_id=0)


class TestArcGISClientQueryAll:
    async def test_paginates_multiple_pages(self, mocker):
        """query_all should paginate until no more features."""
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=1, rate_limit_per_sec=0)
        page1 = _make_mock_response({"features": [{"id": i} for i in range(3)]})
        page2 = _make_mock_response({"features": [{"id": i} for i in range(3, 5)]})
        page3 = _make_mock_response({"features": []})
        mock_get = AsyncMock(side_effect=[page1, page2, page3])
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query_all(layer_id=0, max_records=10, page_size=3)
        assert len(result) == 5

    async def test_stops_at_max_records(self, mocker):
        """query_all should stop when max_records is reached."""
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=1, rate_limit_per_sec=0)
        page = _make_mock_response({"features": [{"id": i} for i in range(5)]})
        mock_get = AsyncMock(return_value=page)
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query_all(layer_id=0, max_records=5, page_size=5)
        assert len(result) == 5

    async def test_stops_on_short_page(self, mocker):
        """query_all should stop when a page has fewer features than page_size."""
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=1, rate_limit_per_sec=0)
        page = _make_mock_response({"features": [{"id": 1}, {"id": 2}]})
        mock_get = AsyncMock(return_value=page)
        mocker.patch("httpx.AsyncClient.get", mock_get)

        result = await client.query_all(layer_id=0, max_records=10, page_size=5)
        assert len(result) == 2
        assert mock_get.call_count == 1


class TestArcGISClientOrderByFields:
    async def test_order_by_fields_param(self, mocker):
        """order_by_fields should be passed to ArcGIS API."""
        client = ArcGISClient(base_url=BASE_URL, cache=None, max_retries=1, rate_limit_per_sec=0)
        mock_get = AsyncMock(return_value=_make_mock_response({"features": []}))
        mocker.patch("httpx.AsyncClient.get", mock_get)

        await client.query(layer_id=0, order_by_fields="Name ASC")
        call_args = mock_get.call_args
        params = call_args[1].get("params", {})
        assert params["orderByFields"] == "Name ASC"


class TestArcGISClientCloseMethod:
    async def test_close_open_client(self):
        """close() should close an open httpx client."""
        client = ArcGISClient(base_url=BASE_URL, rate_limit_per_sec=0)
        await client._get_client()
        assert client._client is not None
        await client.close()
        assert client._client is None

    async def test_close_when_no_client(self):
        """close() should be safe when no client exists."""
        client = ArcGISClient(base_url=BASE_URL, rate_limit_per_sec=0)
        await client.close()  # Should not raise
