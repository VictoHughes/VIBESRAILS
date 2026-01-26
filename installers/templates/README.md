# VibesRails Templates - Ready-to-Use Configuration Files

**Drag & drop templates** for instant VibesRails setup. No scripts, no installation commands - just copy files.

## Available Templates

### 📂 claude-code/

**For Claude Code users** - Complete integration with automation hooks.

**Includes:**
- `vibesrails.yaml` - Security patterns configuration
- `CLAUDE.md` - Claude Code instructions and guidelines
- `.claude/hooks.json` - Automation hooks (SessionStart, PreCompact, PostToolUse)
- `README.md` - Complete installation and usage instructions

**Perfect for:**
- AI-assisted development with Claude Code
- Teams using Claude for coding
- Projects needing automated security checks

## How to Share with Your Team

### Option 1: Send the Folder (Recommended)

1. **Zip the template:**
   ```bash
   cd installers/templates
   zip -r vibesrails-claude-code.zip claude-code/
   ```

2. **Send to teammate:**
   - Email: `vibesrails-claude-code.zip`
   - Slack/Discord: Upload zip file
   - GitHub: Upload as release asset

3. **Teammate extracts and copies files:**
   ```bash
   unzip vibesrails-claude-code.zip
   cd claude-code/
   # Follow README.md instructions
   ```

### Option 2: Direct Git Clone

**Teammate clones VibesRails repo and copies templates:**

```bash
# Clone repo (one-time)
git clone https://github.com/VictoHughes/VIBESRAILS.git
cd VIBESRAILS/installers/templates/claude-code/

# Copy to their project
cp vibesrails.yaml /path/to/their/project/
cp CLAUDE.md /path/to/their/project/
mkdir -p /path/to/their/project/.claude
cp .claude/hooks.json /path/to/their/project/.claude/
```

### Option 3: Share via GitHub Gist

**Create public Gist with template files:**

```bash
# Create Gist with all files
gh gist create \
  claude-code/vibesrails.yaml \
  claude-code/CLAUDE.md \
  claude-code/.claude/hooks.json \
  claude-code/README.md \
  --public \
  --desc "VibesRails templates for Claude Code"
```

**Teammate downloads:**
```bash
gh gist clone <gist-id>
```

## What Your Teammate Gets

### ✅ Security Scanning
- Pre-commit hooks (blocks unsafe code)
- Pattern-based detection (secrets, injections)
- Configurable warnings (code quality)

### ✅ Claude Code Integration
- Session start notifications (active plans)
- Auto-save before compaction
- Commit detection and reminders

### ✅ Zero Configuration
- Works out of the box
- Sensible defaults
- Easy to customize

## Template Contents

### vibesrails.yaml (4KB)
Security patterns configuration:
- **Blocking**: Hardcoded secrets, SQL injection, command injection
- **Warnings**: Star imports, print statements, bare excepts
- **Exceptions**: Test files, config files

### CLAUDE.md (3.5KB)
Instructions for Claude Code:
- How VibesRails works
- Available commands
- Customization guide
- Troubleshooting

### .claude/hooks.json (2KB)
Automation hooks:
- **SessionStart**: Show active plan + current task
- **PreCompact**: Auto-save state
- **PostToolUse**: Detect commits, remind about scanning

### README.md (5.3KB)
Complete guide:
- Installation steps (3 easy steps)
- Verification tests
- Quick commands reference
- Customization examples
- Troubleshooting

## Prerequisites

Your teammate needs:
- **Python 3.10+**
- **pip** (for `pip install vibesrails`)
- **git** (for pre-commit hooks)
- **Claude Code** (for full integration)

## Quick Start for Your Teammate

**3 simple steps:**

```bash
# 1. Install VibesRails
pip install vibesrails

# 2. Copy template files to project
cp -r claude-code/* /path/to/project/

# 3. Install git hook
cd /path/to/project
vibesrails --hook
```

**That's it!** VibesRails is now protecting their codebase.

## Customization

Templates are meant to be customized:

**Add project-specific patterns:**
```yaml
# In vibesrails.yaml
blocking:
  - id: project_specific_rule
    name: "Project Rule"
    regex: "your_pattern"
    message: "Your message"
```

**Adjust hooks:**
```json
// In .claude/hooks.json
{
  "SessionStart": [
    {
      "type": "command",
      "command": "echo 'Project-specific startup command'",
      "description": "Custom startup"
    }
  ]
}
```

## Support

- **Documentation**: [../../docs/](../../docs/)
- **Template Issues**: https://github.com/VictoHughes/VIBESRAILS/issues
- **Questions**: https://github.com/VictoHughes/VIBESRAILS/discussions

---

**Make it easy for your team to code safely. 🚀**
