# Permalink Worker Cutover Runbook

Purpose:

- complete the permalink hosting cutover to Worker-backed serving
- preserve the existing public bundle contract and generated landing page UI
- provide one ordered cutover and rollback path so future agents do not need to re-investigate the architecture

Locked invariants:

- canonical hostname: `https://permalinks.bitpod.app`
- stable opaque permalink ids
- required public paths:
  - `/<opaque_id>/`
  - `/<opaque_id>/status.json`
  - `/<opaque_id>/intake.md`
  - `/<opaque_id>/transcript.md`
  - `/<opaque_id>/discovery.json`
- generated `index.html` remains the primary UI

Known parity fixture:

- `show_key`: `jack_mallers_show`
- `public_id`: `0ceb2e6abdba17e0`

Current architecture:

- production architecture: Worker `bitpod-public-permalinks-worker` with static assets from `artifacts/public/permalinks`
- canonical hostname: `permalinks.bitpod.app`
- preview hostname: `bitpod-public-permalinks-worker.cjarguello.workers.dev`

Worker preview verification:

```bash
bash scripts/deploy_public_permalinks_worker.sh bitpod-public-permalinks-worker jack_mallers_show
```

Expected preview result:

- Worker deploy output includes a `workers.dev` URL
- verification passes for:
  - landing page
  - `status.json`
  - `intake.md`
  - `transcript.md`
  - `discovery.json`

Important behavior:

- preview verification does **not** write health back into `status.json`
- this avoids polluting generated artifacts with `workers.dev` URLs before custom-domain cutover

Custom-domain cutover:

1. confirm preview parity succeeds on the known fixture
2. detach or override the existing `permalinks.bitpod.app` DNS/domain binding if Cloudflare refuses to attach the domain to the Worker
3. deploy the Worker with the custom domain:

```bash
PERMALINKS_WORKER_CUSTOM_DOMAIN=permalinks.bitpod.app \
BITPOD_PUBLIC_PERMALINK_BASE_URL=https://permalinks.bitpod.app \
bash scripts/deploy_public_permalinks_worker.sh bitpod-public-permalinks-worker jack_mallers_show
```

Cutover acceptance:

- `https://permalinks.bitpod.app/0ceb2e6abdba17e0/` returns the generated landing page
- raw artifact URLs under the same opaque root are public and readable
- transcript speech-preview UI remains present

GitHub Actions configuration:

- required:
  - `CLOUDFLARE_ACCOUNT_ID`
- preferred for Worker deploys:
  - `CLOUDFLARE_WORKERS_API_TOKEN`
  - this secret should include Workers deploy permissions for `bitpod-public-permalinks-worker`
- temporary fallback only:
  - `CLOUDFLARE_API_TOKEN`
- optional:
  - `CLOUDFLARE_WORKER_NAME`
  - `PERMALINKS_WORKER_CUSTOM_DOMAIN`
  - `PERMALINKS_WORKER_PREVIEW_BASE_URL`
    - use this during cutover if canonical `permalinks.bitpod.app` is temporarily unavailable
    - example: `https://bitpod-public-permalinks-worker.cjarguello.workers.dev`

Workflow behavior:

- `deploy-public-permalinks-worker.yml` is the canonical permalink deploy workflow
- `mallers-weekly-fetch.yml` deploys refreshed bundles through the Worker path
- workflows verify the canonical domain when `PERMALINKS_WORKER_CUSTOM_DOMAIN=permalinks.bitpod.app`
- canonical verification writes bundle health back into `status.json` and redeploys once
- if the workflow cannot rebuild the bundle on a clean checkout because the canonical status URL is temporarily unavailable, set `PERMALINKS_WORKER_PREVIEW_BASE_URL` so refresh can fall back to the preview Worker status URL

Rollback:

1. remove the Worker custom-domain attachment for `permalinks.bitpod.app`
2. unset `PERMALINKS_WORKER_CUSTOM_DOMAIN` in GitHub Actions vars if workflows should return to preview-only verification
3. verify the known fixture on the preview Worker surface
