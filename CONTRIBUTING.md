# Contributing

## Pre-push checklist

Run the local audit before pushing:

```bash
make audit
```

This executes:
- `scripts/check_repo_size.sh` (tracked file size guard)
- unit tests (`unittest discover`)

## Artifact policy

- Do not commit runtime cache/log outputs from ignored paths (`cache/`, `.wrangler/`, most `artifacts/` runtime folders).
- Transcript files under `transcripts/` are currently tracked artifacts.

## Notes

- If audit fails, fix failures first; do not bypass the guard.
- CI runs the same `make audit` target on push/PR.

