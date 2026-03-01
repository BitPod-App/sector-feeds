# LINEAR_MCP_PERMISSION_MODEL_v1

Status: ACTIVE
Owner: CJ
Last updated: 2026-03-01
Policy version: `m9_linear_mcp_policy.v1`

## Objective
Enable high-autonomy execution in early M-9 while preserving reversibility and auditability.

## Hard requirement
Taylor must follow:
- `docs/agents/linear/LINEAR_BEST_PRACTICES_GUIDE_V1.md`

This is the default baseline in bootstrap mode.
Contextual overrides are allowed when startup realities require them, but each override must be logged with:
- reason for override
- scope and duration
- rollback/normalization plan

## Bootstrap mode
- mode: `bootstrap_high_autonomy`
- rationale: low-risk workspace state, high setup velocity required
- default: Taylor has broad write/admin authority in Linear via MCP

## Agent permission matrix

### Taylor (Lead PM)
- Access: read/write/admin
- Allowed: projects, workflows, templates, labels, issue create/edit/move/assign, cycles, triage sequencing
- Destructive actions: allowed in bootstrap mode if all safeguards run:
  - change proposal artifact
  - pre-change snapshot
  - rollback note
  - post-change validation

### Vera (QA)
- Access: read/write (QA lane)
- Allowed: bug issue creation, QA labels, verification updates, evidence links, readiness outcome
- Not allowed: scope/priority/schema restructuring

### Atlas/Solder (Engineers)
- Access: read/write (execution lane)
- Allowed: issue status updates, implementation notes, PR links, task breakdown updates
- Not allowed: product priority/schema governance changes without Taylor dispatch

## CJ escalation gates
CJ approval required for:
- deleting a Linear team/project/workflow
- mass destructive changes affecting more than 20 entities
- irreversible data removal where rollback is not documented
- integration-level auth/permission changes outside normal issue operations

## Required artifacts
- Change proposal template:
  - `docs/agents/linear/templates/linear_change_proposal_template_v1.md`
- Schema change log:
  - `docs/agents/linear/CHANGELOG_LINEAR_SCHEMA.md`

## Validation checklist after schema changes
1. Core labels/templates still present.
2. Existing active issues still mapped to valid statuses.
3. Blocked workflow labels still resolvable.
4. PM/QA/Eng ownership fields still usable.
5. No orphaned status transitions.

## Lockdown trigger
If any of these occur, switch to `lockdown_review_required` mode:
- unplanned schema breakage
- two failed post-change validations in a row
- loss of issue traceability

In lockdown mode:
- destructive actions disabled for all agents except CJ-approved runs.
