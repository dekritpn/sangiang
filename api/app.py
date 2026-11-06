"""FastAPI REST Service for Sangihe Translation Engine."""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from api.schemas import (
    DictionaryLookupRequest,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
    ModelInfo,
    ModelsResponse,
    MorphologyRequest,
    MorphologyResponse,
    TranslationRequest,
    TranslationResponse,
)
from engine.translator import SangiheTranslationEngine
from morphology.stemmer import analyze_word

app = FastAPI(
    title="Sangiang Translation Engine API",
    description="Bidirectional translation engine for Bahasa Sangihe and Bahasa Indonesia powered by Sangiang.",
    version="1.0.0",
)

# Enable CORS for web apps or Flutter clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static folder
STATIC_DIR = Path(__file__).resolve().parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=FileResponse)
@app.get("/index.html", response_class=FileResponse)
def serve_index():
    """Serve the interactive Translation Workbench web UI."""
    index_file = STATIC_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Web UI index.html not found")
    return FileResponse(str(index_file))


# Engine singleton
engine: SangiheTranslationEngine = None


@app.on_event("startup")
def startup_event():
    global engine
    engine = SangiheTranslationEngine()


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Check status of translation engine, Ollama, and database components."""
    ollama_ok = engine.llm_client.is_alive() if engine else False
    lex_ok = os.path.exists(engine.lexical_retriever.db_path) if engine else False

    corpus_count = 0
    if engine and os.path.exists(engine.semantic_retriever.db_path):
        try:
            with sqlite3.connect(engine.semantic_retriever.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM parallel_sentences;")
                corpus_count = cur.fetchone()[0]
        except Exception:
            pass

    return HealthResponse(
        status="healthy" if (ollama_ok and lex_ok) else "degraded",
        ollama_connected=ollama_ok,
        corpus_sentences_count=corpus_count,
        lexical_database_available=lex_ok,
    )


@app.get("/v1/models", response_model=ModelsResponse)
def get_available_models():
    """Return Sangiang as the unified public model name."""
    if not engine:
        raise HTTPException(status_code=503, detail="Translation engine not initialized")

    return ModelsResponse(
        active_model="Sangiang",
        available_models=[
            ModelInfo(
                name="Sangiang",
                is_active=True,
                is_finetuned=True,
            )
        ],
    )


@app.post("/v1/translate", response_model=TranslationResponse)
def translate_endpoint(req: TranslationRequest):
    """Translate text between Bahasa Sangihe and Bahasa Indonesia."""
    if not engine:
        raise HTTPException(status_code=503, detail="Translation engine not initialized")

    if req.direction not in ("sangihe_to_id", "id_to_sangihe"):
        raise HTTPException(
            status_code=400,
            detail="Direction must be either 'sangihe_to_id' or 'id_to_sangihe'",
        )

    try:
        res = engine.translate(
            text=req.text,
            direction=req.direction,
            model=req.model,
            temperature=req.temperature,
            top_k_parallel=req.top_k_parallel,
            max_lexical=req.max_lexical,
        )

        lex_items = [
            {
                "lemma_id": e.lemma_id,
                "lema_display": e.lema_display,
                "lema_normalized": e.lema_normalized,
                "summary_gloss": e.body_plain if e.body_plain else e.summary_gloss,
                "match_source": e.match_source,
            }
            for e in res.lexical_entries
        ]

        par_items = [
            {
                "reference_id": m.reference_id,
                "source_domain": m.source_domain,
                "sangihe": m.sangihe,
                "indonesian": m.indonesian,
                "score": round(m.score, 4),
            }
            for m in res.parallel_matches
        ]

        return TranslationResponse(
            input_text=res.input_text,
            translated_text=res.translated_text,
            direction=res.direction,
            elapsed_ms=round(res.elapsed_ms, 2),
            model="Sangiang",
            diacritics_restored=res.diacritics_restored,
            lexical_entries=lex_items,
            parallel_matches=par_items,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/v1/morphology/analyze", response_model=MorphologyResponse)
def analyze_morphology(req: MorphologyRequest):
    """Analyze affixes, infixes, and candidate root stems for a Sangihe word."""
    analysis = analyze_word(req.word)
    return MorphologyResponse(
        surface=analysis.surface,
        normalized=analysis.normalized,
        is_reduplicated=analysis.is_reduplicated,
        prefixes=analysis.prefixes,
        infixes=analysis.infixes,
        suffixes=analysis.suffixes,
        candidate_stems=analysis.candidate_stems,
    )


@app.post("/v1/dictionary/lookup")
def dictionary_lookup(req: DictionaryLookupRequest):
    """Direct dictionary lookup in Steller-Aebersold SQLite."""
    if not engine:
        raise HTTPException(status_code=503, detail="Engine not ready")

    if req.direction == "sangihe":
        entries = engine.lexical_retriever.lookup_sangihe_tokens(
            [req.query], max_results=req.limit
        )
    else:
        entries = engine.lexical_retriever.lookup_indonesian_tokens(
            [req.query], max_results=req.limit
        )

    return {
        "query": req.query,
        "direction": req.direction,
        "results": [
            {
                "lemma_id": e.lemma_id,
                "lema_display": e.lema_display,
                "lema_normalized": e.lema_normalized,
                "summary_gloss": e.summary_gloss,
                "sublemmas": e.sublemmas,
                "match_source": e.match_source,
            }
            for e in entries
        ],
    }


FEEDBACK_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "user_feedback.sqlite"
FEEDBACK_JSONL_PATH = Path(__file__).resolve().parent.parent / "data" / "user_feedback.jsonl"


def _init_feedback_db() -> None:
    FEEDBACK_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS translation_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                direction TEXT NOT NULL,
                input_text TEXT NOT NULL,
                machine_translation TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                corrected_translation TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                client_ip TEXT DEFAULT ''
            );
            """
        )


@app.post("/v1/feedback", response_model=FeedbackResponse)
def submit_feedback(req: FeedbackRequest, request: Request):
    """Store user feedback and translation corrections (works locally and via Cloudflare Tunnel)."""
    _init_feedback_db()
    now_iso = datetime.now().isoformat()
    # Support Cloudflare Tunnel header (CF-Connecting-IP) or X-Forwarded-For
    client_ip = (
        request.headers.get("cf-connecting-ip")
        or request.headers.get("x-forwarded-for")
        or (request.client.host if request.client else "")
    )
    corr = (req.corrected_translation or "").strip()
    notes = (req.notes or "").strip()

    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO translation_feedback (
                created_at, direction, input_text, machine_translation,
                is_correct, corrected_translation, notes, client_ip
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                now_iso,
                req.direction,
                req.input_text.strip(),
                req.machine_translation.strip(),
                1 if req.is_correct else 0,
                corr,
                notes,
                client_ip,
            ),
        )
        feedback_id = cur.lastrowid

    # Append to JSONL log for easy corpus/training inspection
    log_record = {
        "id": feedback_id,
        "created_at": now_iso,
        "direction": req.direction,
        "input_text": req.input_text.strip(),
        "machine_translation": req.machine_translation.strip(),
        "is_correct": req.is_correct,
        "corrected_translation": corr,
        "notes": notes,
    }
    with open(FEEDBACK_JSONL_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(log_record, ensure_ascii=False) + "\n")

    # Automatically add confirmed or corrected sentences to parallel_corpus.sqlite for BM25 RAG
    try:
        from morphology.normalizer import normalize_sangihe
        target_txt = corr if (not req.is_correct and corr) else req.machine_translation.strip()
        inp_txt = req.input_text.strip()
        if inp_txt and target_txt and engine and engine.semantic_retriever.db_path.exists():
            sa_txt = inp_txt if req.direction == "sangihe_to_id" else target_txt
            id_txt = target_txt if req.direction == "sangihe_to_id" else inp_txt
            sa_norm = normalize_sangihe(sa_txt).lower()
            ref_id = f"USER_FB_{feedback_id}"
            with sqlite3.connect(str(engine.semantic_retriever.db_path)) as p_conn:
                pc = p_conn.cursor()
                pc.execute(
                    """
                    INSERT INTO parallel_sentences (source_domain, reference_id, sangihe_text, sangihe_normalized, indonesian_tb, indonesian_bimk)
                    VALUES ('user_feedback', ?, ?, ?, ?, ?);
                    """,
                    (ref_id, sa_txt, sa_norm, id_txt, id_txt),
                )
                new_rowid = pc.lastrowid
                pc.execute(
                    """
                    INSERT INTO parallel_fts (rowid, sangihe_normalized, indonesian_tb, indonesian_bimk)
                    VALUES (?, ?, ?, ?);
                    """,
                    (new_rowid, sa_norm, id_txt, id_txt),
                )
                p_conn.commit()
    except Exception:
        pass

    return FeedbackResponse(
        status="ok",
        feedback_id=feedback_id,
        message="Terima kasih! Masukan Anda telah tersimpan untuk menyempurnakan Sangiang.",
    )


@app.get("/v1/feedback")
def list_recent_feedback(limit: int = 50):
    """Retrieve recent user feedback and corrections."""
    _init_feedback_db()
    with sqlite3.connect(str(FEEDBACK_DB_PATH)) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM translation_feedback ORDER BY id DESC LIMIT ?;",
            (limit,),
        )
        rows = [dict(r) for r in cur.fetchall()]
    return {"total_returned": len(rows), "feedback": rows}
