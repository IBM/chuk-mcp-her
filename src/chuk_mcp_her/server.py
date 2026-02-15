"""
Synchronous entry point for chuk-mcp-her.

Launches the MCP server in either stdio or HTTP mode.
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

from .constants import EnvVar, ServerConfig

env_path = Path(__file__).parent.parent.parent / ".env"
if env_path.exists():
    load_dotenv(env_path)

logger = logging.getLogger(__name__)


def main() -> None:
    """Launch the HER MCP server."""
    from .async_server import mcp

    parser = argparse.ArgumentParser(
        prog=ServerConfig.NAME,
        description=ServerConfig.DESCRIPTION,
    )
    parser.add_argument(
        "mode",
        nargs="?",
        choices=["stdio", "http"],
        default=None,
        help="Transport mode (default: auto-detect)",
    )
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8010)
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )

    if args.mode == "stdio":
        mcp.run(stdio=True)
    elif args.mode == "http":
        mcp.run(host=args.host, port=args.port, stdio=False)
    else:
        if os.environ.get(EnvVar.MCP_STDIO) or (not sys.stdin.isatty()):
            mcp.run(stdio=True)
        else:
            mcp.run(host=args.host, port=args.port, stdio=False)


if __name__ == "__main__":
    main()
