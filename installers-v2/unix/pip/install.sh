#!/bin/bash
# VibesRails v2.0 - pip installation
# Usage: curl -sSL https://raw.githubusercontent.com/.../install.sh | bash

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  VibesRails v2.0 Installer (pip)               ║"
echo "║  YAML-driven security + code quality scanner   ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3.10+ is required"
    echo "Download from: https://python.org"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
PYTHON_MAJOR=$(python3 -c 'import sys; print(sys.version_info.major)')
PYTHON_MINOR=$(python3 -c 'import sys; print(sys.version_info.minor)')

if [ "$PYTHON_MAJOR" -lt 3 ] || ([ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -lt 10 ]); then
    echo "ERROR: Python 3.10+ required (you have $PYTHON_VERSION)"
    exit 1
fi

echo "Python version: $PYTHON_VERSION"

# Install vibesrails v2 with all optional dependencies
echo ""
echo "Installing vibesrails v2.0 with all extras..."
pip install "vibesrails[all]>=2.0.0"

# Verify installation
if command -v vibesrails &> /dev/null; then
    echo ""
    echo "Installation successful!"
    vibesrails --version
    echo ""
    echo "v2.0 Features:"
    echo "  - 15 security & quality guards"
    echo "  - Senior Mode (AI coding safety)"
    echo "  - Architecture mapping"
    echo "  - Performance, complexity & dependency audits"
    echo "  - Type safety & API design guards"
    echo "  - Community pattern packs"
    echo ""
    echo "CLI Commands:"
    echo "  vibesrails --all          Scan entire project"
    echo "  vibesrails --setup        Setup new project"
    echo "  vibesrails --senior       Run Senior Mode analysis"
    echo "  vibesrails --show         Show configured patterns"
    echo "  vibesrails --watch        Live scanning mode"
    echo "  vibesrails --learn        AI pattern discovery"
    echo "  vibesrails --fix          Auto-fix issues"
    echo "  vibesrails --stats        View scan statistics"
    echo "  vibesrails --audit        Dependency audit"
    echo "  vibesrails --upgrade      Upgrade advisor"
    echo ""
    echo "Next steps:"
    echo "  cd your-project"
    echo "  vibesrails --setup"
else
    echo ""
    echo "ERROR: Installation failed"
    exit 1
fi
