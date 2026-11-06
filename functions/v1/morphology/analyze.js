import { analyzeWord } from "../../_lib/sangihe_engine.js";

export async function onRequestPost(context) {
  try {
    const body = await context.request.json();
    const analysis = analyzeWord(String(body.word || ""));
    return Response.json(analysis);
  } catch (err) {
    return Response.json({ detail: err.message || String(err) }, { status: 500 });
  }
}

