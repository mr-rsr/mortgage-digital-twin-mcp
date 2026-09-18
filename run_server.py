#!/usr/bin/env python
"""
Launcher for Mortgage Multi-Agent FastMCP Server
Defaults to SSE transport on 0.0.0.0:8000
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.mcp_server.server import mcp
from src.config import settings

if __name__ == "__main__":
    host = settings.mcp_server_host
    port = settings.mcp_server_port
    transport = "sse"

    if len(sys.argv) > 1 and sys.argv[1].startswith("--"):
        # Let server.py argparse handle options
        from src.mcp_server.server import args
    else:
        print(f"Starting Mortgage Multi-Agent FastMCP Server on {host}:{port} via SSE transport...")
        print(f"Endpoint: http://{host}:{port}/sse")
        mcp.run(transport="sse", host=host, port=port)
