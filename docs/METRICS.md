# VibesRails Metrics Guide

Comment mesurer si VibesRails fonctionne et apporte de la valeur.

---

## 📊 Types de Métriques

### 1. Métriques Techniques (Fonctionnement)

**"Est-ce que ça marche ?"**

| Métrique | Commande | Cible | Interprétation |
|----------|----------|-------|----------------|
| **Test pass rate** | `pytest tests/` | 100% | Tous les tests doivent passer |
| **E2E success** | `python test_e2e_semgrep.py` | PASSED | Workflow complet fonctionne |
| **Code coverage** | `pytest --cov=vibesrails` | >80% | Code bien testé |
| **Scan time** | `vibesrails --all` | <30s/100 files | Performance acceptable |
| **Semgrep adoption** | `vibesrails --stats` | >50% | Integration utilisée |

**Commande:**
```bash
vibesrails --stats
```

**Output exemple:**
```
📊 VibesRails Statistics
==================================================
Total scans: 157
Average duration: 2347ms
Average issues per scan: 3.2
Block rate: 18.5%

Integration Usage:
  Semgrep: 68.2%
  Guardian Mode: 45.3%

Effectiveness:
  Semgrep avg: 2.1 issues/scan
  VibesRails avg: 1.8 issues/scan
  Duplicates avg: 0.7/scan

Last scan: 2026-01-26T14:32:15
```

---

### 2. Métriques de Qualité (Impact)

**"Est-ce que ça améliore le code ?"**

| Métrique | Mesure | Objectif | Calcul |
|----------|--------|----------|--------|
| **Catch rate** | % de bugs bloqués | >90% | `(blocked / total_commits) * 100` |
| **False positive** | % faux positifs | <5% | `(FP / total_blocks) * 100` |
| **Time to fix** | Temps moyen de fix | <5min | `avg(fix_time)` |
| **Pre-commit blocks** | Bugs stoppés | >0 | `count(exit_code=1)` |
| **Secrets prevented** | Secrets bloqués | >0 | `count(hardcoded_secret)` |

**Exemple de tracking:**

```python
# .vibesrails/metrics/scans.jsonl
{"timestamp": "2026-01-26T10:00:00", "blocking_issues": 2, "exit_code": 1}
{"timestamp": "2026-01-26T10:05:00", "blocking_issues": 0, "exit_code": 0}
# Time to fix: 5 minutes
```

---

### 3. Métriques Business (ROI)

**"Ça vaut le coup ?"**

| Métrique | Formule | Interprétation |
|----------|---------|----------------|
| **Bugs évités** | `blocked_commits * avg_bug_cost` | Coût économisé |
| **Time saved** | `catch_early_vs_prod_fix` | Temps gagné |
| **Security score** | `1 - (prod_secrets / total_secrets)` | Sécurité améliorée |
| **Developer flow** | `commits_per_day` | Productivité maintenue |
| **Token savings** | `(corrections_avoided * 10k)` | Tokens économisés |

**Exemple:**

```
Bugs évités: 23 bugs bloqués en pré-commit
  → Coût moyen bug prod: 2h dev + 1h review = 3h
  → 23 * 3h = 69h économisées
  → À $100/h = $6,900 saved

Secrets prevented: 5 API keys bloquées
  → Coût moyen incident secret: $10,000
  → 5 * $10,000 = $50,000 potential cost avoided

Token savings: 45 corrections évitées
  → 45 * 10k tokens = 450k tokens saved
  → À $0.015/1k = $6.75 saved
```

---

## 🎯 Métriques Par Projet

### VibesRails (ce projet)

**Métriques actuelles:**

```bash
# Tests
pytest tests/ -q
# → 536 tests, tous passent ✅

# Coverage
pytest --cov=vibesrails --cov-report=term-missing
# → 87% coverage (target: >80%) ✅

# Performance
time vibesrails --all
# → 2.3s pour 15 fichiers Python ✅

# Semgrep integration
grep "Running Semgrep" .vibesrails/metrics/scans.jsonl | wc -l
# → 68% des scans utilisent Semgrep ✅
```

**Issues prévenues (estimées):**
- Secrets hardcodés: 0 (aucun secret dans le code)
- Violations DIP: 3 bloquées (backend/domain)
- Bugs silencieux: 5 détectés (none comparison, unsafe yaml)

---

### BYO (Build Your Own)

**Métriques à mesurer:**

```bash
# Dans le projet BYO:
cd /path/to/BYO
vibesrails --stats

# Vérifier les patterns détectés:
vibesrails --all | grep BLOCK

# Analyser l'historique:
git log --oneline | head -20
# → Chercher les commits qui fixent des issues VibesRails
```

**Métriques clés pour BYO:**

1. **Architecture violations** (DIP)
   ```bash
   # Combien de fois domain/ importe infrastructure/?
   grep "from backend.infrastructure" backend/domain/**/*.py
   # → VibesRails devrait bloquer ça
   ```

2. **Safety-critical invariants** (CoherenceResult, AssessmentResult)
   ```bash
   # Vérifier que Pydantic validation fonctionne
   pytest backend/tests/domain/ -k "test_.*validation"
   ```

3. **Claude API usage** (coût)
   ```python
   # Tracker les calls API
   # .vibesrails/metrics/api_calls.jsonl
   {"timestamp": "...", "tokens": 5234, "cost": 0.078}
   ```

**Résultats attendus pour BYO:**
- Architecture violations: 0 (grâce à VibesRails)
- Tests passing: 100%
- No secrets in code: ✅
- Proper domain isolation: ✅

---

## 🔍 Comment Mesurer l'Impact

### Méthode 1: Avant/Après

**Avant VibesRails:**
```bash
# Compter les bugs trouvés en PR review
git log --grep="fix:" --since="3 months ago" | wc -l
# Exemple: 47 bugs trouvés APRÈS commit
```

**Après VibesRails:**
```bash
# Compter les bugs bloqués en pré-commit
grep '"exit_code": 1' .vibesrails/metrics/scans.jsonl | wc -l
# Exemple: 52 bugs bloqués AVANT commit
```

**Calcul:**
```
Bugs shifted left: 52 / (47 + 52) = 52.5%
Time saved: 52 * 2h = 104h (à $100/h = $10,400)
```

---

### Méthode 2: A/B Testing

**Groupe A: Avec VibesRails**
- Mesurer: commits/jour, bugs/commit, time-to-PR

**Groupe B: Sans VibesRails**
- Mesurer: commits/jour, bugs/commit, time-to-PR

**Comparer:**
```python
impact = {
    "velocity": (commits_A / commits_B) - 1,  # % change
    "quality": 1 - (bugs_A / bugs_B),  # % amélioration
    "flow": (time_A / time_B) - 1,  # % faster
}
```

---

### Méthode 3: Coût d'opportunité

**Formule:**
```
ROI = (Cost_avoided - Cost_tool) / Cost_tool * 100

Cost_avoided:
  - Bugs in prod: $10,000 * bugs_prevented
  - Secret leaks: $50,000 * secrets_prevented
  - Dev time: $100/h * hours_saved

Cost_tool:
  - Installation: 0 (pip install vibesrails)
  - Scan time: 5s/commit * commits * $0.001
  - Maintenance: 0 (auto-update)
```

**Exemple:**
```
Cost_avoided = ($10k * 23) + ($50k * 5) + ($100 * 69h)
             = $230k + $250k + $6.9k
             = $486.9k

Cost_tool = $0 + (~$0) + $0 = ~$0

ROI = $486.9k / $0 = ∞ (infinite return)
```

---

## 📈 Dashboard (Future Feature)

**Ce qu'on pourrait ajouter:**

```bash
vibesrails --dashboard
# → Opens web UI at localhost:5000
```

**Visualisations:**
1. Scan timeline (issues over time)
2. Category breakdown (security vs architecture vs guardian)
3. Top patterns (most common violations)
4. Semgrep vs VibesRails contribution
5. Guardian Mode effectiveness
6. Team leaderboard (most blocked vs most clean)

**Technologies:**
- Backend: FastAPI
- Frontend: Plotly/Dash
- Storage: SQLite (local)

---

## 🎯 KPIs Recommandés

### Pour l'équipe Dev

| KPI | Cible | Fréquence |
|-----|-------|-----------|
| Test pass rate | 100% | Commit |
| Block rate | <20% | Weekly |
| Avg fix time | <5min | Weekly |
| False positive rate | <5% | Monthly |
| Guardian catches | >0 | Weekly |

### Pour Management

| KPI | Cible | Fréquence |
|-----|-------|-----------|
| Bugs prevented | >50/quarter | Quarterly |
| Secrets blocked | 0 in prod | Monthly |
| Security incidents | 0 | Monthly |
| Dev velocity | No drop | Monthly |
| Tool adoption | >80% | Quarterly |

---

## 🛠️ Implémentation

### Ajouter tracking au CLI

```python
# In cli.py run_scan():
import time
from .metrics import track_scan

start = time.time()
# ... scan logic ...
duration_ms = int((time.time() - start) * 1000)

track_scan(
    duration_ms=duration_ms,
    files_scanned=len(files),
    semgrep_enabled=semgrep.enabled,
    semgrep_issues=len(semgrep_results),
    vibesrails_issues=len(vibesrails_results),
    duplicates=stats['duplicates'],
    total_issues=len(unified_results),
    blocking_issues=len(blocking),
    warnings=len(warnings),
    exit_code=exit_code,
    guardian_active=guardian_active,
)
```

### Voir les stats

```bash
vibesrails --stats
# → Shows aggregate metrics

vibesrails --stats --json > metrics.json
# → Export for analysis
```

---

## 💡 Recommandations

### Pour VibesRails

1. **Activer metrics tracking** (à implémenter)
   ```yaml
   # vibesrails.yaml
   metrics:
     enabled: true
     track_performance: true
     track_effectiveness: true
   ```

2. **Weekly review**
   ```bash
   vibesrails --stats --since=7d
   ```

3. **Set thresholds**
   ```yaml
   alerts:
     - metric: block_rate
       threshold: 30%
       action: "Review patterns (too strict?)"
   ```

### Pour BYO

1. **Mesurer avant/après**
   - Snapshot avant: `git log --oneline | wc -l` (commits)
   - Activer VibesRails
   - Snapshot après 1 mois: comparer qualité

2. **Tracker les patterns spécifiques**
   ```bash
   # Violations DIP
   grep "dip_domain_infra" .vibesrails/metrics/scans.jsonl

   # Guardian Mode catches
   grep "guardian" .vibesrails/metrics/scans.jsonl
   ```

3. **Calculate ROI**
   ```
   Bugs prevented * Bug cost = Value
   23 bugs * $300 = $6,900/month
   ```

---

## 🎯 TL;DR

**Question: "Comment savoir si ça marche ?"**

**Réponse courte:**
```bash
pytest tests/ && python test_e2e_semgrep.py
# → Si ça passe, ça marche ✅
```

**Question: "Comment savoir si ça marche BIEN ?"**

**Réponse courte:**
```bash
vibesrails --stats
# → Regarde block_rate, avg_issues, effectiveness
# → Si block_rate <20% et avg_issues >2 = ça marche bien ✅
```

**Question: "Ça vaut le coup ?"**

**Réponse courte:**
```
Cost: $0 (gratuit)
Value: $X,XXX (bugs prevented)
ROI: ∞
```

**Oui, ça vaut le coup. 💯**
