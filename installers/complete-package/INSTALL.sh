#!/bin/bash
# VibesRails - Complete Installation Script
# Install VibesRails + setup your project with templates

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}VibesRails Complete Installer${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check Python version
PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d. -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d. -f2)

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo -e "${RED}ERROR: Python 3.10+ required (you have $PYTHON_VERSION)${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION${NC}"

# Get script directory (where the package is)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEEL_FILE="$SCRIPT_DIR/vibesrails-1.3.0-py3-none-any.whl"
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

echo -e "${GREEN}✓ Target project: $PROJECT_DIR${NC}"
echo ""

# Step 1: Install VibesRails from wheel
echo -e "${BLUE}[1/3] Installing VibesRails...${NC}"
python3 -m pip install "$WHEEL_FILE" --force-reinstall --no-deps
python3 -m pip install pyyaml semgrep  # Install dependencies

# Verify installation
if ! command -v vibesrails &> /dev/null; then
    echo -e "${RED}ERROR: vibesrails command not found after installation${NC}"
    echo "Try: python3 -m vibesrails --version"
    exit 1
fi

INSTALLED_VERSION=$(vibesrails --version 2>&1 | grep -o '[0-9]\+\.[0-9]\+\.[0-9]\+' || echo "unknown")
echo -e "${GREEN}✓ VibesRails $INSTALLED_VERSION installed${NC}"
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
cp "$TEMPLATES_DIR/vibesrails.yaml" "$PROJECT_DIR/"
echo -e "${GREEN}  ✓ vibesrails.yaml${NC}"

cp "$TEMPLATES_DIR/CLAUDE.md" "$PROJECT_DIR/"
echo -e "${GREEN}  ✓ CLAUDE.md${NC}"

mkdir -p "$PROJECT_DIR/.claude"
cp "$TEMPLATES_DIR/.claude/hooks.json" "$PROJECT_DIR/.claude/"
echo -e "${GREEN}  ✓ .claude/hooks.json${NC}"

echo ""

# Step 3: Install git hook
echo -e "${BLUE}[3/3] Installing git pre-commit hook...${NC}"
cd "$PROJECT_DIR"
vibesrails --hook

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Installation Complete! 🚀${NC}"
echo -e "${GREEN}================================${NC}"
echo ""

# Verify files
echo "Files installed:"
echo "  • vibesrails.yaml - Security patterns"
echo "  • CLAUDE.md - Claude Code instructions"
echo "  • .claude/hooks.json - Automation hooks"
echo "  • .git/hooks/pre-commit - Git hook"
echo ""

echo "Test the installation:"
echo -e "  ${BLUE}cd $PROJECT_DIR${NC}"
echo -e "  ${BLUE}vibesrails --all${NC}"
echo ""

echo "Try these commands:"
echo "  vibesrails --show       # Show configured patterns"
echo "  vibesrails --watch      # Live scanning mode"
echo "  vibesrails --learn      # AI pattern discovery"
echo "  vibesrails --stats      # View scan statistics"
echo ""

echo -e "${GREEN}Happy safe coding! 🛤️${NC}"
