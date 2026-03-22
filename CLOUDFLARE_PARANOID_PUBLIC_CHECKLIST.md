# Cloudflare Paranoid-Public Checklist

Use this checklist for `bitpod-public-permalinks` hosting with public access but crawler-paranoid defaults.

## Current State (Already Applied)

- Pages project exists: `bitpod-public-permalinks`
- Canonical public hostname: `permalinks.bitpod.app`
- Pages preview hostname: `bitpod-public-permalinks.pages.dev`
- Deployed static artifact root: `artifacts/public/permalinks`
- Noindex policy active via `_headers`:
  - `X-Robots-Tag: noindex, nofollow, noarchive`
- `robots.txt` served with:
  - `User-agent: *`
  - `Disallow: /`

## Required For Full AI Crawl Control

AI Crawl Control is configured at a **Cloudflare zone/domain** level, not on raw `pages.dev` alone.

1. Attach a custom domain to the Pages project.
2. Ensure the custom domain is proxied through Cloudflare.
3. Apply AI crawler controls on that zone.

## Steps

1. Add custom domain to Pages
- Dashboard: Workers & Pages -> `bitpod-public-permalinks` -> Custom domains -> Set up a domain
- Use a dedicated subdomain, for example: `permalinks.yourdomain.com`

2. Confirm zone proxying
- Dashboard: DNS -> verify record is proxied (orange cloud)

3. Configure AI Crawl Control
- Dashboard: AI Crawl Control -> Crawlers
- Set default action policy:
  - Block unknown/unwanted crawlers
  - Allow only explicit crawlers you trust
- Keep response code for blocked crawlers as `403` unless you intentionally use `402` for paid access

4. Configure Bot settings
- Dashboard: Security Settings -> Bot traffic
- Enable `Block AI bots` for broad protection
- Enable `AI Labyrinth` for non-compliant crawler trapping

5. Validate robots + headers on custom domain
- `curl -I https://permalinks.yourdomain.com/<public_id>/status.json`
- Verify:
  - `x-robots-tag: noindex, nofollow, noarchive`
  - `200` for valid paths

6. Verify policy precedence (important)
- If using AI Crawl Control actions, avoid contradictory WAF/Bot rules that override desired crawler behavior.

## Recommended Defaults For Bitpod

- Keep site public (no auth) for now.
- Keep all permalink endpoints noindex/noarchive.
- Use allowlist-style AI policy:
  - Block all AI crawlers by default.
  - Allow only explicitly approved crawlers/operators.
- Keep dynamic transcript batch window for processors:
  - oldest -> newest processing order
  - bounded by min/max episodes and target total minutes.
