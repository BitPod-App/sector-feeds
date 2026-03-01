# verification_report.md (Vera)

## Environment matrix
- build/version: `codex/m9-proving-run-002-preflight-check` (working state before PR merge)
- platform/device: local macOS dev workspace
- os/browser: shell verification (no browser dependency)
- account/state assumptions: standard template set exists unless explicitly renamed for negative-path test

## Critical acceptance criteria evidence
### AC-1
PASS evidence OR reproducible failure:
- Missing-template preflight fails before scaffold:
  - Setup: temporarily renamed `docs/agents/proving-run/templates/result_template_v1.md`
  - Command: `bash scripts/init_proving_run.sh M9-PROVING-RUN-002-MISSING-TEMPLATE`
  - Evidence:
    - output begins `FATAL: required proving-run templates missing:`
    - lists missing template absolute path
    - `exit=1`
    - `missing_template_run_dir_created=NO`

### AC-2
PASS evidence OR reproducible failure:
- Existing and fresh paths preserved:
  - Existing run command: `bash scripts/init_proving_run.sh M9-PROVING-RUN-002`
    - evidence: six `SKIP existing` + `proving_run_init=OK`
  - Fresh run command: `bash scripts/init_proving_run.sh M9-PROVING-RUN-002-SMOKE`
    - evidence: six `CREATE` + `proving_run_init=OK` + `tmp_file_count=6`
    - cleanup evidence: `tmp_cleanup=OK`
  - Missing arg command: `bash scripts/init_proving_run.sh`
    - evidence: usage text + `missing_arg_exit=2`

## Failure reason (required if FAILED)
this failed QA because ...
- failing criteria: n/a
- concise reason: n/a
- evidence links:
  - `docs/agents/runs/M9-PROVING-RUN-002/plan.md`
  - `docs/agents/runs/M9-PROVING-RUN-002/execution_notes.md`
  - `https://github.com/cjarguello/bitpod/issues/17`

## Optional small/obvious fix hints (max 1-3)
- optional: add `--strict` flag later if you want exit code differentiation between usage and template failures.

QA_VERDICT: PASSED
