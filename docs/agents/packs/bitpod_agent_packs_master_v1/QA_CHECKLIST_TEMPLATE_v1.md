# QA_CHECKLIST_TEMPLATE_v1

Status: DRAFT  
Owner: Vera (QA)  
Last updated: 2026-02-28  
Purpose: Standard QA checklist format for Linear issues and verification reports.

---

## 1) Decision rubric (pick one)

- [ ] **READY**
- [ ] **READY_WITH_FOLLOWUPS**
- [ ] **NOT_READY**

Rationale (1–3 lines):
-

---

## 2) Environment

- build/version:
- platform/device:
- OS/browser:
- account/state assumptions:
- logs/screenshots links:

---

## 3) Critical acceptance criteria evidence (required)

Rule: For each **critical acceptance criterion**, include **PASS evidence** *or* **1 reproducible failure**.

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

## 4) Non-critical checks (optional)

- regression sanity sweep:
- edge case notes:
- performance/latency spot-check:
- accessibility spot-check:

---

## 5) Follow-ups (if READY_WITH_FOLLOWUPS)

Create/Link tickets:
- [ ] BUG:
- [ ] CHORE:
- [ ] UX:
