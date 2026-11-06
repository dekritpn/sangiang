import {
  SYSTEM_INDONESIAN_TO_SANGIHE,
  SYSTEM_SANGIHE_TO_INDONESIAN,
  applySangiheMorphophonemicRules,
  buildTranslationPrompt,
  callGemini,
  lookupIndonesianTokens,
  lookupSangiheTokens,
  restoreDiacritics,
  retrieveParallelMatches,
  tokenizeWords,
} from "../_lib/sangihe_engine.js";

const IDENTITY_QUERIES = new Set([
  "siapa namamu", "siapa nama kamu", "siapa kamu", "siapa anda",
  "kamu siapa", "anda siapa", "who are you", "what is your name",
  "isai arengu", "isai areng-u", "isai i kau", "arengu kai apa", "areng-u kai apa",
  "isai ngaranu", "isai ngangengu", "sapa ngaramu",
]);

export async function onRequestPost(context) {
  const { request, env } = context;
  const startTime = Date.now();

  try {
    const body = await request.json();
    const cleanInput = String(body.text || "").trim();
    const direction = body.direction || "sangihe_to_id";
    const temperature = typeof body.temperature === "number" ? body.temperature : 0.2;
    const topKParallel = body.top_k_parallel || 3;
    const maxLexical = body.max_lexical || 20;

    if (!["sangihe_to_id", "id_to_sangihe"].includes(direction)) {
      return Response.json(
        { detail: "Direction must be either 'sangihe_to_id' or 'id_to_sangihe'" },
        { status: 400 }
      );
    }

    if (!cleanInput) {
      return Response.json({
        input_text: "",
        translated_text: "",
        direction,
        elapsed_ms: 0,
        model: "Sangiang",
        diacritics_restored: false,
        lexical_entries: [],
        parallel_matches: [],
      });
    }

    const normQuery = cleanInput.toLowerCase().replace(/[?.!,;:"']/g, "").trim();
    if (IDENTITY_QUERIES.has(normQuery)) {
      let identityText = "Saya adalah Sangiang, kecerdasan buatan dengan kemampuan berbahasa Sangihe.";
      if (direction === "id_to_sangihe" || ["isai", "arengu", "areng-u"].some(k => normQuery.includes(k))) {
        identityText = "Iạ kai i Sangiang, kecerdasan buatan mạbiahěng u bisara Sangihe.";
      }
      return Response.json({
        input_text: cleanInput,
        translated_text: identityText,
        direction,
        elapsed_ms: Date.now() - startTime,
        model: "Sangiang",
        diacritics_restored: false,
        lexical_entries: [],
        parallel_matches: [],
      });
    }

    const tokens = tokenizeWords(cleanInput, true);
    const lexicalEntries =
      direction === "sangihe_to_id"
        ? await lookupSangiheTokens(env.DB, tokens, maxLexical)
        : await lookupIndonesianTokens(env.DB, tokens, maxLexical);

    const parallelMatches = await retrieveParallelMatches(env.DB, cleanInput, direction, topKParallel);

    // Check human speaker feedback override in D1
    if (env.DB) {
      try {
        const fbRow = await env.DB.prepare(
          `SELECT corrected_translation FROM translation_feedback
           WHERE direction = ?
             AND lower(trim(input_text)) = lower(?)
             AND corrected_translation != ''
             AND trim(corrected_translation) != trim(machine_translation)
           ORDER BY id DESC LIMIT 1;`
        ).bind(direction, cleanInput).first();

        if (fbRow && fbRow.corrected_translation && fbRow.corrected_translation.trim()) {
          return Response.json({
            input_text: cleanInput,
            translated_text: fbRow.corrected_translation.trim(),
            direction,
            elapsed_ms: Date.now() - startTime,
            model: "Sangiang",
            diacritics_restored: false,
            lexical_entries: lexicalEntries,
            parallel_matches: parallelMatches,
          });
        }
      } catch {}
    }

    const systemPrompt =
      direction === "sangihe_to_id" ? SYSTEM_SANGIHE_TO_INDONESIAN : SYSTEM_INDONESIAN_TO_SANGIHE;
    const userPrompt = buildTranslationPrompt(cleanInput, direction, lexicalEntries, parallelMatches);

    // Check D1 LLM Cache
    const cacheKey = `${direction}::${cleanInput.toLowerCase()}`;
    let rawOutput = null;
    if (env.DB) {
      try {
        const cached = await env.DB.prepare("SELECT response_text FROM llm_cache WHERE cache_key = ? LIMIT 1;")
          .bind(cacheKey)
          .first();
        if (cached && cached.response_text) {
          rawOutput = cached.response_text;
        }
      } catch {}
    }

    if (!rawOutput) {
      rawOutput = await callGemini(env, systemPrompt, userPrompt, temperature);
      if (env.DB && rawOutput) {
        try {
          await env.DB.prepare(
            "INSERT OR REPLACE INTO llm_cache (cache_key, response_text, created_at) VALUES (?, ?, datetime('now'));"
          ).bind(cacheKey, rawOutput).run();
        } catch {}
      }
    }

    let translated = (rawOutput || "").replace(/^["'`\s]+|["'`\s]+$/g, "");
    let diacriticsRestored = false;

    if (direction === "id_to_sangihe") {
      const rest = restoreDiacritics(translated, lexicalEntries, parallelMatches);
      translated = applySangiheMorphophonemicRules(rest.text);
      diacriticsRestored = rest.restored;
    }

    return Response.json({
      input_text: cleanInput,
      translated_text: translated,
      direction,
      elapsed_ms: Date.now() - startTime,
      model: "Sangiang",
      diacritics_restored: diacriticsRestored,
      lexical_entries: lexicalEntries.map(e => ({
        lemma_id: e.lemma_id,
        lema_display: e.lema_display,
        lema_normalized: e.lema_normalized,
        summary_gloss: e.body_plain || e.summary_gloss,
        match_source: e.match_source,
      })),
      parallel_matches: parallelMatches,
    });
  } catch (err) {
    return Response.json({ detail: err.message || String(err) }, { status: 500 });
  }
}

