"""Targeted Claude review for sensitive changes."""
import json
import logging
import re
from dataclasses import dataclass, field

try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from ..rate_limiting import with_rate_limiting

logger = logging.getLogger(__name__)


@dataclass
class ReviewResult:
    """Result of Claude review."""
    score: int = 0
    issues: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    reviewed: bool = True
    skip_reason: str | None = None


REVIEW_PROMPT = '''You are a senior developer reviewing code changes. Be concise and actionable.

Review this code for:
1. Security vulnerabilities
2. Error handling gaps
3. Edge cases not handled
4. Performance issues
5. Code clarity

Respond in JSON format ONLY:
{{"score": 1-10, "issues": ["issue1"], "strengths": ["strength1"], "suggestions": ["suggestion1"]}}

FILE: {filepath}
CODE:
```
{code}
```'''


class ClaudeReviewer:
    """Targeted Claude review for sensitive/complex changes."""

    SENSITIVE_PATTERNS = [
        r"auth", r"login", r"password", r"secret", r"token", r"key",
        r"payment", r"billing", r"credit", r"card",
        r"crypt", r"hash", r"security",
        r"admin", r"permission", r"role",
        r"sql", r"query", r"database",
    ]

    COMPLEXITY_THRESHOLD = 30

    def __init__(self):
        self.client = None
        if HAS_ANTHROPIC:
            self.client = anthropic.Anthropic()

    def should_review(self, filepath: str, diff: str) -> bool:
        """Determine if this change needs Claude review."""
        path_lower = filepath.lower()
        if any(re.search(p, path_lower) for p in self.SENSITIVE_PATTERNS):
            return True

        control_flow = len(re.findall(r"\+\s*(if|for|while|try|except|match|case)\b", diff))
        if control_flow >= self.COMPLEXITY_THRESHOLD:
            return True

        if any(re.search(p, diff.lower()) for p in self.SENSITIVE_PATTERNS):
            return True

        return False

    def review(self, code: str, filepath: str) -> ReviewResult:
        """Review code with Claude."""
        if not HAS_ANTHROPIC or not self.client:
            return ReviewResult(
                score=0,
                reviewed=False,
                skip_reason="anthropic not installed"
            )

        try:
            response = self._call_claude(REVIEW_PROMPT.format(
                filepath=filepath,
                code=code
            ))

            data = json.loads(response)
            return ReviewResult(
                score=data.get("score", 5),
                issues=data.get("issues", []),
                strengths=data.get("strengths", []),
                suggestions=data.get("suggestions", []),
            )
        except Exception as e:
            logger.error("Claude review failed: %s", e)
            return ReviewResult(
                score=0,
                reviewed=False,
                skip_reason=f"Review failed: {e}"
            )

    @with_rate_limiting
    def _call_claude(self, prompt: str) -> str:
        """Call Claude API with rate limiting."""
        message = self.client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{"role": "user", "content": prompt}]
        )
        return message.content[0].text
