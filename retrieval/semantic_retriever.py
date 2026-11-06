"""Semantic & Hybrid Translation Memory Retriever.

Uses Two-Stage Retrieval:
1. Fast lexical candidate retrieval using SQLite FTS5 (BM25 ranking).
2. Semantic re-ranking using local Ollama bge-m3 multilingual embeddings.
Provides relevant parallel sentence pairs (few-shot translation memory) for LLM prompting.
"""

import math
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import httpx
from morphology.normalizer import normalize_sangihe
from morphology.stemmer import analyze_word


@dataclass
class ParallelMatch:
    reference_id: str
    source_domain: str
    sangihe: str
    indonesian: str
    score: float


class SemanticRetriever:
    """Retrieves the most semantically relevant parallel sentence pairs."""

    def __init__(
        self,
        db_path: str = "data/parallel_corpus.sqlite",
        ollama_url: str = "http://localhost:11434",
        embedding_model: str = "bge-m3",
    ):
        self.db_path = Path(db_path)
        self.ollama_url = ollama_url
        self.embedding_model = embedding_model

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _get_embedding(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Call Ollama /api/embed for bge-m3 embeddings."""
        if not texts:
            return []
        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(
                    f"{self.ollama_url}/api/embed",
                    json={"model": self.embedding_model, "input": texts},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("embeddings")
        except Exception:
            # Fallback when Ollama embedding service is unreachable
            return None
        return None

    @staticmethod
    def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
        dot = sum(a * b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a * a for a in vec_a))
        norm_b = math.sqrt(sum(b * b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    def retrieve_candidates_fts(
        self, query: str, direction: str = "sangihe_to_id", limit: int = 15
    ) -> List[ParallelMatch]:
        """Stage 1: FTS5 keyword matching to find candidate sentences."""
        if not self.db_path.exists():
            return []

        # Prepare tokens
        norm_q = normalize_sangihe(query)
        words = [w for w in norm_q.split() if len(w) > 2]
        if not words:
            return []

        # If sangihe_to_id, expand with candidate stems
        search_terms = []
        if direction == "sangihe_to_id":
            for w in words[:6]:
                analysis = analyze_word(w)
                search_terms.extend(analysis.candidate_stems[:2])
        else:
            search_terms = words[:6]

        search_terms = list(dict.fromkeys(search_terms))  # deduplicate
        if not search_terms:
            return []

        # Build FTS match query
        match_query = " OR ".join(f'"{t}"' for t in search_terms)

        results: List[ParallelMatch] = []
        with self._get_connection() as conn:
            c = conn.cursor()
            column = "sangihe_normalized" if direction == "sangihe_to_id" else "indonesian_tb"
            sql = f"""
                SELECT p.id, p.source_domain, p.reference_id, p.sangihe_text, p.indonesian_tb, bm25(f) as rank
                FROM parallel_fts f
                JOIN parallel_sentences p ON f.rowid = p.id
                WHERE parallel_fts MATCH ?
                ORDER BY rank
                LIMIT ?;
            """
            try:
                c.execute(sql, (f"{column}: ({match_query})", limit))
                for row in c.fetchall():
                    raw_rank = float(row["rank"])
                    # Normalize BM25 rank (where more negative is better) to a 0.0-1.0 range
                    score = round(1.0 / (1.0 + max(0.0, raw_rank + 10.0)), 4)
                    results.append(
                        ParallelMatch(
                            reference_id=row["reference_id"],
                            source_domain=row["source_domain"],
                            sangihe=row["sangihe_text"],
                            indonesian=row["indonesian_tb"],
                            score=score,
                        )
                    )
            except sqlite3.OperationalError:
                # Fallback to general FTS without column filter
                try:
                    c.execute("""
                        SELECT p.id, p.source_domain, p.reference_id, p.sangihe_text, p.indonesian_tb, bm25(parallel_fts) as rank
                        FROM parallel_fts
                        JOIN parallel_sentences p ON parallel_fts.rowid = p.id
                        WHERE parallel_fts MATCH ?
                        ORDER BY rank
                        LIMIT ?;
                    """, (match_query, limit))
                    for row in c.fetchall():
                        raw_rank = float(row["rank"])
                        score = round(1.0 / (1.0 + max(0.0, raw_rank + 10.0)), 4)
                        results.append(
                            ParallelMatch(
                                reference_id=row["reference_id"],
                                source_domain=row["source_domain"],
                                sangihe=row["sangihe_text"],
                                indonesian=row["indonesian_tb"],
                                score=score,
                            )
                        )
                except Exception:
                    pass

        return results

    def retrieve(
        self,
        query: str,
        direction: str = "sangihe_to_id",
        top_k: int = 2,
        candidate_pool: int = 10,
        use_dense_rerank: bool = False,
    ) -> List[ParallelMatch]:
        """Hybrid Retrieval: fast BM25 matching, with optional dense bge-m3 re-ranking.
        
        Default use_dense_rerank=False prevents Ollama model thrashing on single-model setups,
        ensuring qwen2.5:7b stays continuously warm in memory.
        """
        candidates = self.retrieve_candidates_fts(
            query=query, direction=direction, limit=candidate_pool
        )
        if not candidates:
            return []

        # Fast path: return top BM25 candidates directly (< 3ms, zero Ollama calls)
        if not use_dense_rerank or len(candidates) <= top_k:
            return candidates[:top_k]

        # Dense path: Embed query and candidates with bge-m3 if explicitly enabled
        target_texts = [
            c.sangihe if direction == "sangihe_to_id" else c.indonesian
            for c in candidates
        ]
        all_texts = [query] + target_texts
        embeddings = self._get_embedding(all_texts)

        if not embeddings or len(embeddings) != len(all_texts):
            # Fallback to BM25 ranking if embeddings failed
            return candidates[:top_k]

        q_vec = embeddings[0]
        scored: List[ParallelMatch] = []
        for cand, doc_vec in zip(candidates, embeddings[1:]):
            sim = self._cosine_similarity(q_vec, doc_vec)
            scored.append(
                ParallelMatch(
                    reference_id=cand.reference_id,
                    source_domain=cand.source_domain,
                    sangihe=cand.sangihe,
                    indonesian=cand.indonesian,
                    score=round(sim, 4),
                )
            )

        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]
