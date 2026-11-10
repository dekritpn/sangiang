/**
 * Cloudflare Worker / Pages Function: /v1/tts
 * Text-to-Speech Engine for Sangihe (sxn) and Indonesian (id)
 * 
 * Supports:
 * 1. Native Cloudflare Edge Gemini Multi-Modal TTS (Audio 24kHz Mono WAV)
 *    - Uses env.GEMINI_API_KEY (already available in Cloudflare Worker)
 *    - Automatically handles voice mapping & expression:
 *      * 'male_standard' -> 'Puck'
 *      * 'male_elder'    -> 'Charon'
 *      * 'female_natural'-> 'Kore'
 *      * 'female_youthful'-> 'Aoede'
 *      * 'expressive_calm'-> 'Fenrir'
 *      * 'expressive_excited'-> 'Leda'
 * 2. Custom local/remote TTS Backend (env.TTS_BACKEND_URL)
 * 3. Hugging Face Inference Router (env.HF_TOKEN)
 */

function normalizeSangiheTtsText(text) {
  if (!text) return "";
  let t = text.normalize("NFC");
  t = t.replace(/\(\d+:\d+\)/g, ""); // Hapus rujukan ayat
  t = t.replace(/["“”«»_~]/g, "");
  t = t.replace(/[;:—–]/g, ",");
  t = t.replace(/\s+/g, " ").trim();
  return t;
}

// Konversi 16-bit PCM Linear L16 ke format WAV Container
function pcmToWav(pcmBytes, sampleRate = 24000, numChannels = 1, bitsPerSample = 16) {
  const byteRate = sampleRate * numChannels * (bitsPerSample / 8);
  const blockAlign = numChannels * (bitsPerSample / 8);
  const dataSize = pcmBytes.byteLength;
  const buffer = new ArrayBuffer(44 + dataSize);
  const view = new DataView(buffer);

  // RIFF header
  writeString(view, 0, "RIFF");
  view.setUint32(4, 36 + dataSize, true);
  writeString(view, 8, "WAVE");

  // fmt subchunk
  writeString(view, 12, "fmt ");
  view.setUint32(16, 16, true); // Subchunk1Size (16 for PCM)
  view.setUint16(20, 1, true);  // AudioFormat (1 = PCM)
  view.setUint16(22, numChannels, true);
  view.setUint32(24, sampleRate, true);
  view.setUint32(28, byteRate, true);
  view.setUint16(32, blockAlign, true);
  view.setUint16(34, bitsPerSample, true);

  // data subchunk
  writeString(view, 36, "data");
  view.setUint32(40, dataSize, true);

  // Copy PCM samples
  const wavBytes = new Uint8Array(buffer);
  wavBytes.set(pcmBytes, 44);
  return wavBytes;
}

function writeString(view, offset, string) {
  for (let i = 0; i < string.length; i++) {
    view.setUint8(offset + i, string.charCodeAt(i));
  }
}

// Mapping preset ke nama suara prebuilt Gemini TTS
const PRESET_GEMINI_VOICES = {
  male_standard: { voice: "Puck", desc: "wibawa, nada pria netral dan artikulasi jelas" },
  male_elder: { voice: "Charon", desc: "berat, tempo agak lambat, bijak, nada pria tua/tetua adat" },
  female_natural: { voice: "Kore", desc: "ramah, hangat, nada wanita natural dan bersahabat" },
  female_youthful: { voice: "Aoede", desc: "ceria, enerjik, cerah, nada wanita muda" },
  expressive_calm: { voice: "Fenrir", desc: "sangat tenang, lembut, nada santai meditatif" },
  expressive_excited: { voice: "Leda", desc: "antusias, bersemangat, ceria, intonasi dinamis" },
};

export async function onRequestPost(context) {
  const { request, env } = context;

  try {
    const body = await request.json().catch(() => ({}));
    const rawText = String(body.text || "").trim();
    const lang = String(body.lang || "sxn").toLowerCase();
    const preset = String(body.preset || "male_standard");
    const speed = typeof body.speed === "number" ? body.speed : 1.0;

    if (!rawText) {
      return Response.json({ detail: "Parameter 'text' tidak boleh kosong." }, { status: 400 });
    }

    // 1. Jika bahasa target adalah Bahasa Indonesia
    if (lang === "id" || lang === "ind" || lang === "indonesian") {
      return Response.json({
        provider: "client-speech-synthesis",
        lang: "id-ID",
        text: rawText,
        preset,
        speed,
        message: "Gunakan Web Speech API di peramban untuk bahasa Indonesia (id-ID)."
      });
    }

    // 2. Bahasa Sangihe (sxn)
    const cleanText = normalizeSangiheTtsText(rawText);

    // Opsi A: Jika env.TTS_BACKEND_URL dikonfigurasi
    if (env.TTS_BACKEND_URL) {
      try {
        const backendResp = await fetch(`${env.TTS_BACKEND_URL.replace(/\/+$/, "")}/synthesize`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ text: cleanText, lang: "sxn", preset, speed })
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

    // Opsi B: Gunakan Google Gemini Audio TTS Engine (Aktif via env.GEMINI_API_KEY)
    const geminiKey = env.GEMINI_API_KEY || env.GOOGLE_API_KEY;
    if (geminiKey) {
      try {
        const voiceInfo = PRESET_GEMINI_VOICES[preset] || PRESET_GEMINI_VOICES.male_standard;
        const geminiUrl = `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent?key=${encodeURIComponent(geminiKey)}`;
        
        const payload = {
          contents: [{
            parts: [{
              text: `Ucapkan kalimat Bahasa Sangihe berikut secara alami dengan gaya ${voiceInfo.desc}:\n"${cleanText}"`
            }]
          }],
          generationConfig: {
            responseModalities: ["AUDIO"],
            speechConfig: {
              voiceConfig: {
                prebuiltVoiceConfig: {
                  voiceName: voiceInfo.voice
                }
              }
            }
          }
        };

        // Forward melalui Durable Object jika tersedia untuk bypass geo-restrictions
        let geminiResp;
        if (env.GEMINI_PROXY) {
          const id = env.GEMINI_PROXY.idFromName("sangiang-us-west-v1");
          const stub = env.GEMINI_PROXY.get(id, { locationHint: "wnam" });
          geminiResp = await stub.fetch("https://gemini-proxy/generate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ url: geminiUrl, payload })
          });
        } else {
          geminiResp = await fetch(geminiUrl, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
          });
        }

        if (geminiResp.ok) {
          const geminiData = await geminiResp.json();
          const candidate = geminiData.candidates?.[0];
          const part = candidate?.content?.parts?.[0];
          const base64Data = part?.inlineData?.data;

          if (base64Data) {
            // Decode base64 PCM data
            const binaryString = atob(base64Data);
            const pcmBytes = new Uint8Array(binaryString.length);
            for (let i = 0; i < binaryString.length; i++) {
              pcmBytes[i] = binaryString.charCodeAt(i);
            }

            // Kemas ke WAV 24kHz 16-bit Mono
            const wavAudio = pcmToWav(pcmBytes, 24000, 1, 16);
            return new Response(wavAudio.buffer, {
              status: 200,
              headers: {
                "Content-Type": "audio/wav",
                "Cache-Control": "public, max-age=86400",
              }
            });
          }
        }
      } catch (err) {
        console.warn("Gemini TTS synthesis failed:", err);
      }
    }

    // Opsi C: Hugging Face Router
    const hfToken = env.HF_TOKEN || env.HUGGINGFACE_TOKEN;
    if (hfToken) {
      try {
        const hfResp = await fetch("https://router.huggingface.co/hf-inference/models/facebook/mms-tts-sxn", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": `Bearer ${hfToken}`
          },
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
    }

    // Fallback jika tidak ada backend audio yang siap
    return Response.json({
      success: false,
      error: "TTS_UNAVAILABLE",
      detail: "Layanan audio sedang tidak tersedia.",
      clean_text: cleanText,
      lang: "sxn"
    }, { status: 503 });

  } catch (error) {
    return Response.json({ detail: `Gagal memproses permintaan audio: ${error.message}` }, { status: 500 });
  }
}
