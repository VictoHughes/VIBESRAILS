"""MCP tool: shield_prompt — prompt injection detection.

Scans text, code files, or MCP tool inputs for 5 categories of
prompt injection: system_override, role_hijack, exfiltration,
encoding_evasion, delimiter_escape.
"""

from __future__ import annotations

import logging

from core.input_validator import (
    InputValidationError,
    validate_dict,
    validate_string,
)
from core.learning_bridge import record_safe
from core.path_validator import PathValidationError, validate_path
from core.prompt_shield import PromptShield

logger = logging.getLogger(__name__)

# ── Pedagogy per category ────────────────────────────────────────────

CATEGORY_PEDAGOGY: dict[str, dict[str, str]] = {
    "system_override": {
        "why": (
            "Ce texte contient une instruction qui demande a l'IA d'ignorer ou "
            "contourner ses regles. C'est le vecteur principal des attaques "
            "'Rules File Backdoor' (Pillar Security, mars 2025)."
        ),
        "how_to_fix": (
            "Supprime l'instruction suspecte. Verifie l'historique git: "
            "qui l'a ajoutee?"
        ),
        "prevention": "Scanne tout texte externe avant de le traiter avec un LLM.",
    },
    "role_hijack": {
        "why": (
            "Ce texte tente de reassigner l'identite ou le comportement de l'IA. "
            "Un attaquant peut transformer un assistant securise en complice."
        ),
        "how_to_fix": (
            "Supprime la tentative de role hijacking. Isole les inputs "
            "utilisateur du prompt systeme."
        ),
        "prevention": "Ne jamais inserer du texte non-fiable dans le prompt systeme.",
    },
    "exfiltration": {
        "why": (
            "Ce code ou texte tente d'envoyer des donnees vers un endpoint "
            "externe. Si genere par une IA, elle a peut-etre ete manipulee "
            "pour ajouter cette exfiltration."
        ),
        "how_to_fix": (
            "Verifie que l'URL de destination est legitime. "
            "Bloque les domaines inconnus."
        ),
        "prevention": (
            "Whitelist les domaines autorises. Scanne le code genere "
            "avant toute utilisation."
        ),
    },
    "encoding_evasion": {
        "why": (
            "Ce texte utilise un encodage (Unicode invisible, base64) pour "
            "cacher des instructions invisibles aux humains mais lues par les LLMs."
        ),
        "how_to_fix": (
            "Decode et inspecte le contenu cache. Supprime les caracteres "
            "invisibles."
        ),
        "prevention": (
            "Normalise tout texte externe (strip Unicode invisible, "
            "decode base64 suspect)."
        ),
    },
    "delimiter_escape": {
        "why": (
            "Ce texte contient des delimiteurs de tokenizer LLM "
            "(ChatML, Llama, MCP). Un attaquant peut injecter de faux "
            "messages systeme ou tromper le modele."
        ),
        "how_to_fix": (
            "Supprime ou echappe les delimiteurs. Ne jamais inserer "
            "du texte brut dans le flux MCP."
        ),
        "prevention": "Sanitize tous les inputs avant injection dans le contexte LLM.",
    },
}

_NO_INPUT_PEDAGOGY: dict[str, str] = {
    "why": "Aucune entree fournie a analyser.",
    "how_to_fix": "Fournis text, file_path, ou tool_name+arguments.",
    "prevention": "Toujours scanner les inputs avant traitement LLM.",
}


# ── MCP tool function ────────────────────────────────────────────────


def shield_prompt(
    text: str | None = None,
    file_path: str | None = None,
    tool_name: str | None = None,
    arguments: dict | None = None,
) -> dict:
    """Scan for prompt injection in text, files, or MCP inputs.

    Args:
        text: Arbitrary text to scan.
        file_path: Path to a file to scan.
        tool_name: MCP tool name (requires arguments).
        arguments: MCP tool arguments dict (requires tool_name).

    Returns:
        Dict with status, scan_mode, findings, injection_count,
        categories_found, pedagogy.
    """
    # Validate inputs
    try:
        if text is not None:
            validate_string(text, "text", max_length=10_000_000)
        if arguments is not None:
            validate_dict(arguments, "arguments")
    except InputValidationError as exc:
        return {
            "status": "error",
            "error": str(exc),
            "findings": [],
            "categories_found": [],
            "pedagogy": _NO_INPUT_PEDAGOGY,
        }

    shield = PromptShield()

    try:
        if file_path:
            try:
                validated_path = validate_path(
                    file_path, must_exist=True, must_be_file=True, max_size_mb=10,
                )
            except PathValidationError as exc:
                return {
                    "status": "error",
                    "error": str(exc),
                    "findings": [],
                    "categories_found": [],
                    "pedagogy": _NO_INPUT_PEDAGOGY,
                }
            findings = shield.scan_file(str(validated_path))
            scan_mode = "file"
        elif tool_name and arguments is not None:
            findings = shield.scan_mcp_input(tool_name, arguments)
            scan_mode = "mcp_input"
        elif text is not None:
            findings = shield.scan_text(text)
            scan_mode = "text"
        else:
            return {
                "status": "error",
                "error": "No input provided. Use text, file_path, or tool_name+arguments.",
                "findings": [],
                "categories_found": [],
                "pedagogy": _NO_INPUT_PEDAGOGY,
            }

        # Determine status
        has_block = any(f.severity == "block" for f in findings)
        has_warn = any(f.severity == "warn" for f in findings)

        if has_block:
            status = "block"
        elif has_warn:
            status = "warn"
        else:
            status = "pass"

        categories_found = sorted(set(f.category for f in findings))

        findings_list = [
            {
                "category": f.category,
                "severity": f.severity,
                "message": f.message,
                "line": f.line,
                "matched_text": (
                    f.matched_text[:80] + "..."
                    if len(f.matched_text) > 80
                    else f.matched_text
                ),
                "context": (
                    "[redacted]"
                    if "decoded" in (f.context or "").lower()
                    else (f.context or "")[:120]
                ),
            }
            for f in findings
        ]

        # Build pedagogy
        if categories_found:
            main_cat = categories_found[0]
            pedagogy = {
                **CATEGORY_PEDAGOGY.get(main_cat, {}),
                "categories_detected": {
                    cat: CATEGORY_PEDAGOGY.get(cat, {}).get("why", "")
                    for cat in categories_found
                },
            }
        else:
            pedagogy = {
                "why": "Aucune injection detectee. Le texte semble securise.",
                "recommendation": (
                    "Continue a scanner regulierement — les attaques evoluent."
                ),
            }

        # Feed Learning Engine
        for f in findings_list:
            record_safe(None, "injection", {"category": f["category"]})

        return {
            "status": status,
            "scan_mode": scan_mode,
            "findings": findings_list,
            "injection_count": len(findings),
            "categories_found": categories_found,
            "pedagogy": pedagogy,
        }

    except Exception:
        logger.exception("shield_prompt error")
        return {
            "status": "error",
            "error": "Internal error. Check server logs.",
            "findings": [],
            "categories_found": [],
            "pedagogy": _NO_INPUT_PEDAGOGY,
        }
