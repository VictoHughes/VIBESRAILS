#!/bin/bash
# vibesrails - pip installation
# Usage: curl -sSL https://raw.githubusercontent.com/.../install.sh | bash

set -e

echo "=== VibesRails installer ==="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python 3 is required"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
echo "Python version: $PYTHON_VERSION"

# Install vibesrails
echo ""
echo "Installing vibesrails..."
pip install vibesrails

# Verify installation
if command -v vibesrails &> /dev/null; then
    echo ""
    echo "Installation successful!"
    vibesrails --version
    echo ""
    echo "Next steps:"
    echo "  cd your-project"
    echo "  vibesrails --setup"
else
    echo ""
    echo "ERROR: Installation failed"
    exit 1
fi
