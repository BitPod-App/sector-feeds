# AGENT_OUTPUT_CONTRACTS_v1

Status: ACTIVE  
Owner: CJ  
Last updated: 2026-02-28  
Purpose: Standardize what “done” looks like across agents.  
Rule: Predictable artifacts > vibes.

**Guiding protocol:** `personal-preferences-interactions.md` is the recommended interaction baseline with CJ. Treat it as the default unless a specific task requires a different format.

---

## Artifact formats (minimum set)

All artifacts should be:
- Markdown
- Stored in GitHub (preferred) or attached/linked from Linear
- Named consistently, e.g.:
  - `/docs/agents/<agent>/<issue-id>_<artifact>.md`
  - Example: `/docs/agents/taylor/BITPOD-123_plan.md`

Artifacts (minimum):

### 1) `plan.md`
- Goal (1–2 lines)
- Approach (bullets)
- Dependencies
- Risks + mitigations
- Acceptance criteria (checklist)

### 2) `execution_notes.md`
- What was done
- What changed
- Links to PRs / commits / design refs
- Deviations from plan + why

### 3) `result.md`
- Outcome summary
- Verification summary
- Remaining issues / follow-ups
- Next recommended action

---

## Issue lifecycle contract (Linear)

Every issue should have:
- Owner agent (Taylor / QA / Eng A / Eng B)
- Type label (Bug / Feature / Chore / Design)
- Clear acceptance criteria (checklist)
- A “Gate” note if anything requires CJ approval

---

## Agent-specific contracts

### Taylor (Taylor)
Required:
- `plan.md` for all Features and Epics
- `triage_notes.md` for backlog grooming sessions (if decisions were made)
- `changelist.md` for release-note handoff from QA/Engineering outputs
Recommended:
- `weekly_operating_brief.md` (short)

### QA (Vera)
Required:
- `test_plan.md` for Features
- `verification_report.md` for items entering QA
- `bug_report.md` for failures (also file a Bug issue)
- `verification_report.md` must include decision rubric: `READY | READY_WITH_FOLLOWUPS | NOT_READY`
- For each critical acceptance criterion, QA must include PASS evidence or one reproducible failure.
Reference:
- `QA_CHECKLIST_TEMPLATE_v2.md`
- `VERA_PERSONA_PROFILE_v1.md`

### Engineer A/B/C/D (Atlas / Solder / Jake / Frank)
Required:
- `implementation_plan.md` (short) for Features
- PR link + test notes in `execution_notes.md`
- `result.md` including verification summary
- When applicable, include rollback or disable-switch notes for operational safety.
