#!/usr/bin/env bash
# VibesRails - Mac/Linux Installer (self-contained)
# Usage: bash install.sh /path/to/project
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TARGET="${1:-.}"
TARGET="$(cd "$TARGET" && pwd)"

echo "=== VibesRails Installer ==="
echo "Target: $TARGET"

# 1. Install vibesrails via pip
echo ""
echo "[1/4] Installing vibesrails..."
pip install vibesrails || pip3 install vibesrails

# 2. Copy config files
echo ""
echo "[2/4] Copying configuration files..."

cp "$SCRIPT_DIR/vibesrails.yaml" "$TARGET/vibesrails.yaml"
echo "  -> vibesrails.yaml"

cp "$SCRIPT_DIR/CLAUDE.md" "$TARGET/CLAUDE.md"
echo "  -> CLAUDE.md"

mkdir -p "$TARGET/.claude"
cp "$SCRIPT_DIR/.claude/hooks.json" "$TARGET/.claude/hooks.json"
echo "  -> .claude/hooks.json"

# 3. Install git pre-commit hook
echo ""
echo "[3/4] Installing git pre-commit hook..."
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
    echo "  (no .git directory found, skipping hook)"
fi

# 4. Install AI self-protection hook
echo ""
echo "[4/4] Installing AI self-protection hook..."
HOOKS_DIR="$HOME/.claude/hooks"
mkdir -p "$HOOKS_DIR"
cp "$SCRIPT_DIR/ptuh.py" "$HOOKS_DIR/ptuh.py"
echo "  -> ~/.claude/hooks/ptuh.py"

SETTINGS_FILE="$HOME/.claude/settings.json"
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
else
    echo "  (python3 not found, please add hook to ~/.claude/settings.json manually)"
fi

echo ""
echo "=== Done! ==="
echo "Commands:"
echo "  vibesrails --all    # Scan project"
echo "  vibesrails --setup  # Reconfigure (interactive)"
echo "  vibesrails --show   # Show patterns"
