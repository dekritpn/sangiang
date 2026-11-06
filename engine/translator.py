"""Main Translation Pipeline Orchestrator."""

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from engine.llm_client import OllamaClient
from engine.prompt_templates import (
    SYSTEM_INDONESIAN_TO_SANGIHE,
    SYSTEM_SANGIHE_TO_INDONESIAN,
    build_translation_prompt,
)
from morphology.diacritic_restorer import DiacriticRestorer
from morphology.normalizer import tokenize_words
from retrieval.lexical_retriever import LexicalEntry, LexicalRetriever
from retrieval.semantic_retriever import ParallelMatch, SemanticRetriever


@dataclass
class TranslationResult:
    input_text: str
    translated_text: str
    direction: str
    elapsed_ms: float
    model: str = ""
    lexical_entries: List[LexicalEntry] = field(default_factory=list)
    parallel_matches: List[ParallelMatch] = field(default_factory=list)
    diacritics_restored: bool = False


class SangiheTranslationEngine:
    """End-to-end Translation Engine combining Hybrid RAG and Qwen2.5:7b."""

    def __init__(
        self,
        sarindi_db_path: Optional[str] = None,
        parallel_db_path: str = "data/parallel_corpus.sqlite",
        ollama_url: str = "http://localhost:11434",
        llm_model: Optional[str] = None,
        embedding_model: str = "bge-m3",
    ):
        self.lexical_retriever = LexicalRetriever(sarindi_db_path)
        self.semantic_retriever = SemanticRetriever(
            db_path=parallel_db_path,
            ollama_url=ollama_url,
            embedding_model=embedding_model,
        )
        self.llm_client = OllamaClient(
            base_url=ollama_url,
            model=llm_model,
        )
        self.diacritic_restorer = DiacriticRestorer()

    def translate(
        self,
        text: str,
        direction: str = "sangihe_to_id",
        model: Optional[str] = None,
        temperature: float = 0.2,
        top_k_parallel: int = 3,
        max_lexical: int = 20,
    ) -> TranslationResult:
        """Translate text between Bahasa Sangihe and Bahasa Indonesia."""
        start_time = time.time()
        active_model = model or self.llm_client.model
        clean_input = text.strip()
        if not clean_input:
            return TranslationResult(
                input_text="",
                translated_text="",
                direction=direction,
                elapsed_ms=0.0,
                model=active_model,
            )

        # Check for identity inquiry ("siapa namamu", "isai arengu", etc.)
        normalized_query = clean_input.lower().strip("?.!,;:\"' ")
        if normalized_query in {
            "siapa namamu", "siapa nama kamu", "siapa kamu", "siapa anda",
            "kamu siapa", "anda siapa", "who are you", "what is your name",
            "isai arengu", "isai areng-u", "isai i kau", "arengu kai apa", "areng-u kai apa",
            "isai ngaranu", "isai ngangengu", "sapa ngaramu",
        }:
            identity_text = "Saya adalah Sangiang, kecerdasan buatan dengan kemampuan berbahasa Sangihe."
            if direction == "id_to_sangihe" or any(k in normalized_query for k in ["isai", "arengu", "areng-u"]):
                identity_text = "Iạ kai i Sangiang, kecerdasan buatan mạbiahěng u bisara Sangihe."
            return TranslationResult(
                input_text=clean_input,
                translated_text=identity_text,
                direction=direction,
                elapsed_ms=(time.time() - start_time) * 1000,
                model=active_model,
                diacritics_restored=False,
            )

        # 1. Tokenize input for lexical lookup
        tokens = tokenize_words(clean_input)

        # 2. Retrieve lexical entries (dictionary definitions)
        if direction == "sangihe_to_id":
            lexical_entries = self.lexical_retriever.lookup_sangihe_tokens(
                tokens, max_results=max_lexical
            )
        else:
            lexical_entries = self.lexical_retriever.lookup_indonesian_tokens(
                tokens, max_results=max_lexical
            )

        # 3. Retrieve parallel corpus matches (sentence-level Translation Memory)
        parallel_matches = self.semantic_retriever.retrieve(
            query=clean_input,
            direction=direction,
            top_k=top_k_parallel,
        )

        # 3b. Check if a human speaker has already corrected this exact sentence in user_feedback.sqlite
        try:
            import sqlite3
            from pathlib import Path
            fb_db = Path(__file__).resolve().parent.parent / "data" / "user_feedback.sqlite"
            if fb_db.exists():
                with sqlite3.connect(str(fb_db)) as conn:
                    cur = conn.cursor()
                    cur.execute(
                        """
                        SELECT corrected_translation FROM translation_feedback
                        WHERE direction = ?
                          AND lower(trim(input_text)) = lower(?)
                          AND corrected_translation != ''
                          AND trim(corrected_translation) != trim(machine_translation)
                        ORDER BY id DESC LIMIT 1;
                        """,
                        (direction, clean_input),
                    )
                    row = cur.fetchone()
                    if row and row[0].strip():
                        return TranslationResult(
                            input_text=clean_input,
                            translated_text=row[0].strip(),
                            direction=direction,
                            elapsed_ms=(time.time() - start_time) * 1000,
                            model="Sangiang",
                            lexical_entries=lexical_entries,
                            parallel_matches=parallel_matches,
                            diacritics_restored=False,
                        )
        except Exception:
            pass

        # 4. Build prompt
        system_prompt = (
            SYSTEM_SANGIHE_TO_INDONESIAN
            if direction == "sangihe_to_id"
            else SYSTEM_INDONESIAN_TO_SANGIHE
        )
        user_prompt = build_translation_prompt(
            input_text=clean_input,
            direction=direction,
            lexical_entries=lexical_entries,
            parallel_matches=parallel_matches,
        )

        # 5. Call LLM
        raw_output = self.llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
        )

        # Clean output of any quotes or unwanted markers
        translated = raw_output.strip('"` \n')

        # 6. If target is Sangihe, apply post-processing diacritic restoration
        diacritics_restored = False
        if direction == "id_to_sangihe":
            diacritic_map = self.lexical_retriever.get_diacritic_map(lexical_entries)
            # Also extract words with diacritics from parallel matches
            for pm in parallel_matches:
                for word in pm.sangihe.split():
                    w_clean = word.strip(".,;:!?\"'()[]")
                    if w_clean:
                        from morphology.normalizer import has_diacritics, normalize_sangihe
                        if has_diacritics(w_clean):
                            diacritic_map[normalize_sangihe(w_clean).lower()] = w_clean

            restored = self.diacritic_restorer.restore_text(
                translated, context_glossary=diacritic_map
            )
            if restored != translated:
                diacritics_restored = True
                translated = restored

        elapsed_ms = (time.time() - start_time) * 1000

        return TranslationResult(
            input_text=clean_input,
            translated_text=translated,
            direction=direction,
            elapsed_ms=elapsed_ms,
            model=active_model,
            lexical_entries=lexical_entries,
            parallel_matches=parallel_matches,
            diacritics_restored=diacritics_restored,
        )

    def translate_batch(
        self,
        texts: List[str],
        direction: str = "sangihe_to_id",
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_lexical_per_batch: int = 28,
    ) -> List[TranslationResult]:
        """Translate a batch of sentences in a single LLM call with deduplicated dictionary lemmas."""
        if not texts:
            return []
        start_time = time.time()
        active_model = model or self.llm_client.model

        # Collect and deduplicate tokens across the entire batch
        all_tokens: List[str] = []
        seen_tok: set = set()
        for t in texts:
            for tok in tokenize_words(t):
                tl = tok.lower()
                if tl not in seen_tok:
                    seen_tok.add(tl)
                    all_tokens.append(tok)

        if direction == "sangihe_to_id":
            lexical_entries = self.lexical_retriever.lookup_sangihe_tokens(
                all_tokens, max_results=max_lexical_per_batch
            )
            system_prompt = SYSTEM_SANGIHE_TO_INDONESIAN
        else:
            lexical_entries = self.lexical_retriever.lookup_indonesian_tokens(
                all_tokens, max_results=max_lexical_per_batch
            )
            system_prompt = SYSTEM_INDONESIAN_TO_SANGIHE

        from engine.prompt_templates import format_lexical_context
        lex_str = format_lexical_context(lexical_entries, max_items=max_lexical_per_batch)

        numbered_lines = [f"[{i+1}] {t.strip()}" for i, t in enumerate(texts)]
        target_lang = "Indonesia formal" if direction == "sangihe_to_id" else "Sangihe baku berdiakritik"
        batch_prompt = (
            f"{lex_str}\n\n"
            f"Terjemahkan setiap kalimat bernomor berikut ke bahasa {target_lang}.\n"
            f"Wajib kembalikan hasil dengan penomoran persis [1], [2], dst. (satu baris per nomor, tanpa komentar tambahan):\n"
            + "\n".join(numbered_lines)
        )

        raw_output = self.llm_client.generate(
            prompt=batch_prompt,
            system_prompt=system_prompt,
            model=model,
            temperature=temperature,
            max_tokens=1024,
        )

        # Parse [1], [2], ... lines
        import re
        parsed_map: Dict[int, str] = {}
        for line in raw_output.splitlines():
            m = re.match(r"^\s*\[?(\d+)[\]\.\)]\s*(.+)$", line.strip())
            if m:
                idx = int(m.group(1)) - 1
                parsed_map[idx] = m.group(2).strip()

        total_ms = (time.time() - start_time) * 1000
        per_item_ms = total_ms / max(1, len(texts))

        results: List[TranslationResult] = []
        for i, src in enumerate(texts):
            trans = parsed_map.get(i)
            if not trans:
                # Fallback to single translation if a line was missed
                single_res = self.translate(src, direction=direction, model=model, temperature=temperature)
                results.append(single_res)
            else:
                results.append(
                    TranslationResult(
                        input_text=src,
                        translated_text=trans,
                        direction=direction,
                        elapsed_ms=per_item_ms,
                        model=active_model,
                        lexical_entries=lexical_entries,
                    )
                )
        return results
