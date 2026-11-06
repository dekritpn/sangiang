import { lookupIndonesianTokens, lookupSangiheTokens } from "../../_lib/sangihe_engine.js";

export async function onRequestPost(context) {
  const { request, env } = context;
  try {
    const body = await request.json();
    const query = String(body.query || "").trim();
    const direction = body.direction || "sangihe";
    const limit = body.limit || 10;

    const entries =
      direction === "sangihe"
        ? await lookupSangiheTokens(env.DB, [query], limit)
        : await lookupIndonesianTokens(env.DB, [query], limit);

    return Response.json({
      query,
      direction,
      results: entries.map(e => ({
        lemma_id: e.lemma_id,
        lema_display: e.lema_display,
        lema_normalized: e.lema_normalized,
        summary_gloss: e.summary_gloss,
        sublemmas: e.sublemmas || [],
        match_source: e.match_source,
      })),
    });
  } catch (err) {
    return Response.json({ detail: err.message || String(err) }, { status: 500 });
  }
}

