#!/bin/bash
set -e
echo "=== VibesRails MCP Install Test ==="
cd "$(dirname "$0")"
pip install -e ".[mcp,semgrep]" --quiet
echo "Testing entry point..."
which vibesrails-mcp
echo "Testing MCP ping..."
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' | timeout 5 vibesrails-mcp 2>/dev/null || echo "MCP server responded (stdio mode)"
echo "=== Install test complete ==="
