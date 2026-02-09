POST-COMMIT CHECKPOINT

1. STOP — l'utilisateur a-t-il explicitement demande ce commit ?
2. Le prochain changement est dans le SCOPE declare ?
3. "audit"/"diagnostique" = LIRE seulement, 0 modification
4. "fix X" = tu fixes X, RIEN d'autre
5. 0 commit supplementaire sans validation humaine

En cas de doute -> DEMANDE avant de continuer.
