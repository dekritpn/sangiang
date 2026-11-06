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
import { onRequestPost as v1FeedbackPost } from "../functions/v1/feedback.js";
import { onRequestPost as v1DictLookupPost } from "../functions/v1/dictionary/lookup.js";
import { onRequestPost as v1MorphAnalyzePost } from "../functions/v1/morphology/analyze.js";
import { onRequestGet as apiHealthGet } from "../functions/api/health.js";
import { onRequestGet as apiModelsGet } from "../functions/api/models.js";
import { onRequestPost as apiChatPost } from "../functions/api/chat.js";

const CORS_HEADERS = {
  "Access-Control-Allow-Origin": "*",
  "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
  "Access-Control-Allow-Headers": "Content-Type, Authorization",
};

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

export default {
  async fetch(request, env, ctx) {
    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: CORS_HEADERS });
    }

    const url = new URL(request.url);
    const host = url.hostname.toLowerCase();
    const path = url.pathname.replace(/\/+$/, "") || "/";
    const method = request.method.toUpperCase();
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

    // 2. Subdomain-aware static asset routing for chat.sangihe.org / sangiang.sangihe.org
    const isChatSubdomain =
      host.startsWith("chat.") ||
      host.startsWith("chatbot.") ||
      host.startsWith("sangiang.");

    if (env.ASSETS) {
      if (isChatSubdomain) {
        if (url.pathname === "/" || url.pathname === "/index.html") {
          const chatUrl = new URL("/chat/index.html", url.origin);
          return env.ASSETS.fetch(new Request(chatUrl.toString(), request));
        }
        if (url.pathname.startsWith("/static/")) {
          const chatStaticUrl = new URL("/chat" + url.pathname, url.origin);
          return env.ASSETS.fetch(new Request(chatStaticUrl.toString(), request));
        }
      }

      // Handle directory paths like /chat or /translate without trailing slash
      if (url.pathname === "/chat" || url.pathname === "/chat/") {
        const chatUrl = new URL("/chat/index.html", url.origin);
        return env.ASSETS.fetch(new Request(chatUrl.toString(), request));
      }
      if (url.pathname === "/translate" || url.pathname === "/translate/") {
        const translateUrl = new URL("/translate/index.html", url.origin);
        return env.ASSETS.fetch(new Request(translateUrl.toString(), request));
      }

      return env.ASSETS.fetch(request);
    }

    return new Response("Not Found", { status: 404 });
  },
};
