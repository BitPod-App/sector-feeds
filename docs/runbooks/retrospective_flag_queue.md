# Retrospective Flag Queue

Use this queue for quick capture during execution when something should be discussed in a later retrospective meeting.

This queue is not a retrospective itself. It is an input inbox.

## Command

```bash
bash scripts/flag_retro_item.sh --note "Example: handoff drift on run metadata" --scope "m9" --source "codex" --run-id "M9-PROVING-RUN-002"
```

## Output files

- machine-readable queue:
  - `artifacts/coordination/retrospective_flag_queue.jsonl`
- human-readable queue:
  - `artifacts/coordination/retrospective_flag_queue.md`

## Suggested meeting workflow

1. Collect queue items during the week.
2. In the retrospective meeting, group by scope and root cause.
3. Convert selected items into actions/issues.
4. Mark resolved/handled status in downstream tracking (do not rewrite historical queue rows).
