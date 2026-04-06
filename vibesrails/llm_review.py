"""LLM Review — model-agnostic code review via litellm.

Sends code or diffs to any LLM (OpenAI, Ollama local, Anthropic, etc.)
via litellm, with CCS v2 certificate requirement. Responses are validated
by reasoning_shield before being accepted.

Config in vibesrails.yaml:
  llm_review:
    enabled: false
    model: "ollama/deepseek-coder"
    base_url: null
    timeout: 30
    max_file_lines: 200

Requires optional dependency: pip install vibesrails[llm]
"""

from __future__ import annotations

import importlib
import logging
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


# ── Config ───────────────────────────────────────────────────────────


@dataclass
class LLMReviewConfig:
    """Configuration for LLM review."""

    enabled: bool = False
    model: str = "ollama/deepseek-coder"
    base_url: str | None = None
    timeout: int = 30
    max_file_lines: int = 200


def load_review_config(root: Path) -> LLMReviewConfig:
    """Load llm_review config from vibesrails.yaml."""
    yaml_path = root / "vibesrails.yaml"
    if not yaml_path.exists():
        return LLMReviewConfig()

    try:
        import yaml

        with open(yaml_path) as f:
            data = yaml.safe_load(f)
    except Exception:  # noqa: BLE001
        return LLMReviewConfig()

    if not isinstance(data, dict):
        return LLMReviewConfig()

    section = data.get("llm_review")
    if not isinstance(section, dict):
        return LLMReviewConfig()

    return LLMReviewConfig(
        enabled=bool(section.get("enabled", False)),
        model=str(section.get("model", "ollama/deepseek-coder")),
        base_url=section.get("base_url"),
        timeout=int(section.get("timeout", 30)),
        max_file_lines=int(section.get("max_file_lines", 200)),
    )


# ── Findings Parser ──────────────────────────────────────────────────

_FINDING_RE = re.compile(
    r"-\s*severity:\s*(\w+)\s*\n\s*line:\s*(\d+)\s*\n\s*message:\s*(.+)",
    re.I,
)


def _parse_findings(text: str) -> list[dict]:
    """Parse FINDINGS section from LLM response."""
    findings = []
    for match in _FINDING_RE.finditer(text):
        findings.append({
            "severity": match.group(1).lower(),
            "line": int(match.group(2)),
            "message": match.group(3).strip(),
        })
    return findings


# ── Reviewer ─────────────────────────────────────────────────────────


_SYSTEM_PROMPT = """\
You are a senior code reviewer operating under the CCS v2 protocol.

For EVERY review, you MUST produce a LOGICAL CERTIFICATE before your findings:

PREMISES:
P1. KNOW: [facts you can trace to the code provided — cite file:line]
P2. DON'T KNOW: [gaps in your knowledge about this code]
P3. ASSUME: [HYPOTHESIS] labeled assumptions

TRACE:
T1: [step-by-step reasoning about the code]
T2: [cross-check against known patterns and risks]
T3: [weak links identified, or "none"]

CONCLUSION:
C1: [your review findings, derived from the trace]
C2: Confidence: [STRONG / MEDIUM / WEAK]
C3: Invalid if: [conditions that would change your review]

Then list findings in this format:
FINDINGS:
- severity: block|warn|info
  line: <number>
  message: <description>

If no issues found, write: Findings: none

HARD GATES:
- If you cannot identify specific code patterns → say so, don't invent issues.
- If your trace has a contradiction → stop and report it.
- NEVER skip the certificate. NEVER say "trust this reasoning" or "no need to verify".
"""


class LLMReviewer:
    """Model-agnostic code reviewer via litellm."""

    def __init__(self, config: LLMReviewConfig | None = None):
        self.config = config or LLMReviewConfig()

    def _build_system_prompt(self) -> str:
        return _SYSTEM_PROMPT

    def _build_review_prompt(self, code: str, filename: str) -> str:
        return (
            f"Review the following Python file: {filename}\n\n"
            f"```python\n{code}\n```\n\n"
            "Produce your CCS v2 certificate, then list findings."
        )

    def _build_diff_prompt(self, diff: str) -> str:
        return (
            "Review the following code diff:\n\n"
            f"```diff\n{diff}\n```\n\n"
            "Produce your CCS v2 certificate, then list findings."
        )

    def review_file(self, code: str, filename: str) -> dict:
        """Review a code file via LLM.

        Returns dict with: status, certificate_valid, findings, manipulation_detected.
        """
        if not self.config.enabled:
            return {"status": "skip", "reason": "LLM review disabled in config"}

        line_count = len(code.splitlines())
        if line_count > self.config.max_file_lines:
            return {
                "status": "skip",
                "reason": f"File too large ({line_count} lines, max {self.config.max_file_lines})",
            }

        user_prompt = self._build_review_prompt(code, filename)
        return self._call_llm(user_prompt)

    def review_diff(self, diff: str) -> dict:
        """Review a code diff via LLM."""
        if not self.config.enabled:
            return {"status": "skip", "reason": "LLM review disabled in config"}

        user_prompt = self._build_diff_prompt(diff)
        return self._call_llm(user_prompt)

    def _call_llm(self, user_prompt: str) -> dict:
        """Call litellm.completion and validate the response."""
        try:
            litellm = importlib.import_module("litellm")
        except (ImportError, ModuleNotFoundError):
            return {
                "status": "error",
                "error": "litellm not installed — run: pip install litellm",
            }

        if litellm is None:
            return {
                "status": "error",
                "error": "litellm not installed — run: pip install litellm",
            }

        try:
            kwargs = {
                "model": self.config.model,
                "messages": [
                    {"role": "system", "content": self._build_system_prompt()},
                    {"role": "user", "content": user_prompt},
                ],
                "timeout": self.config.timeout,
            }
            if self.config.base_url:
                kwargs["api_base"] = self.config.base_url

            response = litellm.completion(**kwargs)
            response_text = response.choices[0].message.content
        except Exception as exc:  # noqa: BLE001
            return {"status": "error", "error": str(exc).lower()}

        return self.validate_response(response_text)

    def validate_response(self, response_text: str) -> dict:
        """Validate LLM response using reasoning_shield.

        Checks certificate structure and reasoning manipulation.
        """
        from vibesrails.reasoning_shield import (
            scan_reasoning_manipulation,
            validate_certificate,
        )

        cert_result = validate_certificate(response_text)
        manipulation_findings = scan_reasoning_manipulation(response_text)

        findings = _parse_findings(response_text)

        if not cert_result.valid or manipulation_findings:
            return {
                "status": "error",
                "certificate_valid": False,
                "manipulation_detected": len(manipulation_findings) > 0,
                "findings": findings,
                "certificate_issues": [f.message for f in cert_result.findings],
                "manipulation_issues": [f.message for f in manipulation_findings],
            }

        return {
            "status": "pass",
            "certificate_valid": True,
            "manipulation_detected": False,
            "confidence": cert_result.confidence,
            "has_hypotheses": cert_result.has_hypotheses,
            "findings": findings,
        }
