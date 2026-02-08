#!/usr/bin/env bash
# VibesRails - Drag & Drop Installer
# Usage: Drop this folder into your project, then run:
#   bash install.sh
# OR just open the folder in Claude Code — it will auto-detect.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="$(pwd)"

# If run from inside the installer folder, go up one level
if [ -f "$TARGET/install.sh" ] && [ -f "$TARGET/vibesrails.yaml" ]; then
    TARGET="$(dirname "$TARGET")"
fi

echo "=== VibesRails Installer ==="
echo "Target: $TARGET"

# 1. Install vibesrails from bundled wheel (no internet needed)
echo ""
echo "[1/5] Installing vibesrails from bundled wheel..."
WHL=$(ls "$SCRIPT_DIR"/vibesrails-*.whl 2>/dev/null | head -1)
if [ -z "$WHL" ]; then
    echo "ERROR: No .whl file found. Trying pip install..."
    pip3 install vibesrails 2>/dev/null || pip install vibesrails
else
    pip3 install "$WHL" 2>/dev/null || pip install "$WHL"
fi
echo "  -> vibesrails installed"

# 2. Copy config files to project
echo ""
echo "[2/5] Copying configuration files..."
cp "$SCRIPT_DIR/vibesrails.yaml" "$TARGET/vibesrails.yaml"
echo "  -> vibesrails.yaml"

cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
echo "  -> CLAUDE.md"

mkdir -p "$TARGET/.claude"
cp "$SCRIPT_DIR/.claude/hooks.json" "$TARGET/.claude/hooks.json"
echo "  -> .claude/hooks.json"

# 3. Install git pre-commit hook
echo ""
echo "[3/5] Installing git pre-commit hook..."
if [ -d "$TARGET/.git" ]; then
    HOOK="$TARGET/.git/hooks/pre-commit"
    mkdir -p "$TARGET/.git/hooks"
    cat > "$HOOK" << 'HOOKEOF'
#!/usr/bin/env bash
# vibesrails pre-commit hook
if command -v vibesrails &>/dev/null; then
    vibesrails
elif [ -f ".venv/bin/vibesrails" ]; then
    .venv/bin/vibesrails
elif [ -f "venv/bin/vibesrails" ]; then
    venv/bin/vibesrails
else
    python3 -m vibesrails
fi
HOOKEOF
    chmod +x "$HOOK"
    echo "  -> .git/hooks/pre-commit"
else
    echo "  (no .git directory, skipping)"
fi

# 4. Install AI self-protection hook (global)
echo ""
echo "[4/5] Installing AI self-protection hook..."
HOOKS_DIR="$HOME/.claude/hooks"
mkdir -p "$HOOKS_DIR"
cp "$SCRIPT_DIR/ptuh.py" "$HOOKS_DIR/ptuh.py"
echo "  -> ~/.claude/hooks/ptuh.py"

# Register in ~/.claude/settings.json (new format)
if command -v python3 &>/dev/null; then
    python3 -c "
import json, os
path = os.path.expanduser('~/.claude/settings.json')
settings = {}
if os.path.exists(path):
    with open(path) as f:
        settings = json.load(f)
hook_cmd = 'python3 ~/.claude/hooks/ptuh.py'
matcher_entry = {'matcher': 'Edit|Write|Bash', 'hooks': [{'type': 'command', 'command': hook_cmd}]}
hooks = settings.setdefault('hooks', {})
ptu = hooks.setdefault('PreToolUse', [])
exists = any(any(h.get('command', '') == hook_cmd for h in m.get('hooks', [])) for m in ptu)
if not exists:
    ptu.append(matcher_entry)
with open(path, 'w') as f:
    json.dump(settings, f, indent=2)
"
    echo "  -> ~/.claude/settings.json (hook registered)"
fi

# 5. Clean up installer folder from project
echo ""
echo "[5/5] Cleanup..."
echo "  You can safely delete this installer folder now."

echo ""
echo "=== Done! ==="
echo ""
echo "Open your project in Claude Code. VibesRails is active:"
echo "  - Secrets & injections blocked BEFORE write"
echo "  - Full scan on every commit"
echo "  - AI self-protection enabled"
echo ""
echo "Commands:"
echo "  vibesrails --all    # Scan project"
echo "  vibesrails --setup  # Reconfigure"
echo "  vibesrails --show   # Show patterns"
