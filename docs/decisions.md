# Project Decisions

> Active decisions for VibesRails. AI agents and developers should respect these choices.

## Stack

- **Language**: Python 3.12+
- **Framework**: CLI (argparse) + MCP server (FastMCP/mcp SDK)
- **Database**: SQLite (~/.vibesrails/sessions.db) for learning engine, drift, sessions
- **Package manager**: pip (pyproject.toml, PEP 621)

## Architecture

- **Pattern**: CLI package (vibesrails/) + MCP root modules (tools/, core/, storage/)
- **Entry points**: `vibesrails` (cli.py:main), `vibesrails-mcp` (mcp_server.py:main)
- **Key directories**: vibesrails/ (CLI), tools/ (MCP tools), core/ (MCP logic), tests/

## Priorities

- **Next**: methodology guards, PyPI publication pipeline
- **Pending**: learner module stabilization, community pack ecosystem
- **Deferred**: web dashboard, multi-language support

## Constraints

- **Do not add**: Redis, Django, heavy dependencies, breaking API changes
- **Do not remove**: backward-compatible CLI flags, existing MCP tool signatures
- **Do not touch**: storage/migrations.py schema without bumping SCHEMA_VERSION

## Conventions

- **Commit format**: type(scope): description (feat, fix, refactor, test, docs, chore)
- **Branch naming**: feature/, fix/, chore/
- **Test naming**: test_<function>_<scenario> in tests/test_<module>.py
- **Logs**: stderr only (MCP uses stdout for JSON-RPC)
- **Coverage**: minimum 80%, use --cov-report=term (not term-missing)
