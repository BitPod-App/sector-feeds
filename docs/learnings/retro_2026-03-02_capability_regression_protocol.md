# Retro (Mar 2, 2026)

## 1. What went well
- Early migration execution achieved high throughput when capability state was effectively full-access.
- Critical migration outcomes were delivered (org transfer, key rotation, cutover validation).

## 2. What went poorly
- A capability regression was not surfaced immediately.
- Work shifted to CJ-manual execution for too long, causing major throughput collapse.
- Confidence language did not clearly separate verified facts vs inference in real time.

## 3. Root causes
- Primary: capability-state regression was not explicitly detected and declared early.
- Secondary: task surface included dashboard/manual boundaries that increased operator dependence.
- Process gap: no hard trigger to pause execution and run incident-style troubleshooting.

## 4. How can we improve

### 4.1 Capability State Model (must always be explicit)
- `FULL`: broad expected tool surfaces operational.
- `DEGRADED`: partial loss; critical work still possible with friction.
- `SEVERELY_IMPAIRED`: major loss; manual fallback dominates.
- `DISCONNECTED`: core surfaces unavailable; execute only containment/workaround.

### 4.2 Truthfulness Contract (mandatory on capability-sensitive claims)
Each material claim must include one of:
- `Verified (X%)`: directly tested in-session with command/tool evidence.
- `Inferred (X%)`: reasoned but not directly verified.
- `Unknown (X%)`: insufficient evidence; no certainty claim.

Rules:
- No certainty claim without explicit evidence path.
- If contradictory signals appear, downgrade certainty immediately.
- After 3 failed high-likelihood hypotheses, if confidence drops below 30%, switch to containment/workaround mode.

### 4.3 Immediate Surfacing Protocol (non-optional)
When any capability regression is detected:
1. Announce state immediately (`DEGRADED` or worse), even without root cause.
2. Provide impact scope (what is blocked/slow).
3. Provide 2-3 hypotheses with confidence percentages.
4. Run fast tests and report outcomes.
5. If unresolved after 3 attempts, quarantine and apply workaround plan.

### 4.4 No Burden-Shift Default
- If the agent can do a task faster via tools/commands, the agent executes it.
- CJ manual steps are requested only for true ownership-bound UI/auth steps.

### 4.5 Audit/Parity Integrity Rule
- If asked to run a specific audit mode (e.g., Full T3), run exactly that or explicitly decline with reason and alternative.
- No terminology substitutions that evade the requested requirement.

## 5. Next immediate actions
1. Implement this protocol as a standing operations rule for migration and backlog execution.
2. Track capability state at session start and at each major phase transition.
3. Add a CI/process check artifact proving truth labels were applied to capability-critical updates.
4. Keep workaround path active (lifecycle labels) while Linear workflow-schema control is uncertain.

## Incident Reference
- Linear status incident (verified):
  - https://linearstatus.com/incidents/01KJQSGSNF0FHV5DP7DM467GHK
  - Observed status text at verification time: partial outage / agent suspensions affecting Codex/Copilot/Cursor integrations.
