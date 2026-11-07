export async function onRequestGet(context) {
  const { env } = context;
  const corpusCount = 30308;
  let lexOk = Boolean(env.DB);
  if (env.DB) {
    try {
      const row = await env.DB.prepare("SELECT 1 AS ok;").first();
      lexOk = Boolean(row && row.ok === 1);
    } catch {
      lexOk = false;
    }
  }
  const geminiOk = Boolean(env.GEMINI_API_KEY || env.GOOGLE_API_KEY);
  return Response.json({
    status: geminiOk && lexOk ? "healthy" : "degraded",
    ollama_connected: geminiOk,
    corpus_sentences_count: corpusCount,
    lexical_database_available: lexOk,
  });
}

