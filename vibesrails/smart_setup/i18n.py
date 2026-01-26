"""
vibesrails Smart Setup - Internationalization (i18n).

Language detection and message translations.
"""

import os

# =============================================================================
# LANGUAGE DETECTION
# =============================================================================


def detect_language() -> str:
    """Detect user language from environment. Default: English."""
    lang = os.environ.get("LANG", "").lower()
    lang_var = os.environ.get("LANGUAGE", "").lower()
    # Check for French
    if lang.startswith("fr") or lang_var.startswith("fr"):
        return "fr"
    return "en"


LANG = detect_language()


# =============================================================================
# MESSAGE TRANSLATIONS
# =============================================================================

MESSAGES = {
    "en": {
        "smart_setup": "VibesRails Smart Setup",
        "analyzing": "Analyzing",
        "project_analysis": "Project analysis:",
        "detected_types": "Detected type(s)",
        "generic_python": "Generic Python",
        "packs_to_include": "Packs to include",
        "existing_configs": "Existing configs",
        "secret_patterns_detected": "! Secret patterns detected in code",
        "env_files": ".env files",
        "config_exists": "vibesrails.yaml already exists",
        "overwrite_config": "Overwrite existing configuration?",
        "setup_cancelled": "Setup cancelled",
        "use_force": "Use --force to overwrite",
        "config_mode": "Configuration mode:",
        "mode_simple": "Simple (recommended) - I'll guide you, no regex knowledge needed",
        "mode_advanced": "Advanced - Enter regex patterns yourself",
        "mode_skip": "Skip - Use default config",
        "choice": "Choice",
        "proposed_config": "Proposed configuration:",
        "create_config": "Create vibesrails.yaml and install hook?",
        "created": "Created",
        "updated": "Updated",
        "install_hooks": "Install Claude Code hooks (advanced integration)?",
        "hooks_not_available": "Hooks not available in this installation",
        "setup_complete": "Smart Setup complete!",
        "files_created": "Files created",
        "config_file": "configuration",
        "auto_scan": "automatic scan",
        "claude_instructions": "Claude Code instructions",
        "claude_hooks": "Claude Code integration",
        "next_steps": "Next steps",
        "commit_normally": "Commit normally - vibesrails scans automatically",
        "scan_all": "To scan everything",
        # Vibe coder messages
        "protection_mode": "=== Code Protection (simple mode) ===",
        "analyzing_project": "Analyzing project...",
        "found_secrets": "I found {count} potential secret(s):",
        "no_secrets_found": "No secrets detected in code",
        "enable_protection": "Enable protection for these categories?",
        "protections_enabled": "Protections enabled",
        "additional_protections": "Additional protections available:",
        "none": "None",
        "add_protections": "Add protections (comma-separated numbers, or 0)",
        "custom_protection": "Custom protection (natural language):",
        "examples": "Examples",
        "empty_to_finish": "(empty to finish)",
        "what_to_protect": "What do you want to protect?",
        "will_block": "I will block",
        "confirm": "Confirm?",
        "added": "Added",
        "not_understood": "I didn't understand. Try with a specific value in quotes.",
        "example": "Example",
        "pattern_ignored": "Pattern ignored",
        # Regex validation
        "invalid_regex": "Invalid regex",
        "dangerous_regex": "Potentially dangerous regex (ReDoS)",
        "preview_matches": "Preview of matches ({count} found):",
        "no_matches": "No matches found in current project",
        "add_pattern": "Add this pattern?",
        "regex_to_block": "Regex to block (or Enter)",
        "error_message": "Error message",
        "forbidden_pattern": "Forbidden pattern",
        "additional_patterns": "Additional patterns?",
        "custom_patterns": "Add custom patterns?",
        # Architecture messages
        "arch_detected": "Architecture detected",
        "arch_layers": "layers",
        "arch_suggest": "Enable architecture checking (import-linter)?",
        "arch_install_cmd": "Install command",
        "arch_config_created": "Architecture config created",
        "arch_simple_project": "Simple project - architecture check not needed",
        "arch_tool_missing": "Architecture tool not installed (optional)",
        "arch_will_check": "Pre-commit will check: security + architecture",
    },
    "fr": {
        "smart_setup": "VibesRails Smart Setup",
        "analyzing": "Analyse",
        "project_analysis": "Analyse du projet:",
        "detected_types": "Type(s) detecte(s)",
        "generic_python": "Python generique",
        "packs_to_include": "Packs a inclure",
        "existing_configs": "Configs existants",
        "secret_patterns_detected": "! Patterns de secrets detectes dans le code",
        "env_files": "Fichiers .env",
        "config_exists": "vibesrails.yaml existe deja",
        "overwrite_config": "Ecraser la configuration existante?",
        "setup_cancelled": "Setup annule",
        "use_force": "Utilisez --force pour ecraser",
        "config_mode": "Mode de configuration:",
        "mode_simple": "Simple (recommande) - Je te guide, pas besoin de connaitre les regex",
        "mode_advanced": "Avance - Tu entres les regex toi-meme",
        "mode_skip": "Passer - Utiliser la config par defaut",
        "choice": "Choix",
        "proposed_config": "Configuration proposee:",
        "create_config": "Creer vibesrails.yaml et installer le hook?",
        "created": "Cree",
        "updated": "Mis a jour",
        "install_hooks": "Installer les hooks Claude Code (integration avancee)?",
        "hooks_not_available": "Hooks non disponibles dans cette installation",
        "setup_complete": "Smart Setup termine!",
        "files_created": "Fichiers crees",
        "config_file": "configuration",
        "auto_scan": "scan automatique",
        "claude_instructions": "instructions Claude Code",
        "claude_hooks": "integration Claude Code",
        "next_steps": "Prochaines etapes",
        "commit_normally": "Commitez normalement - vibesrails scanne automatiquement",
        "scan_all": "Pour scanner tout",
        # Vibe coder messages
        "protection_mode": "=== Protection du code (mode simple) ===",
        "analyzing_project": "Analyse du projet...",
        "found_secrets": "J'ai trouve {count} secret(s) potentiel(s):",
        "no_secrets_found": "Aucun secret detecte dans le code",
        "enable_protection": "Activer la protection pour ces categories?",
        "protections_enabled": "Protections activees",
        "additional_protections": "Protections supplementaires disponibles:",
        "none": "Aucune",
        "add_protections": "Ajouter des protections (numeros separes par virgule, ou 0)",
        "custom_protection": "Protection personnalisee (langage naturel):",
        "examples": "Exemples",
        "empty_to_finish": "(Entree vide pour terminer)",
        "what_to_protect": "Que veux-tu proteger?",
        "will_block": "Je vais bloquer",
        "confirm": "Confirmer?",
        "added": "Ajoute",
        "not_understood": "Je n'ai pas compris. Essaie avec une valeur precise entre guillemets.",
        "example": "Exemple",
        "pattern_ignored": "Pattern ignore",
        # Regex validation
        "invalid_regex": "Regex invalide",
        "dangerous_regex": "Regex potentiellement dangereuse (ReDoS)",
        "preview_matches": "Apercu des matches ({count} trouve(s)):",
        "no_matches": "Aucun match trouve dans le projet actuel",
        "add_pattern": "Ajouter ce pattern?",
        "regex_to_block": "Regex a bloquer (ou Entree)",
        "error_message": "Message d'erreur",
        "forbidden_pattern": "Pattern interdit",
        "additional_patterns": "Patterns additionnels?",
        "custom_patterns": "Ajouter des patterns personnalises?",
        # Architecture messages
        "arch_detected": "Architecture detectee",
        "arch_layers": "couches",
        "arch_suggest": "Activer la verification d'architecture (import-linter)?",
        "arch_install_cmd": "Commande d'installation",
        "arch_config_created": "Config architecture creee",
        "arch_simple_project": "Projet simple - verification architecture non necessaire",
        "arch_tool_missing": "Outil architecture non installe (optionnel)",
        "arch_will_check": "Pre-commit verifiera: securite + architecture",
    },
}


def msg(key: str, **kwargs) -> str:
    """Get translated message."""
    text = MESSAGES.get(LANG, MESSAGES["en"]).get(key, key)
    if kwargs:
        return text.format(**kwargs)
    return text
