#!/bin/bash
# vibesrails - Claude Code integration installer
# Usage: ./install.sh [project-path]
#
# Installs vibesrails AND sets up a project for Claude Code

set -e

echo "=== VibesRails + Claude Code installer ==="
echo ""

PROJECT_PATH="${1:-.}"

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

# Step 1: Install vibesrails if not present
if ! command -v vibesrails &> /dev/null; then
    echo "Installing vibesrails..."
    pip install vibesrails
    echo ""
fi

# Verify installation
if ! command -v vibesrails &> /dev/null; then
    echo "ERROR: vibesrails installation failed"
    exit 1
fi

echo "vibesrails $(vibesrails --version 2>&1 | head -1)"
echo ""

# Step 2: Setup project
cd "$PROJECT_PATH"
echo "Setting up project: $(pwd)"
echo ""

# Check if git repo
if [ ! -d ".git" ]; then
    echo "WARNING: Not a git repository. Initializing..."
    git init
fi

# Run smart setup (non-interactive for script)
echo "Running vibesrails --setup..."
vibesrails --setup --force

echo ""
echo "=== Installation complete ==="
echo ""
echo "Files created:"
ls -la vibesrails.yaml CLAUDE.md .claude/hooks.json .git/hooks/pre-commit 2>/dev/null | awk '{print "  " $NF}'
echo ""
echo "Claude Code will now:"
echo "  - Scan code on every commit"
echo "  - Show active plan on session start"
echo "  - Auto-save state before compaction"
echo ""
echo "Try: vibesrails --all"
