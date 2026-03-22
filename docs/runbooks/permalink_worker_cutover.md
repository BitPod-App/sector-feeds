# Permalink Worker Cutover Runbook

Purpose:

- complete the permalink hosting cutover from Cloudflare Pages continuity to Worker-backed serving
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

- temporary continuity: Cloudflare Pages project `bitpod-public-permalinks`
- target architecture: Worker `bitpod-public-permalinks-worker` with static assets from `artifacts/public/permalinks`
- current blocker: `permalinks.bitpod.app` still has an existing DNS/domain binding, so direct Worker attachment fails until Cloudflare-side domain ownership is detached or overridden

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
  - `CLOUDFLARE_API_TOKEN` for current Pages continuity
  - `CLOUDFLARE_ACCOUNT_ID`
- preferred for Worker deploys:
  - `CLOUDFLARE_WORKERS_API_TOKEN`
  - this secret should include Workers deploy permissions for `bitpod-public-permalinks-worker`
- optional:
  - `CLOUDFLARE_WORKER_NAME`
  - `PERMALINKS_WORKER_CUSTOM_DOMAIN`
  - `PERMALINKS_WORKER_PREVIEW_BASE_URL`
    - use this during cutover if canonical `permalinks.bitpod.app` is temporarily unavailable
    - example: `https://bitpod-public-permalinks-worker.cjarguello.workers.dev`

Workflow behavior:

- before cutover:
  - `deploy-public-permalinks.yml` and `mallers-weekly-fetch.yml` keep Pages continuity current
  - `deploy-public-permalinks-worker.yml` keeps the Worker preview surface current
  - Worker verification targets the preview hostname
  - if the Worker workflow fails with Cloudflare auth error `10000`, add or replace `CLOUDFLARE_WORKERS_API_TOKEN` with a token that has Workers deploy permissions
  - if the Worker workflow cannot rebuild the bundle on a clean checkout because the canonical status URL is gone, set `PERMALINKS_WORKER_PREVIEW_BASE_URL` so refresh can fall back to the preview Worker status URL
- after cutover:
  - set `PERMALINKS_WORKER_CUSTOM_DOMAIN=permalinks.bitpod.app`
  - switch canonical workflows to the Worker path
  - workflows verify the canonical domain
  - canonical verification writes bundle health back into `status.json` and redeploys once

Rollback:

1. remove the Worker custom-domain attachment for `permalinks.bitpod.app`
2. restore the Pages project custom-domain binding
3. unset `PERMALINKS_WORKER_CUSTOM_DOMAIN` in GitHub Actions vars if workflows should return to preview-only verification
4. verify the known fixture on the restored Pages continuity surface

Retirement condition for Pages:

- custom-domain cutover succeeds
- Worker-backed canonical verification succeeds from CI and from a normal public client
- no remaining production workflow depends on `wrangler pages deploy`
