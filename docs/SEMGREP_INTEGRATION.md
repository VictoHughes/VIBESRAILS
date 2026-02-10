# Semgrep Integration

**VibesRails 1.2.0+** integrates Semgrep for enhanced code analysis.

## Overview

VibesRails now acts as an **intelligent meta-scanner** that orchestrates:

- **Semgrep**: AST-based analysis (precision, deep patterns)
- **VibesRails**: Architecture rules + Guardian Mode (AI safety)

### Why Both?

| Feature | Semgrep | VibesRails |
|---------|---------|------------|
| **Analysis Type** | AST-based | Regex-based |
| **Precision** | Very high | High |
| **Speed** | Moderate | Fast |
| **Coverage** | Security + bugs | Security + architecture |
| **AI Detection** | ❌ | ✅ Guardian Mode |
| **Architecture Rules** | ❌ | ✅ DIP, layers |
| **Custom Patterns** | Complex | Simple YAML |

**Result:** Best of both worlds - Semgrep's precision + VibesRails' flexibility

---

## How It Works

### 1. Auto-Installation

On first scan, VibesRails auto-installs Semgrep:

```bash
$ vibesrails
📦 Installing Semgrep (enhanced scanning)...
✅ Semgrep installed

🔍 Running Semgrep scan...
   Found 5 issue(s)
🔍 Running VibesRails scan...
   Found 2 issue(s)

📊 Scan Statistics:
   Semgrep:     5 issues
   VibesRails:  2 issues
   Duplicates:  1 (merged)
   Total:       6 unique issues
```

### 2. Orchestration

```
vibesrails scan
    ↓
1. Load vibesrails.yaml
2. Check Semgrep (install if needed)
3. Run Semgrep (AST analysis)
4. Run VibesRails (regex + architecture)
5. Merge results (deduplicate)
6. Display unified output
```

### 3. Deduplication

Results are merged intelligently:

- **Key:** `(file, line)` tuple
- **Priority:** Semgrep first (more precise), then VibesRails
- **Stats:** Tracks duplicates for transparency

```python
# Same issue detected by both scanners
# Only Semgrep result is shown (higher priority)

[SEMGREP] test.py:10
  [python.lang.security.hardcoded-secret] Hardcoded API key
```

---

## Configuration

Add `semgrep` section to `vibesrails.yaml`:

```yaml
version: "1.0"

# Semgrep Integration
semgrep:
  enabled: true
  preset: "auto"  # auto | strict | minimal
  additional_rules:
    - p/python
    - p/fastapi
  exclude_rules: []
```

### Presets

| Preset | Rules | Use Case |
|--------|-------|----------|
| `auto` | ~100 rules | Default, balanced |
| `strict` | ~200 rules | Maximum coverage |
| `minimal` | ~30 rules | Secrets + injections only |

### Additional Rules

Semgrep rule packs:

```yaml
semgrep:
  additional_rules:
    - p/python        # Python best practices
    - p/django        # Django security
    - p/fastapi       # FastAPI patterns
    - p/flask         # Flask security
    - p/owasp-top-10  # OWASP Top 10
```

Find more: https://semgrep.dev/r

### Exclude Rules

Skip specific Semgrep rules:

```yaml
semgrep:
  exclude_rules:
    - generic.secrets.security.detected-secret  # Use VibesRails for secrets
```

---

## Smart Setup

`vibesrails --setup` auto-configures Semgrep:

```bash
$ vibesrails --setup
📋 Analyzing project...
  Detected types: FastAPI
  Packs to include: @vibesrails/security-pack, @vibesrails/fastapi-pack

✅ Generated vibesrails.yaml:
   - Semgrep: enabled (preset: auto, rules: p/fastapi)
   - Guardian: enabled
   - Architecture: detected 3 layers
```

**Generated config:**

```yaml
semgrep:
  enabled: true
  preset: "auto"
  additional_rules:
    - "p/fastapi"  # Auto-detected from project type
  exclude_rules: []
```

---

## Output Format

Results are categorized and attributed:

```bash
🔒 SECURITY:
BLOCK test.py:10 [SEMGREP]
  [python.lang.security.hardcoded-secret] Hardcoded API key

🏗️ ARCHITECTURE:
BLOCK backend/domain/model.py:25 [VIBESRAILS]
  [dip_domain_infra] Domain layer cannot import infrastructure

🛡️ GUARDIAN:
BLOCK api/auth.py:42 [VIBESRAILS]
  [guardian_ai_session] AI-generated code requires extra review

================================
BLOCKING: 3 | WARNINGS: 0
```

**Source Attribution:**
- `[SEMGREP]` - Detected by Semgrep
- `[VIBESRAILS]` - Detected by VibesRails

---

## Graceful Degradation

VibesRails works standalone if Semgrep fails:

```bash
$ vibesrails
📦 Installing Semgrep...
⚠️  Semgrep install failed, continuing with VibesRails only

🔍 Running VibesRails scan...
   Found 2 issue(s)

================================
BLOCKING: 2 | WARNINGS: 0
```

**No breaking changes** - existing workflows continue working.

---

## Performance

### Scan Time Comparison

| Scanner | Time (100 files) |
|---------|------------------|
| VibesRails only | ~2s |
| Semgrep only | ~15s |
| Both (orchestrated) | ~17s |

**Overhead:** ~15% for 2x coverage

### Resource Usage

- **Disk:** +40MB (Semgrep binary)
- **Memory:** +50MB during scan
- **CPU:** Parallel execution when possible

---

## Advanced Usage

### Disable Semgrep

If you only want VibesRails:

```yaml
semgrep:
  enabled: false
```

### Custom Semgrep Config

Use your own Semgrep config:

```bash
# Run Semgrep separately with custom config
semgrep --config=custom-rules.yaml .

# Then run VibesRails for architecture checks
vibesrails
```

### CI/CD Integration

Run both in CI:

```yaml
# .github/workflows/security.yml
- name: VibesRails Scan
  run: vibesrails --all  # Semgrep auto-installed
```

---

## Troubleshooting

### Semgrep Install Fails

**Symptom:** `⚠️ Semgrep install failed`

**Solutions:**
1. Check network connectivity
2. Manual install: `pip install semgrep`
3. Disable: `semgrep: {enabled: false}` in config

### Slow Scans

**Symptom:** Scans take >1 minute

**Solutions:**
1. Use `preset: minimal` for faster scans
2. Exclude large files in `.semgrepignore`
3. Run VibesRails only: `semgrep: {enabled: false}`

### Duplicate Issues

**Symptom:** Same issue shown twice

**Solutions:**
- Check VibesRails version (1.2.0+ has deduplication)
- Exclude redundant Semgrep rules: `exclude_rules: [...]`

---

## Migration Guide

### From VibesRails 1.1.x

**No breaking changes!** Just upgrade:

```bash
pip install --upgrade vibesrails
```

**What changes:**
- First scan auto-installs Semgrep (~40MB)
- New `semgrep:` section in config (optional)
- Output shows `[SEMGREP]` or `[VIBESRAILS]` badges

**Opt-out:**

```yaml
# vibesrails.yaml
semgrep:
  enabled: false  # Disable Semgrep integration
```

---

## FAQ

### Q: Is Semgrep required?

**A:** No. VibesRails works standalone. Semgrep enhances analysis but is optional.

### Q: Does this slow down commits?

**A:** Slightly (~15% overhead). Semgrep adds ~15s for 100 files. Use `preset: minimal` for faster scans.

### Q: Can I use my own Semgrep config?

**A:** Yes. Run Semgrep separately, or contribute to VibesRails preset system.

### Q: What about privacy?

**A:** 100% local. No data sent to cloud. Both Semgrep and VibesRails run locally.

### Q: Does this use more tokens?

**A:** No. Semgrep is local (like VibesRails). Only `--learn` uses tokens (optional).

---

## Credits

- **Semgrep:** r2c (https://semgrep.dev)
- **VibesRails:** by SM (https://github.com/VictoHughes/VIBESRAILS)

**Integration Philosophy:** Augment, don't compete. Use the best tool for each job.

---

## See Also

- [VibesRails README](../README.md)
- [Semgrep Documentation](https://semgrep.dev/docs/)
- [Configuration Reference](../config/vibesrails.yaml)
- [VISION.md](../VISION.md) - Project philosophy
