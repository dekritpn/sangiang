/**
 * Unified Cloudflare Worker Entrypoint for Sangiang Ecosystem (sangihe.org)
 * Supports Cloudflare Workers with Static Assets (`npx wrangler deploy`) + Cloudflare D1 (`env.DB`).
 *
 * Subdomain Routing:
 * - translate.sangihe.org -> Sangiang Translation Engine UI (/* and /v1/*)
 * - chat.sangihe.org / sangiang.sangihe.org -> Sangiang Chatbot UI (/chat/* and /api/*)
 * Path Routing (works on any domain including *.workers.dev):
 * - / or /translate/ -> Sangiang Translation Engine UI
 * - /chat/ -> Sangiang Chatbot UI
 */

import { onRequestGet as healthGet } from "../functions/health.js";
import { onRequestGet as v1ModelsGet } from "../functions/v1/models.js";
import { onRequestPost as v1TranslatePost } from "../functions/v1/translate.js";
import { onRequestPost as v1FeedbackPost, onRequestGet as v1FeedbackGet } from "../functions/v1/feedback.js";
import { onRequestPost as v1DictLookupPost } from "../functions/v1/dictionary/lookup.js";
import { onRequestPost as v1MorphAnalyzePost } from "../functions/v1/morphology/analyze.js";
import { onRequestGet as apiHealthGet } from "../functions/api/health.js";
import { onRequestGet as apiModelsGet } from "../functions/api/models.js";
import { onRequestPost as apiChatPost } from "../functions/api/chat.js";
import { SANGIHE_LANDING_HTML } from "../functions/_lib/landing_html.js";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

const SCANNER_PATH_RE = /(?:^|\/)(?:\.env|\.git|\.svn|\.hg|\.aws|\.vscode|\.cursor|phpinfo|wp-admin|wp-login|wp-content|wp-includes|xmlrpc\.php|actuator|graphql|telescope|_profiler|_environment|service-account\.json|firebase-key\.json|firebase-adminsdk\.json|google-key\.json|google-credentials\.json|gcp-credentials\.json|gcp-sa\.json|sa\.json|keyfile\.json|key\.json)|\.php$/i;

function withCors(response) {
  const headers = new Headers(response.headers);
  for (const [k, v] of Object.entries(CORS_HEADERS)) {
    headers.set(k, v);
  }
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

function withStaticCache(response) {
  if (!response || response.status !== 200) return response;
  const headers = new Headers(response.headers);
  headers.set("Cache-Control", "public, max-age=86400");
  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers,
  });
}

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const host = url.hostname.toLowerCase();
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const method = request.method.toUpperCase();

    // 0a. Permanently de-index legacy MediaWiki spam URLs (/wiki/*) with 410 Gone
    if (path === "/wiki" || path.startsWith("/wiki/")) {
      return new Response("Gone", { status: 410 });
    }

    // 0b. Fast-reject automated vulnerability scanner paths BEFORE HTTP->HTTPS redirect
    if (SCANNER_PATH_RE.test(path)) {
      return new Response("Not Found", { status: 404 });
    }

    // 0c. Enforce HTTPS on production domains
    if (
      url.protocol === "http:" &&
      host !== "localhost" &&
      host !== "127.0.0.1" &&
      !path.startsWith("/.well-known/")
    ) {
      url.protocol = "https:";
      return Response.redirect(url.toString(), 301);
    }

    const context = { request, env, ctx };

    // 1. API Routes (Translation Engine + Chatbot)
    try {
      if (path === "/health" && method === "GET") {
        return withCors(await healthGet(context));
      }
      if (path === "/v1/models" && method === "GET") {
        return withCors(await v1ModelsGet(context));
      }
      if (path === "/v1/translate" && method === "POST") {
        return withCors(await v1TranslatePost(context));
      }
      if (path === "/v1/feedback" && method === "POST") {
        return withCors(await v1FeedbackPost(context));
      }
      if (path === "/v1/feedback" && method === "GET") {
        return withCors(await v1FeedbackGet(context));
      }
      if (path === "/v1/dictionary/lookup" && method === "POST") {
        return withCors(await v1DictLookupPost(context));
      }
      if (path === "/v1/morphology/analyze" && method === "POST") {
        return withCors(await v1MorphAnalyzePost(context));
      }
      if (path === "/api/health" && method === "GET") {
        return withCors(await apiHealthGet(context));
      }
      if (path === "/api/models" && method === "GET") {
        return withCors(await apiModelsGet(context));
      }
      if (path === "/api/chat" && method === "POST") {
        return withCors(await apiChatPost(context));
      }
    } catch (err) {
      return withCors(
        new Response(
          JSON.stringify({ detail: `Internal Server Error: ${err.message || String(err)}` }),
          { status: 500, headers: { "Content-Type": "application/json; charset=utf-8" } }
        )
      );
    }

    // 2. Domain & Subdomain-aware static asset routing
    const isRootPortalDomain =
      host === "sangihe.org" ||
      host === "www.sangihe.org" ||
      host === "dev.sangihe.org";

    const isChatSubdomain =
      host.startsWith("chat.") ||
      host.startsWith("dev-chat.") ||
      host.startsWith("chatbot.") ||
      host.startsWith("sangiang.");

    if (
      (isRootPortalDomain && (path === "/" || path === "/index.html")) ||
      path === "/landing" ||
      path === "/landing/index.html"
    ) {
      if (method !== "GET" && method !== "HEAD") {
        return new Response("Method Not Allowed", { status: 405 });
      }
      return new Response(SANGIHE_LANDING_HTML, {
        status: 200,
        headers: {
          "Content-Type": "text/html; charset=utf-8",
          "Cache-Control": "public, max-age=300, must-revalidate",
        },
      });
    }

    if (isRootPortalDomain && !path.startsWith("/static/") && path !== "/favicon.ico") {
      return new Response("Not Found", { status: 404 });
    }

    if (env.ASSETS) {
      if (path === "/favicon.ico") {
        const iconPath = isChatSubdomain ? "/chat/static/sangiang.jpeg" : "/static/sangiang.jpeg";
        const iconUrl = new URL(iconPath, url.origin);
        return withStaticCache(await env.ASSETS.fetch(new Request(iconUrl.toString(), request)));
      }

      if (isChatSubdomain) {
        if (url.pathname === "/" || url.pathname === "/index.html") {
          const chatUrl = new URL("/chat/", url.origin);
          return env.ASSETS.fetch(new Request(chatUrl.toString(), request));
        }
        if (url.pathname.startsWith("/static/")) {
          const chatStaticUrl = new URL("/chat" + url.pathname, url.origin);
          return withStaticCache(await env.ASSETS.fetch(new Request(chatStaticUrl.toString(), request)));
        }
      }

      if (url.pathname.startsWith("/static/")) {
        return withStaticCache(await env.ASSETS.fetch(request));
      }

      // Handle directory paths like /chat or /translate without trailing slash
      if (url.pathname === "/chat") {
        const chatUrl = new URL("/chat/", url.origin);
        return env.ASSETS.fetch(new Request(chatUrl.toString(), request));
      }
      if (url.pathname === "/translate") {
        const translateUrl = new URL("/translate/", url.origin);
        return env.ASSETS.fetch(new Request(translateUrl.toString(), request));
      }

      return env.ASSETS.fetch(request);
    }

    return new Response("Not Found", { status: 404 });
  },
};

/**
 * Durable Object pinned to Western North America ('wnam') so that outbound
 * LLM API requests always originate from a supported US region even when the
 * user's ISP routes their initial connection through Hong Kong (HKG).
 */
export class GeminiProxyDO {
  constructor(state, env) {
    this.state = state;
    this.env = env;
  }

  async fetch(request) {
    try {
      const { url, payload } = await request.json();
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const text = await resp.text();
      return new Response(text, {
        status: resp.status,
        headers: { "Content-Type": "application/json; charset=utf-8" },
      });
    } catch (err) {
      return new Response(
        JSON.stringify({ error: { message: err.message || String(err) } }),
        { status: 502, headers: { "Content-Type": "application/json; charset=utf-8" } }
      );
    }
  }
}
