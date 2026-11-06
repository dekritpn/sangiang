"""Lexical Retriever connecting to the Steller-Aebersold SQLite database (sarindi.sqlite).

Provides high-speed lookups for:
1. Sangihe -> Indonesian: Lookup lemmas and sublemmas using normalized forms and FTS.
2. Indonesian -> Sangihe: Lookup reverse index (id_index) and FTS for Indonesian glosses.
3. Diacritic Glossary Map: Extracts active (normalized -> diacritic) word mapping for post-processing.
"""

import json
import os
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Set
from morphology.normalizer import normalize_sangihe
from morphology.stemmer import analyze_word


@dataclass
class LexicalEntry:
    lemma_id: int
    lema_display: str
    lema_normalized: str
    summary_gloss: str
    body_plain: str = ""
    sublemmas: List[Dict[str, str]] = field(default_factory=list)
    match_source: str = "exact"  # 'exact', 'stem', 'sublemma', 'fts'


# Sangihe & Indonesian common function words / particles to skip during lexical lookup
# Note: Pronouns (iạ, sie, kau, kami, kite, sire) are intentionally excluded from stopwords
# because accurate pronoun translation is essential and avoids cross-language homograph confusion.
SANGIHE_STOPWORDS = {
    "su", "u", "i", "e", "ku", "kụ", "si", "ringangu", "dingangu", "bou", "bọu", "sarang",
    "kai", "tawe", "tawẹ", "ute", "tangu", "tangú", "ene", "ini", "manga",
    "wou", "wọi", "solong", "sol᷊ong", "kere", "kereu", "maning", "mase",
    "kuteu", "kutẹu", "seng", "sen", "ren", "den",
}

SANGIHE_PRONOUNS = {
    "iạ", "ia", "siạ", "sia", "sie", "isie", "kau", "ikau",
    "kami", "ikami", "kite", "kitẹ", "ikite", "sire", "isire", "kamene", "iạko",
}

INDONESIAN_STOPWORDS = {
    "dan", "di", "ke", "dari", "yang", "pada", "untuk", "dengan", "ini", "itu",
    "atau", "adalah", "ia", "dia", "mereka", "kita", "kami", "kamu", "aku", "saya",
    "akan", "telah", "sudah", "bisa", "dapat", "ada", "tidak", "bukan", "pun",
    "juga", "lalu", "kemudian", "maka", "bahwa", "oleh", "karena", "kepadanya",
    "kepada", "sang", "seekor", "seorang", "sebuah", "para", "sedang",
}


class LexicalRetriever:
    """Interacts with kamus_sangihe_modern.sqlite (and optional sarindi.sqlite fallback) to retrieve lexical definitions and diacritic data."""

    def __init__(self, db_path: Optional[str] = None, fallback_db_path: Optional[str] = None):
        root_dir = Path(__file__).resolve().parent.parent
        if db_path is None:
            # Prioritize the new modern Sangihe-Indonesian dictionary database
            candidates = [
                root_dir / "data" / "kamus_sangihe_modern.sqlite",
                root_dir.parent / "Kamus" / "sarindi" / "assets" / "db" / "sarindi.sqlite",
                Path("/home/dpng/Projects/Kamus/sarindi/assets/db/sarindi.sqlite"),
                Path("../Kamus/sarindi/assets/db/sarindi.sqlite"),
            ]
            for p in candidates:
                if p.exists():
                    self.db_path = str(p.resolve())
                    break
            else:
                self.db_path = str(candidates[0])
        else:
            self.db_path = db_path

        # Set Steller-Aebersold (sarindi.sqlite) as secondary fallback if primary is kamus_sangihe_modern.sqlite
        if fallback_db_path is None:
            sarindi_cand = root_dir.parent / "Kamus" / "sarindi" / "assets" / "db" / "sarindi.sqlite"
            if sarindi_cand.exists() and str(sarindi_cand.resolve()) != self.db_path:
                self.fallback_db_path: Optional[str] = str(sarindi_cand.resolve())
            else:
                self.fallback_db_path = None
        else:
            self.fallback_db_path = fallback_db_path

        if not os.path.exists(self.db_path):
            raise FileNotFoundError(f"Lexical SQLite database not found at: {self.db_path}")

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def lookup_sangihe_tokens(self, tokens: List[str], max_results: int = 20) -> List[LexicalEntry]:
        """Look up Sangihe tokens in dictionary using morphological stemming and fuzzy matching."""
        if not tokens:
            return []

        # Filter stopwords to focus on content words and prevent prompt bloat.
        # Preserve pronouns (even 2-letter tokens like 'ia' / 'iạ')
        filtered_tokens = [
            t for t in tokens
            if t.lower() in SANGIHE_PRONOUNS or (t.lower() not in SANGIHE_STOPWORDS and len(t) > 2)
        ]
        if not filtered_tokens:
            filtered_tokens = [t for t in tokens if t.lower() in SANGIHE_PRONOUNS or len(t) > 2]

        # Deduplicate filtered tokens while preserving sentence order
        dedup_tokens: List[str] = []
        seen_raw: Set[str] = set()
        for t in filtered_tokens:
            tl = normalize_sangihe(t.lower()).lower()
            if tl not in seen_raw:
                seen_raw.add(tl)
                dedup_tokens.append(t)

        # Separate Pass 1 (surface forms) and Pass 2 (morphological stems per token)
        surface_list: List[str] = []
        token_stems: Dict[str, List[str]] = {}
        for tok in dedup_tokens[:25]:
            tok_lower = tok.lower()
            if tok_lower in SANGIHE_PRONOUNS:
                norm_surf = "ia" if tok_lower in ("iạ", "ia", "iạko") else ("sie" if tok_lower in ("sie", "isie") else tok_lower)
            else:
                norm_surf = normalize_sangihe(tok_lower).lower()
            if norm_surf and (norm_surf in SANGIHE_PRONOUNS or len(norm_surf) > 2):
                if norm_surf not in surface_list:
                    surface_list.append(norm_surf)
                analysis = analyze_word(tok)
                stems_for_tok = [
                    c for c in analysis.candidate_stems
                    if c != norm_surf and (c in SANGIHE_PRONOUNS or len(c) > 2)
                ]
                token_stems[norm_surf] = stems_for_tok

        if not surface_list:
            return []

        entries: List[LexicalEntry] = []
        seen_norms: Set[str] = set()
        norm_to_entry: Dict[str, LexicalEntry] = {}
        norm_sense_counts: Dict[str, int] = {}

        def _fetch_lemmas_by_norms(c: sqlite3.Cursor, norms: List[str], source_prefix: str = "") -> None:
            if not norms or len(entries) >= max_results:
                return
            placeholders = ",".join("?" for _ in norms)
            rem = max_results - len(entries)
            query = f"""
                SELECT id, lema_display, lema_normalized, summary_gloss, body_plain, sublemmas_json
                FROM lemmas
                WHERE lema_normalized IN ({placeholders})
                ORDER BY id ASC
                LIMIT ?;
            """
            c.execute(query, norms + [rem * 4])
            for row in c.fetchall():
                lnorm = (row["lema_normalized"] or "").lower()
                ldisp = row["lema_display"] or row["lema_normalized"] or ""
                sgloss = row["summary_gloss"] or ""
                bplain = row["body_plain"] if "body_plain" in row.keys() and row["body_plain"] else sgloss
                if lnorm not in seen_norms:
                    if len(entries) >= max_results:
                        continue
                    seen_norms.add(lnorm)
                    norm_sense_counts[lnorm] = 1
                    subs = []
                    try:
                        subs = json.loads(row["sublemmas_json"])
                    except Exception:
                        pass
                    entry_obj = LexicalEntry(
                        lemma_id=row["id"],
                        lema_display=ldisp,
                        lema_normalized=row["lema_normalized"] or "",
                        summary_gloss=sgloss,
                        body_plain=bplain,
                        sublemmas=subs,
                        match_source=f"{source_prefix}lemma",
                    )
                    entries.append(entry_obj)
                    norm_to_entry[lnorm] = entry_obj
                elif lnorm in norm_to_entry and norm_sense_counts.get(lnorm, 1) < 3 and sgloss:
                    existing = norm_to_entry[lnorm]
                    if sgloss[:40] not in existing.summary_gloss:
                        norm_sense_counts[lnorm] += 1
                        if ldisp not in existing.lema_display:
                            existing.lema_display = f"{existing.lema_display} / {ldisp}"
                        existing.summary_gloss = f"{existing.summary_gloss} || ({ldisp}): {sgloss}"
                        existing.body_plain = f"{existing.body_plain} || ({ldisp}): {bplain}"

        def _query_db(db_file: str, source_prefix: str = "") -> None:
            if len(entries) >= max_results or not os.path.exists(db_file):
                return
            conn = sqlite3.connect(db_file)
            conn.row_factory = sqlite3.Row
            try:
                c = conn.cursor()
                # Pass 1: Exact surface forms first (1 entry per distinct input word)
                _fetch_lemmas_by_norms(c, surface_list, source_prefix)

                # Pass 2: Morphological stems ONLY for surface tokens that did not match in Pass 1
                unmatched_stems: List[str] = []
                for surf in surface_list:
                    if surf not in seen_norms:
                        for st in token_stems.get(surf, []):
                            if st not in seen_norms and st not in unmatched_stems:
                                unmatched_stems.append(st)
                if unmatched_stems:
                    _fetch_lemmas_by_norms(c, unmatched_stems[:30], source_prefix)

                candidate_list = surface_list + unmatched_stems[:20]

                if len(entries) < max_results and candidate_list:
                    rem = max_results - len(entries)
                    placeholders = ",".join("?" for _ in candidate_list)
                    sub_query = f"""
                        SELECT s.lemma_id, s.sublema, s.gloss, l.lema_display, l.lema_normalized, l.summary_gloss, l.body_plain
                        FROM sublemmas s
                        JOIN lemmas l ON s.lemma_id = l.id
                        WHERE s.sublema_normalized IN ({placeholders})
                        ORDER BY l.id ASC
                        LIMIT ?;
                    """
                    c.execute(sub_query, candidate_list + [rem * 2])
                    for row in c.fetchall():
                        if len(entries) >= max_results:
                            break
                        lnorm = (row["lema_normalized"] or "").lower()
                        if lnorm not in seen_norms:
                            seen_norms.add(lnorm)
                            entries.append(
                                LexicalEntry(
                                    lemma_id=row["lemma_id"],
                                    lema_display=row["lema_display"] or row["lema_normalized"] or "",
                                    lema_normalized=row["lema_normalized"] or "",
                                    summary_gloss=f"{row['summary_gloss'] or ''} (Turunan: {row['sublema']} = {row['gloss'] or ''})",
                                    body_plain=row["body_plain"] or row["summary_gloss"] or "",
                                    sublemmas=[],
                                    match_source=f"{source_prefix}sublemma",
                                )
                            )
            finally:
                conn.close()

        # 1. Query primary modern Sangihe dictionary
        _query_db(self.db_path, source_prefix="")
        # 2. Supplement from fallback Steller-Aebersold (sarindi.sqlite) if needed
        if len(entries) < max_results and self.fallback_db_path:
            _query_db(self.fallback_db_path, source_prefix="steller_")

        return entries

    def lookup_indonesian_tokens(self, tokens: List[str], max_results: int = 10) -> List[LexicalEntry]:
        """Look up Indonesian tokens in reverse index (id_index) and joined FTS."""
        if not tokens:
            return []

        # Filter stopwords
        norm_tokens = [
            normalize_sangihe(t).lower()
            for t in tokens
            if t.lower() not in INDONESIAN_STOPWORDS and len(t) > 2
        ]
        if not norm_tokens:
            norm_tokens = [normalize_sangihe(t).lower() for t in tokens if len(t) > 2]
        if not norm_tokens:
            return []

        norm_tokens = norm_tokens[:12]
        entries: List[LexicalEntry] = []
        seen_ids: Set[int] = set()

        with self._get_connection() as conn:
            c = conn.cursor()

            # 1. Reverse index query
            placeholders = ",".join("?" for _ in norm_tokens)
            query = f"""
                SELECT l.id, l.lema_display, l.lema_normalized, l.summary_gloss, l.body_plain, l.sublemmas_json, idx.is_primary
                FROM id_index idx
                JOIN lemmas l ON idx.lemma_id = l.id
                WHERE idx.id_keyword_normalized IN ({placeholders})
                ORDER BY idx.is_primary DESC, l.id ASC
                LIMIT ?;
            """
            c.execute(query, norm_tokens + [max_results])
            for row in c.fetchall():
                lid = row["id"]
                if lid not in seen_ids:
                    seen_ids.add(lid)
                    subs = []
                    try:
                        subs = json.loads(row["sublemmas_json"])
                    except Exception:
                        pass
                    entries.append(
                        LexicalEntry(
                            lemma_id=lid,
                            lema_display=row["lema_display"] or row["lema_normalized"] or "",
                            lema_normalized=row["lema_normalized"] or "",
                            summary_gloss=row["summary_gloss"] or "",
                            body_plain=row["body_plain"] if "body_plain" in row.keys() and row["body_plain"] else (row["summary_gloss"] or ""),
                            sublemmas=subs,
                            match_source="id_index",
                        )
                    )

            # 2. Joined FTS fallback if few results found (Must JOIN lemmas table because lemmas_fts has content='')
            if len(entries) < 4:
                fts_query_str = " OR ".join(f'"{t}"' for t in norm_tokens[:4])
                try:
                    c.execute(
                        """
                        SELECT l.id, l.lema_display, l.lema_normalized, l.summary_gloss, l.body_plain, l.sublemmas_json
                        FROM lemmas_fts fts
                        JOIN lemmas l ON fts.rowid = l.id
                        WHERE lemmas_fts MATCH ?
                        LIMIT ?;
                    """,
                        (fts_query_str, max_results - len(entries)),
                    )
                    for row in c.fetchall():
                        lid = row["id"]
                        if lid not in seen_ids:
                            seen_ids.add(lid)
                            subs = []
                            try:
                                subs = json.loads(row["sublemmas_json"])
                            except Exception:
                                pass
                            entries.append(
                                LexicalEntry(
                                    lemma_id=lid,
                                    lema_display=row["lema_display"] or row["lema_normalized"] or "",
                                    lema_normalized=row["lema_normalized"] or "",
                                    summary_gloss=row["summary_gloss"] or "",
                                    body_plain=row["body_plain"] if "body_plain" in row.keys() and row["body_plain"] else (row["summary_gloss"] or ""),
                                    sublemmas=subs,
                                    match_source="fts",
                                )
                            )
                except sqlite3.OperationalError:
                    pass

        return entries

    def lookup_indonesian_keyword(self, query_text: str, max_results: int = 5) -> List[LexicalEntry]:
        """Convenience wrapper to look up an Indonesian text or keyword string."""
        import re
        words = re.findall(r"[a-zA-Z\-]+", query_text)
        return self.lookup_indonesian_tokens(words, max_results=max_results)

    def get_diacritic_map(self, entries: List[LexicalEntry]) -> Dict[str, str]:
        """Extract a (normalized -> diacritic) mapping from retrieved entries and their sublemmas."""
        mapping: Dict[str, str] = {}
        for e in entries:
            if e.lema_normalized and e.lema_display:
                mapping[e.lema_normalized.lower()] = e.lema_display
            for sub in e.sublemmas:
                sub_name = sub.get("sublema") or sub.get("lema_display") or ""
                if sub_name:
                    norm = normalize_sangihe(sub_name).lower()
                    mapping[norm] = sub_name
        return mapping
