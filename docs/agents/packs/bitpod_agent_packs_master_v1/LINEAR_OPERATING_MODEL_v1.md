# LINEAR_OPERATING_MODEL_v1

Status: ACTIVE  
Owner: CJ  
Last updated: 2026-02-28  
Purpose: Linear is the operating console. This document defines how we use it.  
Tone: Practical. Light. No process cosplay.

**Guiding protocol:** `personal-preferences-interactions.md` is the recommended interaction baseline with CJ. Treat it as the default unless a specific task requires a different format.

---

## What Linear is for
- Intake: ideas/bugs/feedback → trackable work
- Triage: priority + sequencing + scope control
- Execution: ownership, status, coordination
- QA: verification + bug capture
- Non-code work: planning, ops, releases

## What Linear is NOT for
- Secrets (tokens, keys, DSNs, credentials)
- Canonical technical truth (that lives in GitHub)

---

## Week 1 minimum labels

Type:
- 🐞 Bug
- ⭐️ Feature
- ⚙️ Chore
- 🎨 Design (rare in Week 1)

Domain:
- PM
- QA
- Eng

Blocked:
- 🛑 Needs-PM
- 🛑 Needs-Discussion
- 🛑 Blocked

PM Review:
- Accepted
- Rejected

Rule: Keep taxonomy small. Add labels only when repeated friction forces it.

---

## Templates

### Feature template (minimum)
- Problem
- Scope (In / Out)
- Acceptance criteria (checklist)
- Dependencies
- QA notes (what to verify)

### Bug template (minimum)
- Repro steps
- Expected / Actual
- Environment
- Logs / Screenshots
- Severity + impact

---

## Ownership
- Taylor owns triage + priority + scope.
- QA (Vera) owns verification and bug quality.
- Eng agents (Atlas, Solder, Jake, Frank) own implementation.

---

## Change control (Linear schema)
Additive-first:
- Create new label/status/template → migrate usage → optional cleanup.

Destructive changes require:
- A short **Change Proposal** artifact (with rollback notes).

---

## Weekly ritual (15–30 min)
- Stale issues sweep
- Missing acceptance criteria sweep
- Duplicate label sweep
- “Blocked” sweep (convert to decisions or close)
