# sector-feeds AGENTS

This file contains repo-specific instructions only.

## Permalink / public-surface verification

When you change permalink landing-page HTML, permalink bundle generation, or
Cloudflare deployment logic, verify from repo root with commands that do not
depend on external local-only tooling.

Preferred checks:

```bash
python3 scripts/refresh_public_permalinks.py jack_mallers_show
python3 -m pytest tests/test_storage.py
git diff --check
```

Use the generated permalink outputs to confirm:
- `artifacts/public/permalinks/<opaque_id>/index.html` contains the expected UI
  changes,
- `status.json`, `transcript.md`, and `discovery.json` are still emitted,
- public verification output stays truthful about real deploy/readability state.

If the repo already has a fresh local status artifact for the show, optionally run:

```bash
python3 scripts/verify_public_permalink_bundle.py --show jack_mallers_show --base-url https://permalinks.bitpod.app
```

## Transcript changes

When changing transcript rendering or selection behavior:
- inspect `transcripts/jack_mallers_show/` and `index/processed.json`,
- confirm the latest permalink transcript still points at the intended episode,
- prefer tests in `tests/test_storage.py` and `tests/test_sync_filtering.py`
  when the change affects public permalink outputs or transcript selection.

## Review Bundle Gate

- No bundle = no review claim.
- Any claim of "line-by-line review" must include:
  - bundle file path
  - exact command used to generate it
- Standard command:

```bash
bash scripts/make_review_bundle.sh
```

## Review Bundle Format (strict)

Every review bundle must use this section order exactly:
- A) Context: repo, base branch, head branch, commit hashes, timestamp
- B) `git diff --stat` (`base...HEAD`)
- C) full `git diff` (`base...HEAD`)
- D) verification outputs (health checks/tests/scripts)
- E) decisions needed (explicit blockers/questions)

## Bridge Session Memory Capture (required)

When ending a Bridge GPT planning/review session, memory summary must be structured as:
- Decisions (locked)
- Invariants (locked)
- Next Actions (who/what)
- Risks / Unknowns
