#!/bin/bash
#
# VibesRails - Claude Code Launcher
# Double-click to launch Claude Code with latest vibesrails
#

cd "$(dirname "$0")" || exit 1

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  VibesRails — Claude Code Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Activate venv if exists
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

# Update vibesrails (dev mode)
echo "Updating vibesrails..."
pip install -e . -q 2>/dev/null && echo "  vibesrails $(vibesrails --version 2>&1 | head -1)"

# Pre-flight checks
echo ""
echo "Pre-flight checks..."

# Git branch
BRANCH=$(git branch --show-current 2>/dev/null)
if [ "$BRANCH" = "main" ]; then
    echo "  WARNING: Sur branche main!"
fi

# Run tests
echo "  Running tests..."
python -m pytest tests/ -x --tb=no -q 2>/dev/null | tail -1

# vibesrails scan
echo "  Running vibesrails --all..."
vibesrails --all 2>/dev/null | grep -E "BLOCK|PASS|WARNING" | tail -3

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Launch Claude Code (continue previous session)
exec claude --continue
