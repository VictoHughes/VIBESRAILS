"""Pedagogy messages for scan_code guards — extracted from scan_code.py."""

GUARD_PEDAGOGY: dict[str, dict[str, str]] = {
    "dependency_audit": {
        "why": (
            "AI code generators often suggest packages by name without verifying "
            "they exist or are safe. Typosquatting and abandoned packages are real "
            "supply-chain attack vectors."
        ),
        "how_to_fix": "Pin the dependency to a known-good version in requirements.txt or pyproject.toml.",
        "prevention": "Always verify packages on PyPI before adding them. Use pip-audit regularly.",
    },
    "performance": {
        "why": (
            "AI-generated code frequently contains N+1 queries, string concatenation "
            "in loops, and other patterns that are correct but slow at scale."
        ),
        "how_to_fix": "Replace the anti-pattern with the suggested alternative in the finding message.",
        "prevention": "Review generated code for loops that hit I/O. Prefer batch operations.",
    },
    "complexity": {
        "why": (
            "High cyclomatic complexity makes code hard to test and maintain. "
            "AI generators tend to produce deeply nested conditionals instead of "
            "early returns or strategy patterns."
        ),
        "how_to_fix": "Extract nested logic into helper functions. Use early returns to flatten conditionals.",
        "prevention": "Ask the AI to keep functions under 10 cyclomatic complexity.",
    },
    "env_safety": {
        "why": (
            "Secrets leaked in code, environment variables, or __repr__ methods "
            "are the #1 cause of security breaches in AI-assisted projects."
        ),
        "how_to_fix": "Move secrets to environment variables. Never hardcode credentials.",
        "prevention": "Use a .env file with python-dotenv. Add .env to .gitignore.",
    },
    "git_workflow": {
        "why": (
            "AI sessions can produce large, unfocused commits that are hard to review. "
            "Proper git hygiene prevents sneaking bad code into production."
        ),
        "how_to_fix": "Follow the commit message convention. Keep commits focused on one change.",
        "prevention": "Commit after each logical change, not at the end of a long session.",
    },
    "dead_code": {
        "why": (
            "AI generators add unused imports and variables as artifacts of their "
            "generation process. Dead code obscures the real logic and creates "
            "false dependencies."
        ),
        "how_to_fix": "Remove the unused import or variable identified in the finding.",
        "prevention": "Run dead code detection after every AI generation session.",
    },
    "observability": {
        "why": (
            "print() statements left in production code leak internal state and "
            "bypass structured logging. AI generators use print() for debugging "
            "but forget to remove it."
        ),
        "how_to_fix": "Replace print() with logging.getLogger(__name__).info() or .debug().",
        "prevention": "Configure a linter rule to forbid print() in non-test code.",
    },
    "type_safety": {
        "why": (
            "Missing type annotations make AI-generated code harder to validate. "
            "Type checkers catch bugs that tests miss — especially None-safety issues."
        ),
        "how_to_fix": "Add type annotations to the function signatures identified in the finding.",
        "prevention": "Ask the AI to always include type annotations. Run mypy in CI.",
    },
    "docstring": {
        "why": (
            "Public functions without docstrings are opaque to both humans and AI tools. "
            "The next AI session will misunderstand undocumented code."
        ),
        "how_to_fix": "Add a docstring explaining what the function does, its params, and return value.",
        "prevention": "Enforce docstrings for public functions in your linter config.",
    },
    "pr_checklist": {
        "why": (
            "Pull requests from AI sessions often include unrelated changes, "
            "debug artifacts, or incomplete implementations."
        ),
        "how_to_fix": "Review the staged diff and remove anything not related to the PR's purpose.",
        "prevention": "Use a PR template. Limit AI sessions to one feature per PR.",
    },
    "database_safety": {
        "why": (
            "SQL injection is the most common vulnerability in AI-generated code. "
            "AI tools frequently use f-strings or .format() in SQL queries."
        ),
        "how_to_fix": "Use parameterized queries (?, %s) instead of string interpolation.",
        "prevention": "Use an ORM or query builder. Never pass user input directly into SQL.",
    },
    "api_design": {
        "why": (
            "AI generators produce API endpoints that lack authentication, validation, "
            "or proper error handling — patterns that look correct but are insecure."
        ),
        "how_to_fix": "Add input validation, authentication checks, and proper HTTP status codes.",
        "prevention": "Define API contracts (OpenAPI spec) before generating implementation.",
    },
    "pre_deploy": {
        "why": (
            "Pre-deploy checks catch issues that individual guards miss — like version "
            "mismatches, failing tests, or missing changelog entries."
        ),
        "how_to_fix": "Fix the specific pre-deploy check that failed (see finding message).",
        "prevention": "Run pre-deploy checks in CI before every merge to main.",
    },
    "test_integrity": {
        "why": (
            "AI-generated tests often mock too aggressively, test the mock instead of "
            "the code, or contain no real assertions — giving false confidence."
        ),
        "how_to_fix": "Reduce mocking. Assert real behavior, not mock call counts.",
        "prevention": "Review AI-generated tests manually. Run mutation testing to verify test quality.",
    },
    "mutation": {
        "why": (
            "Mutation testing reveals tests that pass even when the code is broken. "
            "AI-generated test suites frequently have low mutation kill rates."
        ),
        "how_to_fix": "Add assertions that catch the surviving mutants listed in the finding.",
        "prevention": "Target 80%+ mutation kill rate. Focus on business logic, not boilerplate.",
    },
    "architecture_drift": {
        "why": (
            "AI generators ignore layer boundaries, importing freely across modules. "
            "This creates spaghetti dependencies that are hard to untangle later."
        ),
        "how_to_fix": "Move the import to the correct layer or create a proper interface.",
        "prevention": "Define architecture rules (import-linter) and enforce them in CI.",
    },
}

# Fallback for guards not in the pedagogy dict
DEFAULT_PEDAGOGY = {
    "why": "This issue was detected by an automated guard. Review the finding message for details.",
    "how_to_fix": "Address the specific issue described in the finding message.",
    "prevention": "Run vibesrails guards regularly to catch issues early.",
}
