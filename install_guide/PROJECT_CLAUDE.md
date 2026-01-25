# CLAUDE.md (à copier dans ton projet)

Copie ce fichier dans ton projet sous le nom `CLAUDE.md` pour que Claude Code sache utiliser vibesrails.

---

```markdown
# Instructions Claude Code

## Sécurité avec vibesrails

Ce projet utilise **vibesrails** pour la sécurité du code.

### Setup (si pas encore fait)

```bash
pip install vibesrails
vibesrails --setup
```

### Règles

1. **Ne jamais commiter de secrets** (API keys, passwords, tokens)
   - Utiliser `os.environ.get("VAR")` pour les credentials
   - Si vibesrails bloque, c'est qu'il y a un problème

2. **Si vibesrails bloque un faux positif**
   - Ajouter `# vibesrails: ignore` sur la ligne
   - Ou `# vibesrails: ignore [pattern_id]` pour un pattern spécifique

3. **Commandes utiles**
   ```bash
   vibesrails --all    # Scanner tout
   vibesrails --fix    # Auto-corriger
   vibesrails --show   # Voir patterns
   ```

### Guardian Mode

vibesrails détecte Claude Code et active le mode Guardian:
- Vérifications plus strictes
- Logging des blocks

### Configuration

Fichier: `vibesrails.yaml`
```
