"""Vibe mode protection patterns — extracted from vibe_mode.py."""

VIBE_PROTECTIONS = {
    "api_keys": {
        "name": "Cles API (OpenAI, Anthropic, AWS, Google...)",
        "patterns": [
            {"id": "openai_key", "regex": r"sk-[a-zA-Z0-9]{20,}", "message": "Cle OpenAI detectee"},
            {"id": "anthropic_key", "regex": r"sk-ant-[a-zA-Z0-9-]{20,}", "message": "Cle Anthropic detectee"},
            {"id": "aws_key", "regex": r"AKIA[0-9A-Z]{16}", "message": "Cle AWS detectee"},
            {"id": "google_key", "regex": r"AIza[0-9A-Za-z-_]{35}", "message": "Cle Google API detectee"},
            {"id": "github_token", "regex": r"ghp_[a-zA-Z0-9]{36}", "message": "Token GitHub detecte"},
            {"id": "generic_api_key", "regex": r"['\"][a-zA-Z0-9]{32,}['\"]", "message": "Possible cle API detectee"},
        ],
    },
    "passwords": {
        "name": "Mots de passe hardcodes",
        "patterns": [
            {"id": "password_assign", "regex": r"password\s*=\s*['\"][^'\"]+['\"]", "message": "Mot de passe hardcode"},
            {"id": "pwd_assign", "regex": r"pwd\s*=\s*['\"][^'\"]+['\"]", "message": "Mot de passe hardcode"},
            {"id": "passwd_assign", "regex": r"passwd\s*=\s*['\"][^'\"]+['\"]", "message": "Mot de passe hardcode"},
        ],
    },
    "tokens": {
        "name": "Tokens et secrets",
        "patterns": [
            {"id": "bearer_token", "regex": r"Bearer\s+[a-zA-Z0-9._-]+", "message": "Bearer token detecte"},
            {"id": "jwt_token", "regex": r"eyJ[a-zA-Z0-9_-]*\.eyJ[a-zA-Z0-9_-]*\.[a-zA-Z0-9_-]*", "message": "JWT token detecte"},
            {"id": "secret_assign", "regex": r"secret\s*=\s*['\"][^'\"]+['\"]", "message": "Secret hardcode"},
        ],
    },
    "urls": {
        "name": "URLs avec credentials",
        "patterns": [
            {"id": "url_with_creds", "regex": r"://[^:]+:[^@]+@", "message": "URL avec credentials detectee"},
            {"id": "localhost_creds", "regex": r"localhost:[0-9]+.*password", "message": "Credentials localhost"},
        ],
    },
}

SKIP_DIRS = {".venv", "venv", "__pycache__", ".git", "node_modules"}
