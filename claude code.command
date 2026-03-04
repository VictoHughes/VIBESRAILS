#!/bin/bash
#
# VibesRails - Claude Code Launcher
# Usage: Double-click ou ./claude\ code.command
#

# Ensure PATH includes homebrew bins (.command from Finder has minimal PATH)
export PATH="/opt/homebrew/bin:/opt/homebrew/sbin:/usr/local/bin:$PATH"

cd "/Users/stan/Dev/vibesrails"

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "  VibesRails — Claude Code Session"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Pre-flight checks
echo "Pre-flight checks..."

# 1. Git branch
BRANCH=$(git branch --show-current 2>/dev/null)
if [ -n "$BRANCH" ]; then
    echo "  Branch: $BRANCH"
    if [ "$BRANCH" = "main" ]; then
        echo "  WARNING: Sur branche main!"
        echo "     Cree une branche: git checkout -b feature/xxx"
    fi
else
    echo "  Git: pas encore initialise"
fi

# 2. CLAUDE.md check
if [ -f "CLAUDE.md" ]; then
    echo "  CLAUDE.md: present"
else
    echo "  CLAUDE.md: absent (a creer)"
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

exec claude
