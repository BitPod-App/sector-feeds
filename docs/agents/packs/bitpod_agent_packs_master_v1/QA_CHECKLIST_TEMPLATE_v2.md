# QA_CHECKLIST_TEMPLATE_v2

Status: ACTIVE  
Owner: Vera (QA)  
Last updated: 2026-03-05  
Purpose: Regression-first QA checklist for Linear issues and verification reports, with evidence-backed READY decisions and changelists for Taylor release notes.

---

## 0) Decision rubric (pick one)

- [ ] **READY**
- [ ] **READY_WITH_FOLLOWUPS**
- [ ] **NOT_READY**

Rationale (1–3 lines):
-

---

## 1) Environment

- build/version:
- platform/device:
- OS/browser:
- account/state assumptions:
- logs/screenshots links:

---

## 2) Regression testing (always)

Baseline rule: **Vera always runs regression tests.** Depth depends on change size.

- Scope of regression for this ticket:
  - [ ] minimal (related area only)
  - [ ] medium (related flows + nearby dependencies)
  - [ ] full release sweep (everything still works)

Regression notes (what was covered):
-

---

## 3) Critical acceptance criteria evidence (required)

Rule: For each **critical** acceptance criterion, include **PASS evidence** *or* **1 reproducible failure**.

### AC-1 (critical): <paste criterion>
**PASS evidence**
- Steps:
- Observed:
OR  
**Reproducible failure**
- Steps:
- Expected:
- Actual:
- Notes/logs:

### AC-2 (critical): <paste criterion>
(Repeat)

---

## 4) Non-critical checks (optional but recommended)

- edge case notes:
- accessibility checks:
- copywriting / UX notes:

---

## 5) Changelist for Taylor (for release notes)

Short, factual list of user-visible changes (no marketing voice; Taylor will rephrase):
-

---

## 6) Follow-ups (if READY_WITH_FOLLOWUPS or NOT_READY)

Create/Link tickets:
- [ ] **BUGS**
- [ ] **Unexpected behavior**
- [ ] **UI/UX issues**
- [ ] **Copy issues** (optional)

---

## 7) Special situations (use when relevant)

### A) Post-QA regression breaks a key feature (AC-1 critical clause)
If something breaks after QA passed, add a short postmortem note:
- What I missed:
- What I learned:
- Process improvement (method):
- Recommendation to avoid rushing (product/marketing/process):

### B) Customer downtime not easily reproducible (AC-2 urgent clause)
- Signal summary (who/what/when):
- Hypotheses ranked (likelihood × blast radius):
- Minimal repro strategy:
- Required logs/telemetry:
- Containment recommendation:
