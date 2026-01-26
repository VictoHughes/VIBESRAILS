"""
vibesrails learn mode - Claude-powered pattern discovery.

Analyzes codebase and suggests security/quality patterns to add to vibesrails.yaml.
Human validates all suggestions before they're added.
"""

import random
from pathlib import Path

# Optional anthropic import
try:
    import anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

from .scanner import BLUE, GREEN, NC, RED, YELLOW, get_all_python_files

LEARN_PROMPT = """You are a security and code quality expert analyzing a Python codebase.

Based on the code samples provided, suggest NEW patterns that could be added to a vibesrails.yaml security scanner config.

IMPORTANT:
- Only suggest patterns that appear multiple times or represent real risks
- Don't suggest patterns that are already common (hardcoded secrets, SQL injection, subprocess shell injection)
- Focus on project-specific anti-patterns you observe
- Each pattern needs a regex that will match the issue

For each suggestion, provide:
1. Pattern ID (snake_case)
2. Name (human readable)
3. Regex (Python regex to detect it)
4. Message (helpful fix suggestion)
5. Level (BLOCK for security, WARN for quality)
6. Reasoning (why this pattern matters)

Format your response as YAML that can be added to vibesrails.yaml:

```yaml
# Suggested patterns from learn mode
# Review each one before adding to your config

suggested:
  - id: pattern_id
    name: "Pattern Name"
    regex: "regex_here"
    message: "Fix suggestion"
    level: "WARN"  # or BLOCK
    # Reasoning: Why this pattern matters
```

If you don't find any new patterns worth suggesting, respond with:
```yaml
# No new patterns suggested
# The codebase looks clean or existing patterns cover the issues
suggested: []
```

CODE SAMPLES TO ANALYZE:
"""


def sample_codebase(max_files: int = 20, max_lines_per_file: int = 100) -> str:
    """Get representative code samples from the codebase."""
    files = get_all_python_files()

    if not files:
        return ""

    # Sample random files if too many
    if len(files) > max_files:
        files = random.sample(files, max_files)

    samples = []
    for filepath in files:
        try:
            content = Path(filepath).read_text()
            lines = content.split("\n")[:max_lines_per_file]
            samples.append(f"# File: {filepath}\n" + "\n".join(lines))
        except (OSError, UnicodeDecodeError):
            continue

    return "\n\n---\n\n".join(samples)


def analyze_with_claude(code_samples: str) -> str:
    """Send code samples to Claude for analysis."""
    if not HAS_ANTHROPIC:
        return None

    client = anthropic.Anthropic()

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=2000,
        messages=[
            {
                "role": "user",
                "content": LEARN_PROMPT + code_samples
            }
        ]
    )

    return message.content[0].text


def run_learn_mode() -> bool:
    """Run learn mode to discover new patterns."""
    print(f"\n{BLUE}vibesrails --learn{NC}")
    print("=" * 40)
    print("Claude-powered pattern discovery\n")

    if not HAS_ANTHROPIC:
        print(f"{RED}ERROR: anthropic package not installed{NC}")
        print("Install with: pip install vibesrails[claude]")
        return False

    # Sample codebase
    print(f"{YELLOW}Sampling codebase...{NC}")
    code_samples = sample_codebase()

    if not code_samples:
        print(f"{RED}No Python files found to analyze{NC}")
        return False

    print("Collected samples from codebase\n")

    # Analyze with Claude
    print(f"{YELLOW}Analyzing with Claude...{NC}")
    try:
        result = analyze_with_claude(code_samples)
    except Exception as e:
        print(f"{RED}Claude API error: {e}{NC}")
        print("Make sure ANTHROPIC_API_KEY is set")
        return False

    if not result:
        print(f"{RED}No response from Claude{NC}")
        return False

    # Display results
    print(f"\n{GREEN}=== Suggested Patterns ==={NC}\n")
    print(result)
    print(f"\n{GREEN}==========================={NC}")
    print(f"\n{YELLOW}Review suggestions above.{NC}")
    print("Copy useful patterns to your vibesrails.yaml")
    print("(Human validation required before adding)")

    return True
