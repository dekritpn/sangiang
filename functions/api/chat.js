import {
  SANGIANG_SYSTEM_PROMPT,
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
      ? "[INSTRUKSI BAHASA WAJIB: Pengguna berbicara kepada Anda dalam BAHASA SANGIHE. Anda WAJIB menjawab 100% SEPENUHNYA DALAM BAHASA SANGIHE MURNI! DILARANG KERAS mencampur dengan kalimat atau terjemahan Bahasa Indonesia sedikit pun! Susunlah seluruh kalimat Bahasa Sangihe Anda HANYA menggunakan kosakata Sangihe asli yang terverifikasi di Kamus Inti & Rujukan Kamus di bawah (tanpa kata karangan sendiri), sehingga jika jawaban Sangihe Anda dimasukkan ke Mesin Penerjemah Sangiang, hasilnya adalah kalimat Bahasa Indonesia yang 100% wajar dan masuk akal.]"
      : "[INSTRUKSI BAHASA WAJIB: Pengguna berbicara kepada Anda dalam BAHASA INDONESIA. Anda WAJIB menjawab SEPENUHNYA DALAM BAHASA INDONESIA sebagai teman diskusi yang hangat, cerdas, dan akrab (tidak perlu mencampur kalimat Bahasa Sangihe kecuali pengguna secara eksplisit memintanya).]";

  if (!db) return `\n\n${langDirective}`;
  try {
    const words = tokenizeWords(userText, false);
    if (!words.length) return `\n\n${langDirective}`;

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
    return "\n\n" + sections.join("\n\n");
  } catch {
    return `\n\n${langDirective}`;
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
    if (!apiKey) {
      return Response.json({ detail: "GEMINI_API_KEY tidak ditemukan di Environment Variables." }, { status: 500 });
    }

    let sysText = SANGIANG_SYSTEM_PROMPT;
    const geminiContents = [];

    for (let i = 0; i < messages.length; i++) {
      const m = messages[i];
      if (m.role === "system") {
        sysText = m.content + "\n";
      } else {
        let content = m.content || "";
        if (i === messages.length - 1 && m.role === "user") {
          const hint = await augmentPromptWithLexicon(env.DB, content);
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

    if (!stream) {
      const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key=${encodeURIComponent(apiKey)}`;
      const res = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(geminiPayload),
      });
      const data = await res.json();
      const cands = data.candidates || [];
      const parts = (cands[0] && cands[0].content && cands[0].content.parts) || [];
      const content = parts.map(p => p.text || "").join("");
      return Response.json({ response: content, model: "Sangiang" });
    }

    // Streaming SSE response
    const sseUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:streamGenerateContent?alt=sse&key=${encodeURIComponent(apiKey)}`;
    const upstream = await fetch(sseUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(geminiPayload),
    });

    if (!upstream.ok || !upstream.body) {
      const errBody = await upstream.text();
      const errPayload = `data: ${JSON.stringify({ error: `Gemini API HTTP ${upstream.status}: ${errBody}` })}\n\n`;
      return new Response(errPayload, {
        headers: { "Content-Type": "text/event-stream", "Cache-Control": "no-cache" },
      });
    }

    const { readable, writable } = new TransformStream();
    const writer = writable.getWriter();
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    (async () => {
      const reader = upstream.body.getReader();
      let buffer = "";
      try {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";
          for (const rawLine of lines) {
            const line = rawLine.trim();
            if (!line.startsWith("data:")) continue;
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;
            try {
              const data = JSON.parse(jsonStr);
              const cands = data.candidates || [];
              if (cands.length) {
                const parts = (cands[0].content && cands[0].content.parts) || [];
                const chunk = parts.map(p => p.text || "").join("");
                if (chunk) {
                  await writer.write(
                    encoder.encode(`data: ${JSON.stringify({ chunk, done: false, model: "Sangiang" })}\n\n`)
                  );
                }
              }
            } catch {}
          }
        }
        await writer.write(
          encoder.encode(`data: ${JSON.stringify({ chunk: "", done: true, model: "Sangiang" })}\n\n`)
        );
      } catch (e) {
        await writer.write(
          encoder.encode(`data: ${JSON.stringify({ error: e.message || String(e) })}\n\n`)
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

