# M9_AGENT_OS_PROVING_RUN_v1

Status: ACTIVE
Owner: CJ
Last updated: 2026-03-01
Purpose: Execute one real end-to-end proving run for the agent operating system.

## Objective
Prove this workflow works on a real issue with auditable artifacts:
- Taylor plans/dispatches
- Engineer implements
- Vera verifies independently
- CJ approves/rejects merge gate
- retrospective logged

## Governing references
- `docs/agents/linear/LINEAR_MCP_PERMISSION_MODEL_v1.md`
- `docs/agents/linear/LINEAR_BEST_PRACTICES_GUIDE_V1.md`
- `milestones/m9_linear_mcp_policy.json`

## Proving-run scope
Pick one real issue with low-to-medium blast radius:
- preferred type: small feature or high-confidence bug fix
- avoid irreversible migrations
- avoid broad schema changes

## Required run id
Use: `M9-PROVING-RUN-001` (increment for each new run)

## Required artifact folder
Create:
- `docs/agents/runs/<run-id>/`

Initializer command:
```bash
bash scripts/init_proving_run.sh M9-PROVING-RUN-001 --context i22p23
```

Minimum files:
- `plan_<context>_<YYYY-MM-DD>.md` (Taylor)
- `execution_notes_<context>_<YYYY-MM-DD>.md` (Engineer)
- `qa_report_<context>_<YYYY-MM-DD>.md` (Vera)
- `final_decision_<context>_<YYYY-MM-DD>.md` (gate owner)
- `ticket_summary_<context>_<YYYY-MM-DD>.md` (Taylor wrap-up)
- `retrospective_<context>_<YYYY-MM-DD>.md` (what to change)
- `artifact_manifest.json` (maps artifact roles to actual file names)

Artifact metadata:
- Each generated `.md` artifact starts with a YAML metadata block including `repo`, `run_id`, `context`, `date_utc`, and `artifact_kind`.

## Workflow (strict order)
1. Taylor creates/updates Linear issue using best-practice baseline.
2. Taylor writes `plan_<context>_<YYYY-MM-DD>.md` and dispatch details.
3. Engineer executes and writes `execution_notes_<context>_<YYYY-MM-DD>.md` with PR + test evidence.
4. Vera runs QA independently and writes `qa_report_<context>_<YYYY-MM-DD>.md` with final line:
   - `QA_VERDICT: PASSED` or
   - `QA_VERDICT: FAILED`
5. Gate owner records decision in `final_decision_<context>_<YYYY-MM-DD>.md`.
6. If approved, finalize `ticket_summary_<context>_<YYYY-MM-DD>.md` + `retrospective_<context>_<YYYY-MM-DD>.md` before merge.
7. Merge PR.
8. Post-merge edits should be metadata-only (for example merge hash), and only when needed.

## Vera boundary (enforced)
- Vera decides only `PASSED` or `FAILED`.
- No collaboration required for verdict.
- If failed, include: `this failed QA because ...` + failing criteria + evidence.
- Optional fix hints only when small/obvious (max 1-3 bullets).

## CJ gate rule
No merge before `final_decision_<context>_<YYYY-MM-DD>.md` is present with explicit decision.

## Retros timing rule
- Retrospective content should be completed pre-merge by default.
- Post-merge retrospective rewrites are exception-only and should not be expected.

## Acceptance criteria for proving run
- one real Linear issue completed end-to-end
- all required artifacts present in run folder
- Vera verdict present and evidence-linked
- CJ decision explicitly recorded
- merged PR (if approved) and retrospective completed

## Exit outcomes
- PASS: run completed with clear evidence and no critical process drift
- FAIL: missing artifacts, ambiguous ownership, or gate bypass occurred

## If FAIL
- stop scaling autonomy
- file follow-up issue for each process defect
- run `M9-PROVING-RUN-002` only after fixes
