# Taylor Skill Pointer (Repo-Portable)

This repository points to the external canonical Taylor skill at:

- `~/.agents/skills/taylor/SKILL.md`

Do not duplicate or override Taylor's canonical behavior/spec in this repo.

## Taylor Skill Folder Status

- Keep `~/.agents/skills/taylor` as the canonical Taylor spec + references (required).
- Taylor runtime implementation lives in `tools/taylor` (repo-level runtime code).
- Repo docs are pointer + health-check surfaces only; do not duplicate spec text.

### Deprecation Criteria (future, not current)

Only consider deprecating the external skill folder after all are true:
- `tools/taylor/policy/taylor_policy.yaml` is versioned and stable.
- `tools/taylor` CLI/API behavior is stable.
- Determinism tests + manifests are in place.
- Canonical contract docs are mirrored in-repo without split-brain.
- A single source of truth is explicitly selected (external or in-repo), never both.

## Canonical Reference Anchors

- `~/.agents/skills/taylor/references/taylor-agent-contract.md`
- `~/.agents/skills/taylor/references/report-template.md` (periodic + ad hoc)
- `~/.agents/skills/taylor/references/bridge-gpt-team-sessions.md`

## Health Check

Run from repo root:

```bash
bash scripts/check_taylor_skill.sh
```
