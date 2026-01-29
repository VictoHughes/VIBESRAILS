#!/bin/bash
# VibesRails v2.0 - installation from source
# Usage: ./install.sh

set -e

echo "╔════════════════════════════════════════════════╗"
echo "║  VibesRails v2.0 Installer (source)            ║"
echo "║  YAML-driven security + code quality scanner   ║"
echo "╚════════════════════════════════════════════════╝"
echo ""

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3.10+ is required"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "ERROR: git is required"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Clone repository
INSTALL_DIR="${HOME}/.vibesrails"

if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
    git checkout v2.0 2>/dev/null || git checkout main
else
    echo "Cloning vibesrails..."
    git clone https://github.com/VictoHughes/VIBESRAILS.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
    git checkout v2.0 2>/dev/null || git checkout main
fi

# Install in development mode with all extras
echo ""
echo "Installing vibesrails v2.0 from source..."
pip install -e ".[all]"

# Verify installation
if command -v vibesrails &> /dev/null; then
    echo ""
    echo "Installation successful!"
    vibesrails --version
    echo ""
    echo "Installed at: $INSTALL_DIR"
    echo ""
    echo "v2.0 Features:"
    echo "  - 15 security & quality guards"
    echo "  - Senior Mode (AI coding safety)"
    echo "  - Architecture mapping"
    echo "  - Performance, complexity & dependency audits"
    echo "  - Type safety & API design guards"
    echo "  - Community pattern packs"
    echo ""
    echo "Next steps:"
    echo "  cd your-project"
    echo "  vibesrails --setup"
else
    echo ""
    echo "ERROR: Installation failed"
    exit 1
fi
