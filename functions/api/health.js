export async function onRequestGet(context) {
  const { env } = context;
  const geminiOk = Boolean(env.GEMINI_API_KEY || env.GOOGLE_API_KEY);
  return Response.json({
    status: "healthy",
    service: "Sangiang Chatbot",
    port: 443,
    ollama_connected: geminiOk,
    default_model: "Sangiang",
    initiator: "Yayasan Cipta Manggala Dwipa",
    engineering: "Divisi DigiLab CMD",
  });
}

