import {
  SANGIANG_SYSTEM_PROMPT,
  applySangiheMorphophonemicRules,
  callGeminiPayload,
  detectUserLanguage,
  lookupIndonesianTokens,
  lookupSangiheTokens,
  retrieveParallelMatches,
  tokenizeWords,
} from "../_lib/sangihe_engine.js";

async function augmentPromptWithLexicon(db, userText) {
  const userLang = detectUserLanguage(userText);
  const langDirective =
    userLang === "sangihe"
      ? "[INSTRUKSI BAHASA & MORFOFONEMIK WAJIB: Pengguna berbicara kepada Anda dalam BAHASA SANGIHE. Anda WAJIB menjawab 100% SEPENUHNYA DALAM BAHASA SANGIHE MURNI! DILARANG KERAS mencampur dengan Bahasa Indonesia sedikit pun! WAJIB patuhi hukum perubahan bunyi (lenisi) sesudah suku kata terbuka: konsonan 'b-' menjadi 'w-' dan 'd-' menjadi 'r-' sesudah vokal terbuka, serta gunakan ligatur '-ng' pada frasa genitif (misalnya: tulis 'werang Sangihẹ̌', 'su werang Sangihẹ̌', 'u werang Sangihẹ̌', atau 'berang u Sangihẹ̌' — DILARANG KERAS menulis 'bera Sangihe' tanpa '-ng' dan tanpa lenisi 'w-'!). Gunakan 'mẹ̌bera-wera', 'mal᷊uasẹ̌', dan 'ringangu' sesudah kata berakhiran vokal terbuka.]"
      : "[INSTRUKSI BAHASA WAJIB: Pengguna berbicara kepada Anda dalam BAHASA INDONESIA. Anda WAJIB menjawab SEPENUHNYA DALAM BAHASA INDONESIA sebagai teman diskusi yang hangat, cerdas, dan akrab (tidak perlu mencampur kalimat Bahasa Sangihe kecuali pengguna secara eksplisit memintanya).]";

  if (!db) return { hint: `\n\n${langDirective}`, userLang };
  try {
    const words = tokenizeWords(userText, false);
    if (!words.length) return { hint: `\n\n${langDirective}`, userLang };

    const sghEntries = await lookupSangiheTokens(db, words, 10);
    const idEntries = await lookupIndonesianTokens(db, words, 10);

    const seen = new Set();
    const entries = [];
    for (const e of [...sghEntries, ...idEntries]) {
      const key = (e.lema_display || e.lema_normalized || "").toLowerCase();
      if (key && !seen.has(key)) {
        seen.add(key);
        entries.push(e);
      }
    }

    const lexHints = [];
    for (const e of entries.slice(0, 14)) {
      const norm = (e.lema_normalized || "").toLowerCase();
      if (norm === "ia" || norm === "iạ") {
        lexHints.push("- **iạ**: [pron] SAYA / AKU (kata ganti orang pertama tunggal, BUKAN kata ganti orang ketiga 'ia'/'dia'!)");
        continue;
      } else if (norm === "sie" || norm === "isie") {
        lexHints.push("- **i sie**: [pron] DIA / IA / BELIAU (kata ganti orang ketiga tunggal)");
        continue;
      } else if (norm === "kau" || norm === "ikau") {
        lexHints.push("- **i kau**: [pron] ENGKAU / KAMU (kata ganti orang kedua tunggal)");
        continue;
      } else if (norm === "bera" || norm === "wera" || norm === "berang" || norm === "werang") {
        lexHints.push("- **werang Sangihẹ̌ / berang u Sangihẹ̌**: [n] bahasa Sangihe (sesudah vokal terbuka wajib lenisi b->w menjadi 'werang Sangihẹ̌', misal: 'su werang Sangihẹ̌', 'u werang Sangihẹ̌'; DILARANG menulis 'bera Sangihe'!)");
        continue;
      }
      const defn = String(e.summary_gloss || e.body_plain || "").replace(/\n/g, " ").trim().slice(0, 260);
      lexHints.push(`- **${e.lema_display}**: ${defn}`);
    }

    let matches = await retrieveParallelMatches(db, userText, "sangihe_to_id", 3);
    if (!matches.length) {
      matches = await retrieveParallelMatches(db, userText, "id_to_sangihe", 3);
    }
    const parHints = matches.map(
      m => `- Sangihe: "${(m.sangihe || "").slice(0, 180)}" -> Indonesia: "${(m.indonesian || "").slice(0, 180)}"`
    );

    const sections = [langDirective];
    if (lexHints.length) {
      sections.push("[Rujukan Kamus Sangihe-Indonesia Modern (Internal - Jangan ditampilkan sebagai daftar kamus)]:\n" + lexHints.join("\n"));
    }
    if (parHints.length) {
      sections.push("[Contoh Kalimat Paralel Korpus]:\n" + parHints.join("\n"));
    }
    return { hint: "\n\n" + sections.join("\n\n"), userLang };
  } catch {
    return { hint: `\n\n${langDirective}`, userLang };
  }
}

export async function onRequestPost(context) {
  const { request, env } = context;
  try {
    const req = await request.json();
    const messages = req.messages || [];
    const temperature = typeof req.temperature === "number" ? req.temperature : 0.4;
    const stream = req.stream !== false;

    const apiKey = env.GEMINI_API_KEY || env.GOOGLE_API_KEY;
    if (!apiKey && !env.AI) {
      return Response.json({ detail: "GEMINI_API_KEY tidak ditemukan di Environment Variables." }, { status: 500 });
    }

    let sysText = SANGIANG_SYSTEM_PROMPT;
    const geminiContents = [];
    let activeUserLang = "indonesian";

    for (let i = 0; i < messages.length; i++) {
      const m = messages[i];
      if (m.role === "system") {
        sysText = m.content + "\n";
      } else {
        let content = m.content || "";
        if (i === messages.length - 1 && m.role === "user") {
          const { hint, userLang } = await augmentPromptWithLexicon(env.DB, content);
          activeUserLang = userLang;
          if (hint) content += hint;
        }
        geminiContents.push({
          role: m.role === "assistant" ? "model" : "user",
          parts: [{ text: content }],
        });
      }
    }

    const geminiPayload = {
      contents: geminiContents,
      systemInstruction: { parts: [{ text: sysText.trim() }] },
      generationConfig: {
        temperature,
        topP: 0.9,
        maxOutputTokens: 1024,
      },
    };

    let rawReply = "";
    try {
      rawReply = await callGeminiPayload(env, geminiPayload, temperature);
    } catch (err) {
      const errMsg = err.message || "Layanan Sangiang sedang sibuk, silakan coba sesaat lagi.";
      if (!stream) {
        return Response.json({ detail: errMsg }, { status: 500 });
      }
      const errPayload = `data: ${JSON.stringify({ error: errMsg })}\n\n`;
      return new Response(errPayload, {
        headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
      });
    }

    const finalReply =
      activeUserLang === "sangihe" ? applySangiheMorphophonemicRules(rawReply) : rawReply;

    if (!stream) {
      return Response.json({ response: finalReply, model: "Sangiang" });
    }

    // Stream the morphophonemically-verified reply smoothly as SSE chunks
    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const encoder = new TextEncoder();

    (async () => {
      try {
        const words = finalReply.split(/(\s+)/);
        let chunkBuf = "";
        for (let i = 0; i < words.length; i++) {
          chunkBuf += words[i];
          if (chunkBuf.length >= 28 || i === words.length - 1) {
            await writer.write(
              encoder.encode(`data: ${JSON.stringify({ chunk: chunkBuf, done: false, model: "Sangiang" })}\n\n`)
            );
            chunkBuf = "";
          }
        }
        await writer.write(
          encoder.encode(`data: ${JSON.stringify({ chunk: "", done: true, model: "Sangiang" })}\n\n`)
        );
      } finally {
        await writer.close();
      }
    })();

    return new Response(readable, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (err) {
    return Response.json({ detail: err.message || String(err) }, { status: 500 });
  }
}
