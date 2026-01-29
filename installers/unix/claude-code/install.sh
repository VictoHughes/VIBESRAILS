#!/bin/bash
# VibesRails v2.0 - Claude Code integration installer
# Usage: ./install.sh [project-path]
#
# Installs vibesrails v2.0 AND sets up Claude Code integration:
#   - vibesrails.yaml   (security patterns)
#   - CLAUDE.md         (Claude Code instructions)
#   - .claude/hooks.json (session automation)
#   - .git/hooks/pre-commit (security scanning)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEMPLATES_DIR="$(cd "$SCRIPT_DIR/../../templates/claude-code" 2>/dev/null && pwd || echo "")"

echo "╔════════════════════════════════════════════════╗"
echo "║  VibesRails v2.0 + Claude Code Installer       ║"
echo "║  15 guards + Senior Mode + AI integration      ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

PROJECT_PATH="${1:-.}"

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3.10+ is required"
    exit 1
fi

# Step 1: Install vibesrails v2 if not present
if ! command -v vibesrails &> /dev/null; then
    echo "[1/4] Installing vibesrails v2.0..."
    pip install "vibesrails[all]>=2.0.0"
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

if [ -n "$TEMPLATES_DIR" ] && [ -d "$TEMPLATES_DIR" ]; then
    # vibesrails.yaml
    if [ ! -f "vibesrails.yaml" ]; then
        cp "$TEMPLATES_DIR/vibesrails.yaml" ./vibesrails.yaml
        echo "      + vibesrails.yaml (security patterns)"
    else
        echo "      ~ vibesrails.yaml (already exists, skipped)"
    fi

    # CLAUDE.md
    if [ ! -f "CLAUDE.md" ]; then
        cp "$TEMPLATES_DIR/CLAUDE.md" ./CLAUDE.md
        echo "      + CLAUDE.md (Claude Code instructions)"
    else
        echo "      ~ CLAUDE.md (already exists, skipped)"
    fi

    # .claude/hooks.json
    mkdir -p .claude
    if [ ! -f ".claude/hooks.json" ]; then
        cp "$TEMPLATES_DIR/.claude/hooks.json" ./.claude/hooks.json
        echo "      + .claude/hooks.json (session automation)"
    else
        echo "      ~ .claude/hooks.json (already exists, skipped)"
    fi
else
    echo "      Templates directory not found, running vibesrails --setup instead..."
    vibesrails --setup --force 2>/dev/null || vibesrails --setup 2>/dev/null || true
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
echo "  v2.0 Features available:"
echo "    - 15 security & quality guards"
echo "    - Senior Mode with architecture mapping"
echo "    - AI coding safety (hallucination, bypass, lazy code detection)"
echo "    - Performance, complexity & dependency audits"
echo "    - Community pattern packs"
echo ""
echo "  Claude Code will now:"
echo "    - Scan code on every commit"
echo "    - Run Senior Mode during AI sessions"
echo "    - Show active plan on session start"
echo "    - Auto-save state before compaction"
echo ""
echo "  CLI Commands:"
echo "    vibesrails --all          Full project scan"
echo "    vibesrails --senior       Senior Mode analysis"
echo "    vibesrails --audit        Dependency audit"
echo "    vibesrails --upgrade      Upgrade advisor"
echo "    vibesrails --watch        Live scanning"
echo ""
