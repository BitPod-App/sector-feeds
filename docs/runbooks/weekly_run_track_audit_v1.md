# Weekly Run-Track Audit v1

## Scope

Audit the weekly Jack Mallers automation tracks to answer four questions:

1. Why are these jobs being run?
2. What outputs are they expected to produce?
3. What outputs actually exist in the canonical `sector-feeds` workspace?
4. Which jobs and artifacts are useful enough to keep?

## Canonical intended contract

The current repo docs define exactly two allowed weekly automations:

1. `legacy_tuesday_track`
   - command: `bash scripts/run_legacy_tuesday_track.sh jack_mallers_show`
   - purpose: stable personal weekly report path
   - expected outputs:
     - `artifacts/jack_mallers_show_tuesday_report.md`
     - permalink/status contract via `bash scripts/print_show_contract.sh jack_mallers_show`
2. `experimental_track`
   - command: `bash scripts/run_experimental_track.sh jack_mallers_show`
   - purpose: isolated experimental intake/output path
   - expected outputs:
     - `artifacts/private/experimental_weekly/jack_mallers_show_intake_snapshot.json`
     - optional `artifacts/private/weekly_bundles/weekly_critical_bundle.json`
     - optional external gate artifact under `bitregime-core`

Friday legacy is intentionally documented as ad hoc only, not a standing weekly automation.

Source runbooks/docs reviewed:
- `docs/runbooks/weekly_automation_two_track_contract.md`
- `docs/runbooks/report_tracks_short_vs_long_term.md`
- `docs/runbooks/legacy_tuesday_report.md`
- `docs/runbooks/experimental_weekly_btc_gate.md`
- `docs/prompts/weekly_tracks_quickstart.md`

## Actual live automation state

Automation store currently contains eight paused weekly jobs:

### Canonical-named jobs
- `legacy_tuesday_track` (`bitpod-tuesday-verify`)
- `experimental_track` (`bitpod-weekly-sync`)

### Duplicate legacy debris
- `mallers-monday-sync`
- `mallers-monday-sync-2`
- `mallers-monday-sync-3`
- `mallers-tuesday-verify`
- `mallers-tuesday-verify-2`
- `mallers-tuesday-verify-3`

All inspected automation TOMLs still point at the obsolete workspace cwd:
- `$WORKSPACE/bitpod`

The canonical repo path is now:
- `$WORKSPACE/sector-feeds`

## What the scripts actually do

### Legacy Tuesday wrapper
`bash scripts/run_legacy_tuesday_track.sh jack_mallers_show`

Behavior:
- conditionally runs `run_show_weekly.sh` if YouTube DNS resolves
- falls back to existing status artifacts if heavy sync cannot run
- always runs `report_show_weekly_status.sh jack_mallers_show tuesday`
- always runs `print_show_contract.sh jack_mallers_show`

### Experimental wrapper
`bash scripts/run_experimental_track.sh jack_mallers_show`

Behavior:
- conditionally runs `experimental_weekly_ctl.sh collect`
- then runs `experimental_weekly_ctl.sh process`
- then runs `print_show_contract.sh jack_mallers_show`

### Important implementation detail

The contract is split across multiple storage locations:
- transcript pointer content under `transcripts/jack_mallers_show/`
- status/report artifacts expected under `artifacts/`
- optional GPT consumption acknowledgment under `artifacts/<slug>_gpt_ack.json`
- optional bundle/gate artifacts under `artifacts/private/...` and `bitregime-core/artifacts/...`

## Current canonical workspace reality

In a clean canonical `sector-feeds` clone/worktree:
- `transcripts/jack_mallers_show/jack_mallers.md` exists
- `transcripts/jack_mallers_show/jack_mallers_status.json` does not exist
- `transcripts/jack_mallers_show/mallers_bitpod_status.json` does not exist
- no top-level `artifacts/` directory exists
- no top-level `state/` directory exists

This means the documented weekly automation contract currently depends on non-versioned runtime outputs that are not present in a fresh canonical workspace.

## What is useful vs opaque

### Potentially useful
- deterministic Tuesday readiness report for a specific show
- deterministic experimental intake snapshot for a specific show
- explicit explanation of whether the latest episode was processed, why it was skipped, and what blocked it
- durable evidence of whether GPT actually consumed the episode used in reporting

### Currently opaque / weak
- duplicate Monday sync and Tuesday verify jobs add no value
- paused jobs pointing at the old repo path create confusion and hidden failure risk
- artifacts are split across `transcripts/`, `artifacts/`, and external repo outputs with no single operator-facing summary
- current contract does not make "used by GPT" obvious unless the GPT ack artifact exists and matches the current `run_id`
- because runtime outputs are not present in a clean clone, a human cannot tell from repo state alone whether the automations are currently healthy or merely documented


## GPT consumer framing (cross-check)

GPT was asked to evaluate the weekly tracks from the perspective that GPT is currently the only consumer of `sector-feeds` outputs and the only current user of the permalink.

Result:
- `legacy_tuesday_track` only makes sense as a reliability/backfill lane
- `experimental_track` only makes sense as a safe diff/evaluation lane

Operator-facing interpretation:
- legacy should prove that it catches missed or late-changing episodes and produces one canonical record GPT can trust
- experimental should prove new processing logic against the same latest episode and emit a comparison artifact, not just another opaque run

Useful GPT-oriented fields that are currently missing or non-obvious:
- `latest_episode_id`
- `last_seen_episode_id`
- `processed_at`
- `used_by_gpt_at`
- `gpt_run_id`
- optional `gpt_use_count`
- optional `experiment_version`

This strengthens the audit conclusion: the weekly runs should stay only if they answer discovery / processing / GPT consumption explicitly for the latest episode in one operator-facing summary.

## Audit conclusion

The two-track model is directionally valid, but the current weekly automation setup is not justified in its live form.

Why:
- live automations violate the repo's own two-track policy
- all live jobs point to the obsolete repo path
- the canonical workspace does not contain the runtime artifacts the jobs are supposed to refresh
- operator value is weak because it is still difficult to answer the three key questions cleanly:
  - was the latest episode discovered?
  - was it processed successfully?
  - was it actually consumed by GPT for reporting?

## Recommended next actions

### Keep
- keep only two weekly jobs:
  - `legacy_tuesday_track`
  - `experimental_track`

### Remove / retire
- delete all duplicate `mallers-monday-sync*` jobs
- delete all duplicate `mallers-tuesday-verify*` jobs

### Fix before re-activation
1. repoint canonical jobs to `$WORKSPACE/sector-feeds`
2. define one operator-facing evidence surface per run
3. ensure useful recurring artifacts use unique, timestamped or context-keyed names when they represent run results rather than stable docs
4. make GPT consumption state explicit and queryable from one summary artifact
5. document whether the weekly jobs are meant to be:
   - health checks only
   - precompute tasks for GPT
   - operator alerts
   - or future-user simulation tasks

## Proposed useful recurring artifacts

If weekly jobs remain active, they should produce durable, uniquely named evidence artifacts such as:
- `artifacts/runs/legacy_tuesday_track/jack_mallers_show/<timestamp>__summary.md`
- `artifacts/runs/experimental_track/jack_mallers_show/<timestamp>__summary.md`
- `artifacts/runs/.../<timestamp>__status.json`

Each run summary should answer:
- latest candidate episode id
- source chosen (`rss_only`, `rss_preferred`, `all`)
- whether new episode was accessible
- whether it was processed
- whether it was included in the pointer/status contract
- whether GPT consumption acknowledgment exists for the same `run_id`
- if not, exact failure stage and next action

## Stale path notes found during audit

The following docs still contain obsolete `/bitpod` path references and should be normalized in a follow-up pass:
- `docs/runbooks/experimental_weekly_btc_gate.md`
- `docs/runbooks/intake_gate_daily_ops.md`
- `docs/runbooks/bitregime_core_intake_handshake.md`
- `docs/runbooks/show_onboarding_template.md`
- `docs/runbooks/m9_intake_governance_agent.md`

## Decision rule

Do not keep recurring weekly automations active unless they produce one clear, operator-useful, uniquely attributable run output and can answer whether the newest episode was discovered, processed, and actually consumed by GPT.
