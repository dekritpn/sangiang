export async function onRequestGet(context) {
  const { env } = context;
  let corpusCount = 30307;
  let lexOk = Boolean(env.DB);
  if (env.DB) {
    try {
      const row = await env.DB.prepare("SELECT COUNT(*) AS cnt FROM parallel_sentences;").first();
      if (row && typeof row.cnt === "number") corpusCount = row.cnt;
    } catch {}
  }
  const geminiOk = Boolean(env.GEMINI_API_KEY || env.GOOGLE_API_KEY);
  return Response.json({
    status: geminiOk && lexOk ? "healthy" : "degraded",
    ollama_connected: geminiOk,
    corpus_sentences_count: corpusCount,
    lexical_database_available: lexOk,
  });
}

