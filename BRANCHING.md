# Branching And PR Naming

## Branch Naming

Use this pattern:

`codex/<type>/<scope>-<short-description>`

Examples:
- `codex/feat/jack-mallers-transcript-pipeline`
- `codex/fix/rss-guid-dedup`
- `codex/docs/readme-template`
- `codex/chore/release-automation`

Rules:
- Branch names describe work intent, not release version.
- Keep names lowercase and hyphenated.
- One branch should map to one cohesive change set/PR.

## PR Title Naming

Use Conventional Commit style in PR titles:

- `feat: add Jack Mallers RSS-to-transcript pipeline`
- `fix: prevent duplicate episode processing by GUID`
- `docs: establish README template for transcript pipeline`
- `chore: tighten release workflow`

Rules:
- Start with `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, or `ci`.
- Focus on user-visible impact or operational impact.
- Keep titles concise and specific.

## Version In Names

Include version numbers only for release-specific work.

Release branch pattern:
- `codex/release/vX.Y.Z`

Release PR title pattern:
- `release: vX.Y.Z`

All other feature/fix/docs branches and PRs should omit version numbers.

## Merge Hygiene

- Rebase or merge `main` before final review if needed.
- Keep unrelated file noise out of commits (for example `.DS_Store`).
- Confirm changelog and version metadata only when preparing an actual release PR.
