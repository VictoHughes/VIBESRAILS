#!/bin/bash
# vibesrails - installation from source
# Usage: ./install.sh

set -e

echo "=== vibesrails installer (from source) ==="
echo ""

# Check dependencies
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

if ! command -v git &> /dev/null; then
    echo "ERROR: git is required"
    exit 1
fi

# Clone repository
INSTALL_DIR="${HOME}/.vibesrails"

if [ -d "$INSTALL_DIR" ]; then
    echo "Updating existing installation..."
    cd "$INSTALL_DIR"
    git pull
else
    echo "Cloning vibesrails..."
    git clone https://github.com/VictoHughes/VIBESRAILS.git "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# Install in development mode
echo ""
echo "Installing vibesrails..."
pip install -e .

# Verify installation
if command -v vibesrails &> /dev/null; then
    echo ""
    echo "Installation successful!"
    vibesrails --version
    echo ""
    echo "Installed at: $INSTALL_DIR"
    echo ""
    echo "Next steps:"
    echo "  cd your-project"
    echo "  vibesrails --setup"
else
    echo ""
    echo "ERROR: Installation failed"
    exit 1
fi
