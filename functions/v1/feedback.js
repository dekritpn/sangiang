import { normalizeSangihe } from "../_lib/sangihe_engine.js";

export async function onRequestPost(context) {
  const { request, env } = context;
  try {
    const body = await request.json();
    const nowIso = new Date().toISOString();
    const direction = body.direction || "sangihe_to_id";
    const inputText = String(body.input_text || "").trim();
    const machineTranslation = String(body.machine_translation || "").trim();
    const isCorrect = body.is_correct ? 1 : 0;
    const correctedTranslation = String(body.corrected_translation || "").trim();
    const notes = String(body.notes || "").trim();
    const clientIp =
      request.headers.get("cf-connecting-ip") ||
      request.headers.get("x-forwarded-for") ||
      "";

    let feedbackId = Date.now();
    if (env.DB) {
      const res = await env.DB.prepare(
        `INSERT INTO translation_feedback (
          created_at, direction, input_text, machine_translation,
          is_correct, corrected_translation, notes, client_ip
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);`
      )
        .bind(nowIso, direction, inputText, machineTranslation, isCorrect, correctedTranslation, notes, clientIp)
        .run();
      if (res && res.meta && res.meta.last_row_id) {
        feedbackId = res.meta.last_row_id;
      }

      // Auto-sync into parallel_sentences in D1 so Sangiang learns immediately
      const targetTxt = !isCorrect && correctedTranslation ? correctedTranslation : machineTranslation;
      if (inputText && targetTxt) {
        const saTxt = direction === "sangihe_to_id" ? inputText : targetTxt;
        const idTxt = direction === "sangihe_to_id" ? targetTxt : inputText;
        const saNorm = normalizeSangihe(saTxt).toLowerCase();
        const refId = `USER_FB_${feedbackId}`;
        await env.DB.prepare(
          `INSERT INTO parallel_sentences (source_domain, reference_id, sangihe_text, sangihe_normalized, indonesian_tb, indonesian_bimk)
           VALUES ('user_feedback', ?, ?, ?, ?, ?);`
        )
          .bind(refId, saTxt, saNorm, idTxt, idTxt)
          .run();
      }
    }

    return Response.json({
      status: "ok",
      feedback_id: feedbackId,
      message: "Terima kasih! Masukan Anda telah tersimpan untuk menyempurnakan Sangiang.",
    });
  } catch (err) {
    return Response.json({ detail: err.message || String(err) }, { status: 500 });
  }
}

export async function onRequestGet(context) {
  const { request, env } = context;
  const url = new URL(request.url);
  const limit = Number(url.searchParams.get("limit") || 50);
  if (!env.DB) {
    return Response.json({ total_returned: 0, feedback: [] });
  }
  const { results } = await env.DB.prepare(
    "SELECT * FROM translation_feedback ORDER BY id DESC LIMIT ?;"
  ).bind(limit).all();
  return Response.json({
    total_returned: (results || []).length,
    feedback: results || [],
  });
}

