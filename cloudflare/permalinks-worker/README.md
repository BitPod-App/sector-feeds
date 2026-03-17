# Permalinks Worker

Long-term Cloudflare target for the permalink surface:

- one opaque URL per `sector_feed_id` / show
- raw artifact links nested under the same opaque root
- machine-readable run contract embedded on the HTML page itself

Current routing shape:

- `/<opaque_id>` -> rendered HTML landing page
- `/<opaque_id>/status.json`
- `/<opaque_id>/intake.md`
- `/<opaque_id>/transcript.md`
- `/<opaque_id>/discovery.json`

The asset directory points at the generated runtime bundle under:

- `artifacts/public/permalinks/`

Deploy flow:

1. refresh local permalink artifacts from current show status
2. deploy worker + static assets
3. verify public readability against actual deployed URLs

Suggested command:

```bash
bash scripts/deploy_public_permalinks_worker.sh bitpod-public-permalinks-worker jack_mallers_show
```
