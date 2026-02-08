"""Tests for core/secret_patterns.py — centralized secret detection patterns."""

import re

import pytest

from core.secret_patterns import SECRET_PATTERN_DEFS


def _match(text: str) -> list[str]:
    """Return labels of all patterns that match the given text."""
    hits = []
    for pattern_str, label in SECRET_PATTERN_DEFS:
        compiled = re.compile(pattern_str, re.IGNORECASE)
        if compiled.search(text):
            hits.append(label)
    return hits


class TestSecretPatternCoverage:
    """Every pattern must detect its target secret type."""

    def test_aws_access_key(self):
        assert "AWS Access Key" in _match("AKIAIOSFODNN7EXAMPLE")

    def test_openai_key(self):
        assert "OpenAI/Anthropic API Key" in _match("sk-abc123def456ghi789jkl012mno")

    def test_openai_proj_key(self):
        assert "OpenAI/Anthropic API Key" in _match("sk-proj-abcdefghij1234567890")

    def test_anthropic_key(self):
        """Anthropic keys have hyphens: sk-ant-api03-xxx."""
        assert "OpenAI/Anthropic API Key" in _match("sk-ant-api03-fake1234567890abcdef")

    def test_google_api_key(self):
        assert "Google API Key" in _match("AIzaSyA1234567890abcdefghijklmnopqrstuv")

    def test_github_pat(self):
        assert "GitHub Personal Access Token" in _match(
            "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        )

    def test_github_oauth(self):
        assert "GitHub OAuth Token" in _match(
            "gho_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        )

    def test_gitlab_pat(self):
        assert "GitLab Personal Access Token" in _match("glpat-xxxxxxxxxxxxxxxxxxxx")

    def test_stripe_live_key(self):
        assert "Stripe Secret Key" in _match("sk_live_abcdefghij1234567890")

    def test_stripe_test_key(self):
        assert "Stripe Secret Key" in _match("sk_test_abcdefghij1234567890")

    def test_webhook_secret(self):
        assert "Webhook Secret (Stripe/Svix)" in _match("whsec_abcdefghij1234567890")

    def test_sendgrid_key(self):
        assert "SendGrid API Key" in _match("SG.abcdefghij1234567890_abc")

    def test_slack_bot_token(self):
        assert "Slack Token" in _match("xoxb-1234567890-abcdef")

    def test_slack_user_token(self):
        assert "Slack Token" in _match("xoxp-1234567890-abcdef")

    def test_bearer_token(self):
        assert "Bearer Token" in _match("Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9")

    def test_pem_rsa_private_key(self):
        assert "Private Key (PEM)" in _match("-----BEGIN RSA PRIVATE KEY-----")

    def test_pem_ec_private_key(self):
        assert "Private Key (PEM)" in _match("-----BEGIN EC PRIVATE KEY-----")

    def test_pem_generic_private_key(self):
        assert "Private Key (PEM)" in _match("-----BEGIN PRIVATE KEY-----")

    def test_postgres_url_with_password(self):
        assert "Database URL with password" in _match(
            "postgresql://user:secretpass@localhost:5432/mydb"
        )

    def test_mysql_url_with_password(self):
        assert "Database URL with password" in _match(
            "mysql://admin:hunter2abc@db.example.com/app"
        )

    def test_mongodb_url_with_password(self):
        assert "Database URL with password" in _match(
            "mongodb://root:longpassword@mongo:27017/admin"
        )

    def test_hardcoded_password(self):
        assert "Hardcoded password" in _match('password = "SuperSecret123"')

    def test_hardcoded_api_key_assignment(self):
        assert "Hardcoded API key/secret" in _match('api_key = "some-long-value-here"')


class TestSecretPatternFalsePositives:
    """Patterns should NOT trigger on safe content."""

    def test_safe_env_var_usage(self):
        assert _match('api_key = os.environ["API_KEY"]') == []

    def test_short_password(self):
        """Passwords under 8 chars should not match."""
        assert "Hardcoded password" not in _match('password = "short"')

    def test_db_url_without_password(self):
        """DB URLs without passwords should not match."""
        assert _match("postgresql://localhost:5432/mydb") == []

    def test_plain_text_no_secrets(self):
        assert _match("Hello world, this is normal text") == []

    def test_comment_with_example_prefix(self):
        """Comments are not filtered at pattern level (handled by consumers)."""
        # This is intentional — the patterns themselves match, but consumers
        # (pre_tool_use.py) skip comment lines via _should_skip_line()
        pass


class TestPatternConsistency:
    """Verify structural integrity of the pattern list."""

    def test_all_patterns_are_tuples(self):
        for item in SECRET_PATTERN_DEFS:
            assert isinstance(item, tuple)
            assert len(item) == 2

    def test_all_patterns_compile(self):
        for pattern_str, label in SECRET_PATTERN_DEFS:
            compiled = re.compile(pattern_str, re.IGNORECASE)
            assert compiled is not None, f"Failed to compile: {label}"

    def test_no_duplicate_labels(self):
        labels = [label for _, label in SECRET_PATTERN_DEFS]
        assert len(labels) == len(set(labels)), f"Duplicate labels: {labels}"

    def test_minimum_pattern_count(self):
        """We should have at least 15 patterns after centralization."""
        assert len(SECRET_PATTERN_DEFS) >= 15
