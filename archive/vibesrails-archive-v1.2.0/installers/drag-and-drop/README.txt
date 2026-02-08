VibesRails - Security for Claude Code
=====================================

INSTALLATION:

1. Ouvre le Terminal
2. cd dans ton projet:  cd /chemin/vers/ton/projet
3. Lance:               bash /chemin/vers/ce-dossier/install.sh

C'est tout. Ouvre Claude Code, c'est actif.

PRE-REQUIS:
- Python 3 (deja installe sur Mac)
- Claude Code

CE QUE CA FAIT:
- Bloque les secrets AVANT que Claude les ecrive
- Bloque les injections SQL
- Scanne chaque commit automatiquement
- Empeche Claude de desactiver ses propres gardes

COMMANDES:
  vibesrails --all    # Scanner le projet
  vibesrails --setup  # Reconfigurer
  vibesrails --show   # Voir les patterns
