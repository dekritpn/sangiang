/**
 * Cloudflare Worker / Pages Function: /v1/tts
 * Text-to-Speech proxy and provider router for Sangihe & Indonesian
 * 
 * Supports:
 * - Language: "sxn" (Sangihe) or "id" (Indonesian)
 * - Providers:
 *   1. Direct Hugging Face Inference Router (facebook/mms-tts-sxn) if HF_TOKEN is configured in env.
 *   2. Custom self-hosted / backend TTS endpoint if TTS_BACKEND_URL is configured in env.
 *   3. Informative metadata response explaining client-side native TTS for Indonesian or audio capability status.
 */

// Normalisasi karakter ortografi & diakritik Sangihe sebelum sintesis fonetik MMS-TTS
function normalizeSangiheTtsText(text) {
  if (!text) return "";
  let t = text.normalize("NFC");
  t = t.replace(/\(\d+:\d+\)/g, ""); // Hapus rujukan ayat misal (1:1)
  t = t.replace(/["“”«»_~]/g, "");
  t = t.replace(/[;:—–]/g, ",");
  t = t.replace(/\s+/g, " ").trim().toLowerCase();
  return t;
}

export async function onRequestPost(context) {
  const { request, env } = context;

  try {
    const body = await request.json().catch(() => ({}));
    const rawText = String(body.text || "").trim();
    const lang = String(body.lang || "sxn").toLowerCase(); // "sxn" or "id"

    if (!rawText) {
      return Response.json({ detail: "Parameter 'text' tidak boleh kosong." }, { status: 400 });
    }

    // 1. Jika bahasa target adalah Bahasa Indonesia, arahkan client untuk menggunakan Web Speech API
    if (lang === "id" || lang === "ind" || lang === "indonesian") {
      return Response.json({
        provider: "client-speech-synthesis",
        lang: "id-ID",
        text: rawText,
        message: "Gunakan Web Speech API di peramban untuk bahasa Indonesia (id-ID)."
      });
    }

    // 2. Bahasa Sangihe (sxn)
    const cleanText = normalizeSangiheTtsText(rawText);

    // Opsi A: Jika env.TTS_BACKEND_URL dikonfigurasi (misal backend Python Sangihe Speech Engine)
    if (env.TTS_BACKEND_URL) {
      try {
        const backendResp = await fetch(`${env.TTS_BACKEND_URL.replace(/\/+$/, "")}/synthesize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: cleanText, lang: "sxn" })
        });

        if (backendResp.ok) {
          const audioBytes = await backendResp.arrayBuffer();
          return new Response(audioBytes, {
            status: 200,
            headers: {
              "Content-Type": backendResp.headers.get("Content-Type") || "audio/wav",
              "Cache-Control": "public, max-age=86400",
            }
          });
        }
      } catch (err) {
        console.warn("TTS Backend fetch failed:", err);
      }
    }

    // Opsi B: Hugging Face Inference API / Serverless (facebook/mms-tts-sxn)
    const hfToken = env.HF_TOKEN || env.HUGGINGFACE_TOKEN;
    const hfHeaders = { "Content-Type": "application/json" };
    if (hfToken) {
      hfHeaders["Authorization"] = `Bearer ${hfToken}`;
    }

    try {
      const hfResp = await fetch("https://router.huggingface.co/hf-inference/models/facebook/mms-tts-sxn", {
        method: "POST",
        headers: hfHeaders,
        body: JSON.stringify({ inputs: cleanText })
      });

      if (hfResp.ok) {
        const audioBytes = await hfResp.arrayBuffer();
        return new Response(audioBytes, {
          status: 200,
          headers: {
            "Content-Type": hfResp.headers.get("Content-Type") || "audio/flac",
            "Cache-Control": "public, max-age=86400",
          }
        });
      }
    } catch (err) {
      console.warn("HF router fetch error:", err);
    }

    // Jika belum ada backend TTS aktif atau token HF belum disetel di Cloudflare Secrets
    return Response.json({
      success: false,
      error: "TTS_BACKEND_NOT_CONFIGURED",
      detail: "Endpoint Text-to-Speech Sangihe memerlukan secret HF_TOKEN atau TTS_BACKEND_URL pada Cloudflare Worker.",
      clean_text: cleanText,
      lang: "sxn"
    }, { status: 503 });

  } catch (error) {
    return Response.json({ detail: `Gagal memproses permintaan audio: ${error.message}` }, { status: 500 });
  }
}
