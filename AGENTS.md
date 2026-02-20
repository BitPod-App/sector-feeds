# Agent Setup Notes

This repository expects the `taylor` skill to live outside the repo at:

- `~/.agents/skills/taylor/SKILL.md`

## Expected Skill Baseline

- Skill name field: `name: taylor`
- Required section header: `## Project vision & architecture knowledge`
- Required reference doc: `~/.agents/skills/taylor/references/app-mission-vision.md`

## Bootstrap Check

Run this from repo root to validate local setup:

```bash
bash scripts/check_taylor_skill.sh
```
