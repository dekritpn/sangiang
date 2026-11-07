/**
 * Cloudflare Pages Global Middleware for Sangiang Ecosystem (sangihe.org)
 * - Handles CORS preflight and headers
 * - Routes chat.sangihe.org / sangiang.sangihe.org to the Sangiang Chatbot UI (/chat/*)
 *   and translate.sangihe.org to the Sangiang Translation Engine UI (/*).
 */

export async function onRequest(context) {
  const { request, env, next } = context;
  const url = new URL(request.url);
  const host = url.hostname.toLowerCase();

  // 1. Handle CORS Preflight
  if (request.method === "OPTIONS") {
    return new Response(null, {
      status: 204,
      headers: {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
      },
    });
  }

  // 2. Domain & Subdomain-aware static asset routing
  const isRootPortalDomain =
    host === "sangihe.org" ||
    host === "www.sangihe.org";

  const isChatSubdomain =
    host.startsWith("chat.") ||
    host.startsWith("chatbot.") ||
    host.startsWith("sangiang.");

  if (isRootPortalDomain && env.ASSETS) {
    if (url.pathname === "/" || url.pathname === "/index.html") {
      const landingUrl = new URL("/landing/", url.origin);
      return env.ASSETS.fetch(new Request(landingUrl.toString(), request));
    }
  }

  if (isChatSubdomain && env.ASSETS) {
    if (url.pathname === "/" || url.pathname === "/index.html") {
      const chatUrl = new URL("/chat/", url.origin);
      return env.ASSETS.fetch(new Request(chatUrl.toString(), request));
    }
    if (url.pathname.startsWith("/static/")) {
      const chatStaticUrl = new URL("/chat" + url.pathname, url.origin);
      return env.ASSETS.fetch(new Request(chatStaticUrl.toString(), request));
    }
  }

  const response = await next();
  const newHeaders = new Headers(response.headers);
  newHeaders.set("Access-Control-Allow-Origin", "*");
  newHeaders.set("Access-Control-Allow-Methods", "GET, POST, OPTIONS");
  newHeaders.set("Access-Control-Allow-Headers", "Content-Type, Authorization");

  return new Response(response.body, {
    status: response.status,
    statusText: response.statusText,
    headers: newHeaders,
  });
}

