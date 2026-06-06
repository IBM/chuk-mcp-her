"""Tests for chuk_mcp_her.server and async_server module imports."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch


class TestServerMain:
    def test_main_is_callable(self):
        """Verify server.main() exists and is callable."""
        from chuk_mcp_her.server import main

        assert callable(main)

    def test_server_module_imports(self):
        """Verify the server module can be imported without error."""
        import chuk_mcp_her.server as server_mod

        assert hasattr(server_mod, "main")


class TestAsyncServer:
    def test_async_server_creates_mcp(self):
        """Verify async_server.py creates an mcp instance."""
        from chuk_mcp_her.async_server import mcp

        assert mcp is not None
        assert hasattr(mcp, "tool")

    def test_async_server_creates_registry(self):
        """Verify async_server.py creates a registry instance."""
        from chuk_mcp_her.async_server import registry

        assert registry is not None
        assert hasattr(registry, "list_sources")
        assert hasattr(registry, "search_monuments")
        assert hasattr(registry, "get_adapter")

    def test_async_server_registry_has_sources(self):
        """Verify the registry has all 6 sources registered."""
        from chuk_mcp_her.async_server import registry

        sources = registry.list_sources()
        assert len(sources) == 6
        ids = [s["id"] for s in sources]
        assert "nhle" in ids
        assert "aim" in ids
        assert "conservation_area" in ids
        assert "heritage_at_risk" in ids
        assert "heritage_gateway" in ids


class TestServerMainFunction:
    """Test the main() entry point with different transport modes."""

    @patch("chuk_mcp_her.async_server.mcp")
    def test_stdio_mode(self, mock_mcp):
        with patch("sys.argv", ["chuk-mcp-her", "stdio"]):
            from chuk_mcp_her.server import main

            main()
        mock_mcp.run.assert_called_once_with(stdio=True)

    @patch("chuk_mcp_her.async_server.mcp")
    def test_http_mode(self, mock_mcp):
        with patch("sys.argv", ["chuk-mcp-her", "http", "--port", "9999"]):
            from chuk_mcp_her.server import main

            main()
        mock_mcp.run.assert_called_once_with(host="localhost", port=9999, stdio=False)

    @patch("chuk_mcp_her.async_server.mcp")
    def test_http_custom_host(self, mock_mcp):
        with patch("sys.argv", ["chuk-mcp-her", "http", "--host", "0.0.0.0"]):
            from chuk_mcp_her.server import main

            main()
        mock_mcp.run.assert_called_once_with(host="0.0.0.0", port=8010, stdio=False)

    @patch("chuk_mcp_her.async_server.mcp")
    def test_auto_detect_env_var(self, mock_mcp):
        with patch("sys.argv", ["chuk-mcp-her"]):
            with patch.dict(os.environ, {"MCP_STDIO": "1"}):
                from chuk_mcp_her.server import main

                main()
        mock_mcp.run.assert_called_once_with(stdio=True)

    @patch("chuk_mcp_her.async_server.mcp")
    def test_auto_detect_non_tty(self, mock_mcp):
        env = {k: v for k, v in os.environ.items() if k != "MCP_STDIO"}
        with patch("sys.argv", ["chuk-mcp-her"]):
            with patch.dict(os.environ, env, clear=True):
                with patch.object(sys.stdin, "isatty", return_value=False):
                    from chuk_mcp_her.server import main

                    main()
        mock_mcp.run.assert_called_once_with(stdio=True)

    @patch("chuk_mcp_her.async_server.mcp")
    def test_auto_detect_tty_http(self, mock_mcp):
        env = {k: v for k, v in os.environ.items() if k != "MCP_STDIO"}
        with patch("sys.argv", ["chuk-mcp-her"]):
            with patch.dict(os.environ, env, clear=True):
                with patch.object(sys.stdin, "isatty", return_value=True):
                    from chuk_mcp_her.server import main

                    main()
        mock_mcp.run.assert_called_once_with(host="localhost", port=8010, stdio=False)


class TestPackageImport:
    def test_top_level_import(self):
        """Verify the top-level package can be imported."""
        import chuk_mcp_her

        assert chuk_mcp_her is not None

    def test_constants_import(self):
        """Verify constants can be imported from the package."""
        from chuk_mcp_her.constants import ServerConfig, SourceId

        assert ServerConfig.NAME == "chuk-mcp-her"
        assert SourceId.NHLE == "nhle"

    def test_models_import(self):
        """Verify models can be imported from the package."""
        from chuk_mcp_her.models import (
            ErrorResponse,
            format_response,
        )

        assert ErrorResponse is not None
        assert callable(format_response)

    def test_core_imports(self):
        """Verify core modules can be imported."""
        from chuk_mcp_her.core.arcgis_client import ArcGISClient
        from chuk_mcp_her.core.cache import ResponseCache
        from chuk_mcp_her.core.coordinates import bng_to_wgs84, wgs84_to_bng
        from chuk_mcp_her.core.source_registry import SourceRegistry

        assert ArcGISClient is not None
        assert ResponseCache is not None
        assert callable(bng_to_wgs84)
        assert callable(wgs84_to_bng)
        assert SourceRegistry is not None

    def test_adapter_imports(self):
        """Verify adapters can be imported."""
        from chuk_mcp_her.core.adapters.aim import AIMAdapter
        from chuk_mcp_her.core.adapters.heritage_gateway import HeritageGatewayAdapter
        from chuk_mcp_her.core.adapters.nhle import NHLEAdapter

        assert NHLEAdapter is not None
        assert AIMAdapter is not None
        assert HeritageGatewayAdapter is not None

    def test_tools_imports(self):
        """Verify tool registration functions can be imported."""
        from chuk_mcp_her.tools import (
            register_aerial_tools,
            register_crossref_tools,
            register_discovery_tools,
            register_export_tools,
            register_gateway_tools,
            register_nhle_tools,
        )

        assert callable(register_discovery_tools)
        assert callable(register_nhle_tools)
        assert callable(register_aerial_tools)
        assert callable(register_gateway_tools)
        assert callable(register_crossref_tools)
        assert callable(register_export_tools)
