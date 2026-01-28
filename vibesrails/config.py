"""
vibesrails config management with extends/inheritance support.

Supports:
- Local file: extends: "./base.yaml"
- Remote URL: extends: "https://example.com/config.yaml"
- Built-in pack: extends: "@vibesrails/security-pack"
- Multiple extends: extends: ["./base.yaml", "@vibesrails/web-pack"]
"""

import urllib.error
import urllib.request
from pathlib import Path

import yaml

from .scanner import NC, RED, YELLOW

# Allowed domains for remote config fetch (SSRF protection)
ALLOWED_REMOTE_DOMAINS = {
    "github.com",
    "raw.githubusercontent.com",
    "gitlab.com",
    "bitbucket.org",
    "gist.githubusercontent.com",
}

# Built-in pattern packs (bundled with vibesrails)
BUILTIN_PACKS = {
    "@vibesrails/security-pack": "packs/security.yaml",
    "@vibesrails/web-pack": "packs/web.yaml",
    "@vibesrails/fastapi-pack": "packs/fastapi.yaml",
    "@vibesrails/django-pack": "packs/django.yaml",
}

# Cache for remote configs (avoid re-fetching)
_remote_cache: dict[str, dict] = {}


def deep_merge(base: dict, override: dict) -> dict:
    """Deep merge two dicts. Override wins for conflicts.

    Special handling for lists: extends/appends instead of replace.
    """
    result = base.copy()

    for key, value in override.items():
        if key in result:
            if isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge dicts
                result[key] = deep_merge(result[key], value)
            elif isinstance(result[key], list) and isinstance(value, list):
                # Extend lists (patterns from child added to parent)
                result[key] = result[key] + value
            else:
                # Override scalar values
                result[key] = value
        else:
            result[key] = value

    return result


def resolve_pack_path(pack_name: str) -> Path | None:
    """Resolve built-in pack name to file path."""
    if pack_name not in BUILTIN_PACKS:
        return None

    pack_file = BUILTIN_PACKS[pack_name]
    pack_path = Path(__file__).parent / pack_file

    if pack_path.exists():
        return pack_path

    return None


def is_allowed_remote_domain(url: str, extra_domains: set[str] | None = None) -> bool:
    """Check if URL domain is in the allowlist (SSRF protection)."""
    from urllib.parse import urlparse

    try:
        parsed = urlparse(url)

        # Block HTTP (only HTTPS allowed)
        if parsed.scheme != "https":
            return False

        domain = parsed.netloc.lower()

        # Strip userinfo (user:pass@) - prevents bypass like github.com:443@evil.com
        if "@" in domain:
            domain = domain.split("@")[-1]

        # Remove port if present
        if ":" in domain:
            domain = domain.split(":")[0]

        # Block IP addresses (prevent internal network access)
        import re
        # Block IPv4 addresses
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain):
            return False
        # Block IPv6 addresses (including bracketed format like [::1])
        if domain.startswith("[") or re.match(r"^[a-f0-9:]+$", domain, re.IGNORECASE):
            return False

        allowed = ALLOWED_REMOTE_DOMAINS.copy()
        if extra_domains:
            allowed.update(extra_domains)

        return domain in allowed
    except Exception:
        return False


def fetch_remote_config(
    url: str,
    timeout: int = 10,
    extra_domains: set[str] | None = None
) -> dict | None:
    """Fetch config from remote URL with caching and domain validation."""
    # SSRF protection: validate domain allowlist
    if not is_allowed_remote_domain(url, extra_domains):
        print(f"{RED}BLOCKED: Remote domain not allowed: {url}{NC}")
        print(f"  Allowed domains: {', '.join(sorted(ALLOWED_REMOTE_DOMAINS))}")
        print("  Add trusted domains to config: remote_domains: [\"example.com\"]")
        return None

    if url in _remote_cache:
        return _remote_cache[url]

    try:
        # URL scheme validated by is_allowed_remote_domain (HTTPS only, allowlisted domains)
        with urllib.request.urlopen(url, timeout=timeout) as response:  # nosec B310 nosemgrep: SSRF protected
            content = response.read().decode('utf-8')

            # Size limit for remote configs
            if len(content) > 500_000:  # 500KB limit
                print(f"{YELLOW}WARN: Remote config too large, skipping: {url}{NC}")
                return None

            config = yaml.safe_load(content)
            _remote_cache[url] = config
            return config

    except (urllib.error.URLError, yaml.YAMLError) as e:
        print(f"{YELLOW}WARN: Failed to fetch remote config {url}: {e}{NC}")
        return None


def load_extended_config(
    config_path: Path,
    seen_paths: set[str] | None = None
) -> dict:
    """Load config with extends resolution.

    Args:
        config_path: Path to the config file
        seen_paths: Set of already-loaded paths (circular reference detection)

    Returns:
        Merged config dict
    """
    if seen_paths is None:
        seen_paths = set()

    # Circular reference check
    path_key = str(config_path.resolve())
    if path_key in seen_paths:
        print(f"{YELLOW}WARN: Circular config reference detected: {config_path}{NC}")
        return {}

    seen_paths.add(path_key)

    # Load the config file
    with open(config_path) as f:
        config = yaml.safe_load(f) or {}

    # Check for extends
    extends = config.pop("extends", None)
    if not extends:
        return config

    # Normalize extends to list
    if isinstance(extends, str):
        extends = [extends]

    # Start with empty base
    merged = {}

    # Process each parent config
    for parent_ref in extends:
        parent_config = resolve_extends(parent_ref, config_path.parent, seen_paths)
        if parent_config:
            merged = deep_merge(merged, parent_config)

    # Merge child config (overrides parents)
    merged = deep_merge(merged, config)

    return merged


def resolve_extends(
    ref: str,
    base_dir: Path,
    seen_paths: set[str]
) -> dict | None:
    """Resolve a single extends reference.

    Args:
        ref: The extends reference (path, URL, or pack name)
        base_dir: Directory of the config file (for relative paths)
        seen_paths: Set of already-loaded paths

    Returns:
        Loaded config dict or None
    """
    # Built-in pack
    if ref.startswith("@vibesrails/"):
        pack_path = resolve_pack_path(ref)
        if pack_path:
            return load_extended_config(pack_path, seen_paths.copy())
        else:
            print(f"{YELLOW}WARN: Unknown pack: {ref}{NC}")
            print(f"  Available packs: {', '.join(BUILTIN_PACKS.keys())}")
            return None

    # Remote URL
    if ref.startswith("http://") or ref.startswith("https://"):
        remote_config = fetch_remote_config(ref)
        if remote_config:
            # Remote configs can also have extends (but not recursive remote)
            extends = remote_config.pop("extends", None)
            if extends:
                print(f"{YELLOW}WARN: Remote config extends not supported: {ref}{NC}")
            return remote_config
        return None

    # Local file path
    if ref.startswith("./") or ref.startswith("../") or ref.startswith("/"):
        if ref.startswith("/"):
            local_path = Path(ref)
        else:
            local_path = base_dir / ref

        if local_path.exists():
            return load_extended_config(local_path, seen_paths.copy())
        else:
            print(f"{YELLOW}WARN: Config file not found: {local_path}{NC}")
            return None

    # Assume local file in same directory
    local_path = base_dir / ref
    if local_path.exists():
        return load_extended_config(local_path, seen_paths.copy())

    print(f"{YELLOW}WARN: Could not resolve extends: {ref}{NC}")
    return None


def load_config_with_extends(config_path: Path | str) -> dict:
    """Load config file with full extends support.

    This is the main entry point for loading configs.
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Config not found: {config_path}")

    # Size check
    if config_path.stat().st_size > 1_000_000:
        raise ValueError(f"Config file too large: {config_path}")

    return load_extended_config(config_path)
