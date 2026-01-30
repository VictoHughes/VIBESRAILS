# VibesRails - Project Vision

> **North Star Document** - The unchanging vision that guides all decisions

**Last Updated:** 2026-01-26
**Version:** 1.0
**Status:** Active

---

## Why This Document Exists

Every project faces drift:
- Feature bloat (adding "just one more thing")
- Architecture erosion (quick hacks that stay forever)
- Mission creep (becoming something you didn't intend)

**VISION.md is the anchor.**

When in doubt, return here.
When tempted to deviate, read this first.
When lost, this is your map.

---

## Vision Statement

**What:** Security scanner that preserves developer flow state

**Why:** Developers shouldn't choose between speed and security. Flow state (vibes coding) is where the best work happens. Traditional security tools interrupt this flow. VibesRails protects you *silently*.

**For Whom:** Developers who code fast (especially with AI tools like Claude Code, Cursor, Copilot)

**How:** Pre-commit scanning with zero configuration. Blocks disasters, allows creativity.

**Success Looks Like:** Developers forget VibesRails exists (until it saves them from a production disaster)

---

## Core Principles (Immutable)

These never change. If a feature violates these, we don't build it.

### 1. Preserve Flow State
```
❌ DON'T: Interrupt during coding
✅ DO: Scan at commit (natural breakpoint)

❌ DON'T: Require manual configuration
✅ DO: Smart defaults that just work

❌ DON'T: Noisy false positives
✅ DO: High-confidence patterns only
```

**Test:** Would this interrupt a developer in flow? If yes, reject.

---

### 2. Security Without Compromise
```
❌ DON'T: Allow "skip this scan" buttons
✅ DO: Force fix or explicit ignore

❌ DON'T: Warning fatigue (too many warnings)
✅ DO: BLOCK real risks, WARN style issues

❌ DON'T: Post-commit detection
✅ DO: Pre-commit prevention
```

**Test:** Would this allow a secret to reach production? If yes, reject.

---

### 3. Developer Experience First
```
❌ DON'T: Enterprise-first features
✅ DO: Developer-first, enterprise-compatible

❌ DON'T: Complex UIs and dashboards
✅ DO: CLI-first, UI optional

❌ DON'T: Subscription required for core
✅ DO: Core forever free, Pro optional
```

**Test:** Would a solo indie hacker find this useful? If no, reconsider.

---

### 4. Transparent & Open
```
❌ DON'T: Proprietary pattern formats
✅ DO: YAML configs anyone can read

❌ DON'T: Black-box scanning
✅ DO: Show exactly what matched

❌ DON'T: Closed-source core
✅ DO: MIT license, public repo
```

**Test:** Can users understand and extend this? If no, simplify.

---

### 5. AI-Friendly by Design
```
❌ DON'T: Ignore AI coding era
✅ DO: Claude Code / Cursor integration

❌ DON'T: Treat AI code differently
✅ DO: Same standards, stricter in Guardian mode

❌ DON'T: Fight against AI tools
✅ DO: Complement them (guardrails)
```

**Test:** Does this help developers using AI? If no, question value.

---

## Architecture Conceptual

Not implementation details (those go in `/docs/architecture/`), but the **mental model**.

### The Stack (Conceptual Layers)

```
┌─────────────────────────────────────┐
│  Developer Experience               │  ← User sees this
│  - CLI (vibesrails command)         │
│  - Git hooks (invisible)            │
│  - CLAUDE.md (instructions)         │
└─────────────────────────────────────┘
           │
┌─────────────────────────────────────┐
│  Intelligence Layer                 │  ← Decisions
│  - Smart setup (project detection)  │
│  - Guardian mode (AI detection)     │
│  - Pattern learning (optional)      │
└─────────────────────────────────────┘
           │
┌─────────────────────────────────────┐
│  Scanning Engine                    │  ← Core logic
│  - Regex matcher (fast, reliable)   │
│  - Config loader (vibesrails.yaml)  │
│  - Result formatter                 │
└─────────────────────────────────────┘
           │
┌─────────────────────────────────────┐
│  Foundation                         │  ← Always free
│  - 100% local execution             │
│  - No telemetry                     │
│  - MIT license                      │
└─────────────────────────────────────┘
```

**Key Architectural Decisions:**

1. **Regex-based scanning** (not AST)
   - Why: Faster, simpler, language-agnostic
   - Trade-off: Some false positives
   - Decision: Accept trade-off for speed

2. **Local-first** (not cloud-based)
   - Why: Privacy, speed, no accounts
   - Trade-off: No cross-machine state
   - Decision: Cloud optional (Pro feature)

3. **Git hook integration** (not CI-only)
   - Why: Catch issues before push
   - Trade-off: Requires local install
   - Decision: Worth it for developer experience

4. **YAML config** (not code)
   - Why: Non-programmers can read/edit
   - Trade-off: Less flexible than code
   - Decision: Flexibility via custom patterns

---

## Success Criteria

### Quantitative

**By Month 6:**
- 1,000+ GitHub stars
- 100+ weekly active users
- 10+ sponsors
- 0 critical bugs

**By Year 1:**
- 5,000+ stars
- 500+ weekly active users
- $5,000/month revenue
- 3+ enterprise customers

**By Year 3:**
- 20,000+ stars
- 5,000+ weekly active users
- $50,000/month revenue
- Recognized brand in dev tools

### Qualitative

**We know we've succeeded when:**

1. **Developers forget it exists** (until it saves them)
   - "VibesRails just blocked my AWS key. Forgot it was even running."

2. **It becomes a default** (like pytest, black)
   - "Of course we use VibesRails. Everyone does."

3. **Flow state preserved** (no complaints about interruptions)
   - "I code just as fast, but safer."

4. **Community-driven** (users contribute patterns)
   - "Someone already made a pattern for my framework!"

5. **Trusted for security** (not just convenience)
   - "Our security audit passed because of VibesRails."

---

## Anti-Patterns (What We Will NOT Become)

### ❌ Feature Bloat

**Don't become:**
- "Swiss army knife" security platform
- Dashboard-first tool
- Configuration hell

**Instead:**
- One thing well: pre-commit security
- CLI-first always
- Smart defaults

**Test:** Can a new user understand all features in 5 minutes? If no, cut features.

---

### ❌ Enterprise-First Pivot

**Don't become:**
- Sales-driven roadmap
- Features only for paying customers
- Forget indie developers

**Instead:**
- Core always free
- Enterprise features = convenience, not capabilities
- Indie devs are our heart

**Test:** Would this require enterprise subscription? If yes, reconsider.

---

### ❌ Proprietary Lock-In

**Don't become:**
- Proprietary pattern format
- Cloud-only features
- Vendor lock-in

**Instead:**
- YAML stays standard
- Local-first always
- Export/migrate friendly

**Test:** Can users leave easily? If no, redesign.

---

### ❌ False Positive Hell

**Don't become:**
- Cry-wolf scanner
- Too strict (developers bypass it)
- Too loose (misses real issues)

**Instead:**
- High-confidence patterns
- Easy suppression (with comment)
- Community feedback loop

**Test:** Would you ignore this warning? If yes, remove pattern.

---

### ❌ Complexity Creep

**Don't become:**
- Requires configuration expert
- Needs training to use
- Documentation taller than code

**Instead:**
- `vibesrails --setup` is all you need
- Docs = quick reference, not bible
- Simplicity is a feature

**Test:** Can a junior dev set up in 5 minutes? If no, simplify.

---

## Decision Framework

When facing a choice, use this hierarchy:

### Level 1: Does it violate Core Principles?
- If YES → Reject immediately
- If NO → Continue to Level 2

### Level 2: Does it preserve flow state?
- If NO → Reject or redesign
- If YES → Continue to Level 3

### Level 3: Is it simple?
- If NO → Can we simplify?
- If can't simplify → Probably wrong feature
- If YES → Continue to Level 4

### Level 4: Is it free in core?
- If NO → Move to Pro tier (if value-add)
- If YES → Continue to Level 5

### Level 5: Does it scale?
- Will this work at 10x users?
- Will this work at 100x patterns?
- If NO → Redesign architecture
- If YES → Build it

### Example Decision: "Add Dashboard UI"

```
Level 1: Core Principles?
  → Doesn't violate (UI is optional)

Level 2: Flow state?
  → CLI-first stays, dashboard is optional → YES

Level 3: Simple?
  → Dashboard adds complexity
  → Can we simplify? → Make it Pro feature

Level 4: Free in core?
  → NO (dashboard is Pro) → OK for Pro tier

Level 5: Scale?
  → YES (standard web app)

DECISION: ✅ Build dashboard as Pro feature
```

---

## Roadmap Alignment

Every feature must map to the vision.

### Phase 1: Foundation (Current)
**Goal:** Be the best pre-commit security scanner

Features:
- ✅ Smart setup
- ✅ Pre-commit hooks
- ✅ Claude Code integration
- ✅ Guardian mode

**Vision Alignment:** Core security + flow preservation

---

### Phase 2: Ecosystem (Months 3-6)
**Goal:** Community patterns & integrations

Features:
- Pattern marketplace
- More framework integrations
- Team config sharing

**Vision Alignment:** Community-driven, extensible

---

### Phase 3: Intelligence (Months 6-12)
**Goal:** Smarter pattern learning

Features:
- AI pattern discovery (unlimited)
- Analytics dashboard (Pro)
- Trend detection

**Vision Alignment:** AI-friendly, developer insights

---

### Phase 4: Enterprise (Year 2)
**Goal:** Work at any scale

Features:
- Self-hosted option
- SSO integration
- Compliance reports

**Vision Alignment:** Enterprise-compatible, not enterprise-first

---

## Living Document

This vision is **living but stable**.

### When to Update

**YES, update when:**
- Market fundamentally changes
- User research reveals wrong assumptions
- Technology breakthrough (e.g., AST parsing 10x faster)
- Team consensus on pivot

**NO, don't update for:**
- Feature requests
- Competitive pressure
- Revenue optimization
- Investor pressure

### Update Process

1. Propose change in GitHub issue
2. Team discussion (1 week minimum)
3. User feedback (if major change)
4. Vote (consensus required)
5. Update document + version bump
6. Announce to community

**Version History:**
- v1.0 (2026-01-26) - Initial vision

---

## How VibesRails Uses This Document

### During Development

**Before adding a feature:**
```bash
# Developer reads VISION.md
# Asks: "Does this align with Core Principles?"
# If uncertain, discuss in GitHub issue
```

**During PR review:**
```bash
# Reviewer checks:
# - Does this preserve flow state?
# - Is it simple?
# - Does it align with vision?
```

---

### For Users (Future Feature)

**`vibesrails --vision` command:**
```bash
$ vibesrails --vision

📖 VibesRails Vision

Mission: Security that preserves flow state

Core Principles:
1. Preserve flow state
2. Security without compromise
3. Developer experience first
4. Transparent & open
5. AI-friendly by design

Read full vision: VISION.md
```

**Smart Setup Integration (Future):**
```bash
$ vibesrails --setup

📋 Analyzing your project...

💡 Want to define your project vision first?
   This helps VibesRails configure patterns that align with your goals.

   [Y] Create VISION.md (guided)
   [n] Skip (use defaults)
```

---

### For AI Assistants (Claude, Cursor, etc.)

**CLAUDE.md references VISION.md:**
```markdown
## Project Vision

Read VISION.md before making architectural decisions.

Key principles:
1. Preserve flow state
2. Security without compromise
3. [etc.]

When suggesting features, verify alignment with VISION.md
```

---

## Drift Detection (Future Feature)

**VibesRails could detect when project drifts from vision:**

```bash
$ vibesrails --check-vision

🔍 Checking alignment with VISION.md...

⚠️  Potential drift detected:

1. vibesrails.yaml has 50+ patterns
   Vision: "High-confidence patterns only"
   Suggestion: Review patterns, keep only essential

2. Multiple --skip-scan usages detected (5 in last 10 commits)
   Vision: "Force fix or explicit ignore"
   Suggestion: Fix issues instead of skipping

✅ Overall: 90% aligned with vision
```

---

## Questions to Ask Yourself

When contributing to VibesRails:

### Before Adding a Feature

1. Does this preserve flow state?
2. Would I use this myself?
3. Is it simple enough to explain in one sentence?
4. Does it belong in core or Pro?
5. Will users understand it immediately?

### When Reviewing Code

1. Does this code reflect our values?
2. Is it as simple as it could be?
3. Does it respect user privacy?
4. Would this scale?
5. Is it testable?

### When Making Business Decisions

1. Does this help developers or just make money?
2. Would we do this if we were bootstrapping forever?
3. Are we staying true to open source?
4. Would our users approve?
5. Can we reverse this decision later?

---

## The North Star

When lost, remember:

**We build tools that preserve flow state while keeping code secure.**

Everything else is details.

---

**VISION.md - Keep the vibes alive 🛤️**

*KIONOS™ - The vibes development company*
*A.B.H.A.M.H*
