#!/bin/bash
# vibesrails - Claude Code integration installer
# Usage: ./install.sh [project-path]
#
# Installs vibesrails AND sets up Claude Code integration:
#   - vibesrails.yaml  (security patterns)
#   - CLAUDE.md        (Claude Code instructions)
#   - .claude/hooks.json (session automation)
#   - .git/hooks/pre-commit (security scanning)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../../templates/claude-code" && pwd)"

echo "╔════════════════════════════════════════════════╗"
echo "║  VibesRails + Claude Code Installer            ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

PROJECT_PATH="${1:-.}"

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

# Step 1: Install vibesrails if not present
if ! command -v vibesrails &> /dev/null; then
    echo "[1/4] Installing vibesrails..."
    pip install vibesrails
else
    echo "[1/4] vibesrails already installed"
fi

# Verify
if ! command -v vibesrails &> /dev/null; then
    echo "ERROR: vibesrails installation failed"
    exit 1
fi
echo "      $(vibesrails --version 2>&1 | head -1)"
echo ""

# Step 2: Setup project directory
cd "$PROJECT_PATH"
echo "[2/4] Project: $(pwd)"

if [ ! -d ".git" ]; then
    echo "      Initializing git repository..."
    git init
fi
echo ""

# Step 3: Copy Claude Code templates
echo "[3/4] Installing Claude Code integration..."

# vibesrails.yaml - only if not already present
if [ ! -f "vibesrails.yaml" ]; then
    cp "$TEMPLATES_DIR/vibesrails.yaml" ./vibesrails.yaml
    echo "      + vibesrails.yaml (security patterns)"
else
    echo "      ~ vibesrails.yaml (already exists, skipped)"
fi

# CLAUDE.md - only if not already present
if [ ! -f "CLAUDE.md" ]; then
    cp "$TEMPLATES_DIR/CLAUDE.md" ./CLAUDE.md
    echo "      + CLAUDE.md (Claude Code instructions)"
else
    echo "      ~ CLAUDE.md (already exists, skipped)"
fi

# .claude/hooks.json - only if not already present
mkdir -p .claude
if [ ! -f ".claude/hooks.json" ]; then
    cp "$TEMPLATES_DIR/.claude/hooks.json" ./.claude/hooks.json
    echo "      + .claude/hooks.json (session automation)"
else
    echo "      ~ .claude/hooks.json (already exists, skipped)"
fi
echo ""

# Step 4: Install git pre-commit hook
echo "[4/4] Installing git pre-commit hook..."
vibesrails --hook --force 2>/dev/null || vibesrails --hook 2>/dev/null || echo "      (skipped - run 'vibesrails --hook' manually)"
echo ""

# Summary
echo "════════════════════════════════════════════════"
echo "  Installation complete!"
echo "════════════════════════════════════════════════"
echo ""
echo "  Files installed:"
for f in vibesrails.yaml CLAUDE.md .claude/hooks.json .git/hooks/pre-commit; do
    [ -f "$f" ] && echo "    $f"
done
echo ""
echo "  Claude Code will now:"
echo "    - Scan code on every commit"
echo "    - Show active plan on session start"
echo "    - Auto-save state before compaction"
echo "    - Remind about scanning on first edit"
echo ""
echo "  Next: vibesrails --all"
