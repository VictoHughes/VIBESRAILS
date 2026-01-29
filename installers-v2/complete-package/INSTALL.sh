#!/bin/bash
# VibesRails v2.0 - Complete Installation Script
# Install VibesRails v2.0 + setup your project with templates

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================================${NC}"
echo -e "${BLUE}  VibesRails v2.0 Complete Installer${NC}"
echo -e "${BLUE}  15 guards + Senior Mode + AI integration${NC}"
echo -e "${BLUE}================================================${NC}"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}ERROR: Python 3.10+ required (you have $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Python $PYTHON_VERSION${NC}"

# Get script directory (where the package is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEEL_FILE="$SCRIPT_DIR/vibesrails-2.0.0-py3-none-any.whl"
TEMPLATES_DIR="$SCRIPT_DIR/claude-code"

# Check wheel exists
if [ ! -f "$WHEEL_FILE" ]; then
    echo -e "${RED}ERROR: vibesrails wheel not found at: $WHEEL_FILE${NC}"
    exit 1
fi

# Get target project directory
if [ -z "$1" ]; then
    echo ""
    echo "Usage: $0 /path/to/your/project"
    echo ""
    echo "Or run from your project directory:"
    echo "  cd your-project"
    echo "  bash /path/to/INSTALL.sh ."
    echo ""
    exit 1
fi

PROJECT_DIR="$(cd "$1" && pwd)"

if [ ! -d "$PROJECT_DIR" ]; then
    echo -e "${RED}ERROR: Directory not found: $1${NC}"
    exit 1
fi

echo -e "${GREEN}[OK] Target project: $PROJECT_DIR${NC}"
echo ""

# Step 1: Install VibesRails from wheel
echo -e "${BLUE}[1/3] Installing VibesRails v2.0...${NC}"
python3 -m pip install "$WHEEL_FILE[all]" --force-reinstall
# Install core dependencies
python3 -m pip install pyyaml semgrep

# Verify installation
if ! command -v vibesrails &> /dev/null; then
    echo -e "${RED}ERROR: vibesrails command not found after installation${NC}"
    echo "Try: python3 -m vibesrails --version"
    exit 1
fi

INSTALLED_VERSION=$(vibesrails --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
echo -e "${GREEN}[OK] VibesRails $INSTALLED_VERSION installed${NC}"
echo ""

# Step 2: Copy templates to project
echo -e "${BLUE}[2/3] Copying configuration files...${NC}"

# Check if git repo
if [ ! -d "$PROJECT_DIR/.git" ]; then
    echo -e "${YELLOW}WARNING: Not a git repository. Initializing...${NC}"
    cd "$PROJECT_DIR"
    git init
fi

# Copy templates
if [ -d "$TEMPLATES_DIR" ]; then
    cp "$TEMPLATES_DIR/vibesrails.yaml" "$PROJECT_DIR/" 2>/dev/null && \
        echo -e "${GREEN}  [OK] vibesrails.yaml${NC}" || true

    cp "$TEMPLATES_DIR/CLAUDE.md" "$PROJECT_DIR/" 2>/dev/null && \
        echo -e "${GREEN}  [OK] CLAUDE.md${NC}" || true

    mkdir -p "$PROJECT_DIR/.claude"
    cp "$TEMPLATES_DIR/.claude/hooks.json" "$PROJECT_DIR/.claude/" 2>/dev/null && \
        echo -e "${GREEN}  [OK] .claude/hooks.json${NC}" || true
else
    echo -e "${YELLOW}Templates not found, running vibesrails --setup...${NC}"
    cd "$PROJECT_DIR"
    vibesrails --setup --force 2>/dev/null || vibesrails --setup 2>/dev/null || true
fi

echo ""

# Step 3: Install git hook
echo -e "${BLUE}[3/3] Installing git pre-commit hook...${NC}"
cd "$PROJECT_DIR"
vibesrails --hook 2>/dev/null || true

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}  Installation Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Verify files
echo "Files installed:"
for f in vibesrails.yaml CLAUDE.md .claude/hooks.json .git/hooks/pre-commit; do
    [ -f "$PROJECT_DIR/$f" ] && echo "  - $f"
done
echo ""

echo "v2.0 Features:"
echo "  - 15 security & quality guards"
echo "  - Senior Mode with architecture mapping"
echo "  - AI coding safety (hallucination, bypass, lazy code)"
echo "  - Performance, complexity & dependency audits"
echo "  - Type safety & API design guards"
echo "  - Community pattern packs"
echo ""

echo "Test the installation:"
echo -e "  ${BLUE}cd $PROJECT_DIR${NC}"
echo -e "  ${BLUE}vibesrails --all${NC}"
echo ""

echo "CLI Commands:"
echo "  vibesrails --all          Scan entire project"
echo "  vibesrails --senior       Run Senior Mode analysis"
echo "  vibesrails --show         Show configured patterns"
echo "  vibesrails --watch        Live scanning mode"
echo "  vibesrails --learn        AI pattern discovery"
echo "  vibesrails --fix          Auto-fix issues"
echo "  vibesrails --audit        Dependency audit"
echo "  vibesrails --upgrade      Upgrade advisor"
echo "  vibesrails --stats        View scan statistics"
echo ""

echo -e "${GREEN}Happy safe coding!${NC}"
