function htmlEscape(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function rawArtifactUrl(origin, opaqueId, filename) {
  return `${origin}/${opaqueId}/${filename}`;
}

async function fetchAsset(request, env, pathname) {
  const assetUrl = new URL(pathname, request.url);
  return env.ASSETS.fetch(new Request(assetUrl, request));
}

async function renderShowPage(request, env, opaqueId) {
  const assetResp = await fetchAsset(request, env, `/${opaqueId}/index.html`);
  if (assetResp.status === 200) {
    return assetResp;
  }

  const statusResp = await fetchAsset(request, env, `/${opaqueId}/status.json`);
  if (statusResp.status !== 200) {
    return new Response("Not Found", { status: 404 });
  }

  const status = await statusResp.json();
  const origin = new URL(request.url).origin;
  const links = [
    ["status.json", rawArtifactUrl(origin, opaqueId, "status.json")],
    ["intake.md", rawArtifactUrl(origin, opaqueId, "intake.md")],
    ["transcript.md", rawArtifactUrl(origin, opaqueId, "transcript.md")],
    ["discovery.json", rawArtifactUrl(origin, opaqueId, "discovery.json")],
  ];

  const body = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <meta name="robots" content="noindex,nofollow,noarchive">
    <title>BitPod Permalink Bundle</title>
    <style>
      :root { color-scheme: light; }
      body { font-family: ui-monospace, SFMono-Regular, Menlo, monospace; margin: 2rem; line-height: 1.5; }
      h1 { margin-bottom: 0.5rem; }
      code, pre { background: #f5f5f5; padding: 0.15rem 0.3rem; border-radius: 4px; }
      .muted { color: #666; }
      ul { padding-left: 1.25rem; }
    </style>
  </head>
  <body>
    <h1>BitPod Permalink Bundle</h1>
    <p class="muted">Opaque permalink surface for one feed. Use the raw artifact links below or the embedded contract JSON.</p>
    <ul>
      ${links.map(([label, href]) => `<li><a href="${htmlEscape(href)}">${htmlEscape(label)}</a></li>`).join("\n")}
    </ul>
    <h2>Embedded Run Contract</h2>
    <script id="bitpod-run-contract" type="application/json">${htmlEscape(JSON.stringify(status))}</script>
    <pre>${htmlEscape(JSON.stringify(status, null, 2))}</pre>
  </body>
</html>`;

  return new Response(body, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "X-Robots-Tag": "noindex, nofollow, noarchive",
      "Access-Control-Allow-Origin": "*",
    },
  });
}

export default {
  async fetch(request, env) {
    if (!["GET", "HEAD"].includes(request.method)) {
      return new Response("Method Not Allowed", { status: 405 });
    }

    const url = new URL(request.url);
    const path = url.pathname.replace(/\/+$/, "") || "/";

    if (path === "/") {
      return new Response("Not Found", { status: 404 });
    }

    const showPageMatch = path.match(/^\/([a-f0-9]{16})$/);
    if (showPageMatch) {
      return renderShowPage(request, env, showPageMatch[1]);
    }

    return fetchAsset(request, env, url.pathname);
  },
};
