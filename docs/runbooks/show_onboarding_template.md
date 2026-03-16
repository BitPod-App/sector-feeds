# Show Onboarding Template

Use `show_scaffold_template` in [shows.json](/Users/cjarguello/BitPod-App/sector-feeds/shows.json) as the copy source for a new show entry under `shows`.

## Minimal checklist

1. Copy scaffold into `shows.<new_show_key>`.
2. Set:
   - `show_key`
   - `stable_pointer`
   - `sector`
   - `feeds.rss` (required for canonical ingest)
3. Optional enrichments:
   - `youtube_handle`, `youtube_channel_url`, `feeds.youtube`, `feeds.youtube_channel_id`
   - `format_tags`
4. Run:

```bash
.venv311/bin/python -m bitpod discover --show <new_show_key>
bash scripts/run_show_weekly.sh <new_show_key>
bash scripts/print_show_contract.sh <new_show_key>
```

5. Validate board/gate:

```bash
make track-status-board SHOW_KEY=<new_show_key>
make track-status-check SHOW_KEY=<new_show_key>
```

