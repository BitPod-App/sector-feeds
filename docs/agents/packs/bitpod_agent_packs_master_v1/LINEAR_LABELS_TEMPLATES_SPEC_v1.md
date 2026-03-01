# LINEAR_LABELS_TEMPLATES_SPEC_v1

Status: DRAFT  
Owner: CJ  
Last updated: 2026-02-28  
Purpose: Copy/paste spec for Linear labels + templates (Week 1).  
Note: This is intentionally minimal. Expand only when repeated friction forces it.

---

## Label groups (recommended)

### Group: Type
- 🐞 Bug
- ⭐️ Feature
- ⚙️ Chore
- 🎨 Design *(future-heavy; optional Week 1)*

### Group: Domain
- PM
- QA
- Eng

### Group: Blocked
- 🛑 Needs-PM
- 🛑 Needs-Discussion
- 🛑 Blocked

### Group: PM Review
- Accepted
- Rejected

---

## Optional “severity” (only if you need it in Week 1)
Group: Severity
- P0 (production down / data loss)
- P1 (core feature broken)
- P2 (major annoyance)
- P3 (minor / polish)

If you add severity, also add a rule: “Only for Bugs.”

---

## Templates

### Template: Feature

**Title pattern**
`⭐️ <verb> <object> (short)`

**Body**
**Problem**
-

**Scope**
In:
-

Out:
-

**Acceptance Criteria**
- [ ]

**Dependencies**
-

**QA Notes**
- What to verify:
- Edge cases:

**Gate / Approval**
- (If needed) CJ approval required for:
  -

---

### Template: Bug

**Title pattern**
`🐞 <what is broken> — <where>`

**Body**
**Repro Steps**
1)
2)
3)

**Expected**
-

**Actual**
-

**Environment**
- device:
- OS:
- app version / build:
- browser (if applicable):
- logs/screenshots:

**Severity**
- (optional) P0/P1/P2/P3

**Notes**
-
