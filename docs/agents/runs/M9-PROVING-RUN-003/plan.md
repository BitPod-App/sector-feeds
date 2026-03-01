# plan.md

## Goal
Ship a non-script, low-blast feature that improves retrospective meeting preparation by summarizing queued retrospective flags from the Python CLI.

## Problem statement (2-5 lines)
Run-002 added queue capture (`flag_retro_item.sh`), but there is no native Python command to inspect queue health and recent items. This creates friction for meeting prep and weakens auditability from runtime capture to review.

## Scope
In:
- Add `bitpod retro-flags` command.
- Add Python queue loader/summarizer module.
- Add unit tests for normal and malformed JSONL behavior.
- Document CLI queue inspection command.

Out:
- New queue status mutation workflows (close/reopen flags).
- Retrospective meeting automation/scheduling.
- Changes to existing flag writer behavior.

## Acceptance criteria (3-7)
- [x] `python3 -m bitpod retro-flags --json` returns path/counts/recent items.
- [x] `--limit` controls recent output; invalid limit fails non-zero.
- [x] malformed queue JSONL fails with clear error and non-zero exit.
- [x] unit tests cover queue load/summarize + CLI error/success paths.

## Dependencies
- GitHub tracking issue: `https://github.com/cjarguello/bitpod/issues/22`
- Existing queue artifact path:
  - `artifacts/coordination/retrospective_flag_queue.jsonl`

## Risks + mitigations
- Risk: malformed runtime artifact could break meeting-prep command.
  - Mitigation: explicit parse error handling with line numbers and exit code `2`.
- Risk: command output shape drifts over time.
  - Mitigation: machine-readable JSON output path preserved in tests.

## Dispatch
- Tracking issue: `https://github.com/cjarguello/bitpod/issues/22`
- Linear issue: `TBD` (to mirror during Linear sync)
- Engineer owner: Atlas (executed in this run)
- Vera QA trigger condition: CLI command evidence + unit test results captured in `execution_notes.md`
- CJ gate required: yes
