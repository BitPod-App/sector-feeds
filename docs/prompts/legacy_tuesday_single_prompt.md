# Legacy Tuesday Single Prompt (Run + Verify)

Use this to run the legacy track and evaluate it in one pass.

```text
You are running and evaluating the Legacy Tuesday track.

Run commands in this order:
1) bash scripts/run_show_weekly.sh jack_mallers_show
2) bash scripts/report_mallers_tuesday_status.sh
3) bash scripts/print_show_contract.sh jack_mallers_show

Task:
1) Read:
   - artifacts/jack_mallers_show_tuesday_report.md
   - transcripts/jack_mallers_show/jack_mallers_status.json
2) Verify:
   - run_status == ok
   - intake_ready == true
   - ready_via_permalink == true
   - public permalink URLs exist in status payload
3) Summarize readiness in <=5 bullets.
4) Return final verdict: PASS or FAIL.
5) If FAIL, list exact blockers and one lowest-risk next command.

Rules:
- Use only repository artifacts and command outputs.
- Do not fetch external data.
- Do not redesign the pipeline.
- Do not mix in experimental/lab guidance.

Required output:
- verdict
- readiness_summary
- blockers
- next_command
```
