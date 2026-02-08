"""Centralized secret detection patterns — single source of truth.

All secret-scanning code (pre_tool_use.py, ptuh.py, env_safety.py)
imports from here. Add new patterns in ONE place.

Each pattern is a tuple of (regex_string, label).
Regexes are compiled with re.IGNORECASE by consumers.
"""

# --- API Keys & Tokens ---

SECRET_PATTERN_DEFS: list[tuple[str, str]] = [
    # Cloud providers
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"(?:sk-|sk-proj-)[a-zA-Z0-9\-]{20,}", "OpenAI/Anthropic API Key"),
    (r"AIza[0-9A-Za-z\-_]{35}", "Google API Key"),

    # Git platforms
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub Personal Access Token"),
    (r"gho_[a-zA-Z0-9]{36}", "GitHub OAuth Token"),
    (r"glpat-[a-zA-Z0-9\-_]{20,}", "GitLab Personal Access Token"),

    # Payment / SaaS
    (r"sk_(?:live|test)_[a-zA-Z0-9]{20,}", "Stripe Secret Key"),
    (r"whsec_[a-zA-Z0-9]{20,}", "Webhook Secret (Stripe/Svix)"),
    (r"SG\.[a-zA-Z0-9\-_]{20,}", "SendGrid API Key"),

    # Communication
    (r"xox[bps]-[a-zA-Z0-9\-]{10,}", "Slack Token"),

    # Auth tokens
    (r"Bearer\s+[a-zA-Z0-9\-_.]{20,}", "Bearer Token"),

    # PEM private keys
    (r"-----BEGIN\s+(?:RSA |EC |DSA |OPENSSH )?PRIVATE KEY-----", "Private Key (PEM)"),

    # Database connection strings with embedded password
    (
        r"(?:postgresql|mysql|mongodb|redis|amqp)://[^:]+:[^@]{4,}@",
        "Database URL with password",
    ),

    # Generic hardcoded secrets (assignment patterns)
    (
        r"(?:password|passwd|pwd)\s*=\s*['\"][^'\"]{8,}['\"]",
        "Hardcoded password",
    ),
    (
        r"(?:api_key|apikey|secret_key|secret|token)\s*=\s*['\"][^'\"]{8,}['\"]",
        "Hardcoded API key/secret",
    ),
]
