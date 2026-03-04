# Decide where to move Bitpod files outside permitted folders

Linked issue: BIT-40
Linear URL: https://linear.app/bitpod-app/issue/BIT-40/establish-global-artifact-naming-policy-new-location-for-disallowed

## Problem
Operational metadata and memory files can end up outside approved workspace roots, which violates workspace boundaries and creates shadow state.

## Decision requested
Choose and standardize a single workspace-safe home for Bitpod/Codex runtime metadata.

Suggested path:
`/Users/cjarguello/bitpod-app/local-workspace/local-codex/.codex/`

## Constraints
- Do not move/rename canonical runtime files without explicit migration design.
- Keep persistence near-zero clutter and preserve only high-value history.
- Do not write files outside approved workspace folders.
