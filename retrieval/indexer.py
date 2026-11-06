"""Parallel Corpus Indexer.

Collects and parses:
1. Alkitab parallel verses (31,102 verses) from ../Kamus/Sangihe/corpus/merged/*.tsv
2. Classical narrative verse & prose from ../WoordenBoek/Himbawo/himbawo.tex
3. Folk literature from ../WoordenBoek/dongeng/chapters/*.tex

Builds an optimized SQLite database with FTS5 search (data/parallel_corpus.sqlite)
to serve as the Sentence-Level Translation Memory for Hybrid RAG.
"""

import glob
import os
import re
import sqlite3
from pathlib import Path
from typing import List, Tuple
from morphology.normalizer import normalize_sangihe


def clean_latex(text: str) -> str:
    """Strip LaTeX commands, footnotes, comments, and extra formatting."""
    # Remove footnotes completely
    text = re.sub(r"\\footnote\{.*?\}", "", text, flags=re.DOTALL)
    # Remove common commands like \textit{...}, \textbf{...}, \small, etc.
    text = re.sub(r"\\[a-zA-Z]+\*?(\[[^\]]*\])?(\{([^\{\}]*)\})?", r"\3", text)
    text = re.sub(r"\\[a-zA-Z]+", "", text)
    # Clean braces and slashes
    text = text.replace("{", "").replace("}", "")
    text = text.replace(" / ", ", ").replace("/", ",")
    # Normalize whitespaces while preserving paragraph breaks
    paragraphs = [re.sub(r"[ \t]+", " ", p).strip() for p in text.split("\n\n")]
    return "\n\n".join(p for p in paragraphs if p)


class CorpusIndexer:
    """Builds and manages data/parallel_corpus.sqlite."""

    def __init__(self, db_path: str = "data/parallel_corpus.sqlite"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def init_db(self):
        """Create tables and FTS5 indexes."""
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.execute("DROP TABLE IF EXISTS parallel_sentences;")
            c.execute("DROP TABLE IF EXISTS parallel_fts;")
            c.execute("""
                CREATE TABLE parallel_sentences (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_domain TEXT NOT NULL,
                    reference_id TEXT NOT NULL,
                    sangihe_text TEXT NOT NULL,
                    sangihe_normalized TEXT NOT NULL,
                    indonesian_tb TEXT NOT NULL,
                    indonesian_bimk TEXT
                );
            """)
            c.execute("""
                CREATE VIRTUAL TABLE parallel_fts USING fts5(
                    sangihe_normalized,
                    indonesian_tb,
                    indonesian_bimk,
                    content='parallel_sentences',
                    content_rowid='id'
                );
            """)
            c.execute("CREATE INDEX idx_ref_id ON parallel_sentences(reference_id);")
            c.execute("CREATE INDEX idx_domain ON parallel_sentences(source_domain);")
            conn.commit()

    def index_bible_corpus(self, merged_dir: str) -> int:
        """Parse all 1,189 TSV chapter files from Alkitab merged corpus."""
        files = sorted(glob.glob(os.path.join(merged_dir, "*.tsv")))
        records: List[Tuple[str, str, str, str, str, str]] = []

        for fpath in files:
            fname = Path(fpath).stem  # e.g. GEN1, MAT5
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                for line in f:
                    parts = line.strip().split("\t")
                    if len(parts) >= 2:
                        sangihe = parts[0].strip(' "\'')
                        tb = parts[1].strip(' "\'')
                        bimk = parts[3].strip(' "\'') if len(parts) > 3 else ""
                        v_num = parts[4].strip() if len(parts) > 4 else "1"

                        if sangihe and tb:
                            ref = f"{fname}:{v_num}"
                            s_norm = normalize_sangihe(sangihe)
                            records.append(("bible", ref, sangihe, s_norm, tb, bimk))

        self._insert_records(records)
        return len(records)

    def index_himbawo(self, himbawo_path: str) -> int:
        """Extract paired verses and prose from Himbawo LaTeX source."""
        if not os.path.exists(himbawo_path):
            return 0

        with open(himbawo_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Match \sangverse{...} and immediately following \idverse{...}
        verse_pattern = re.compile(
            r"\\sangverse\{(.*?)\}\s*\\idverse\{(.*?)\}", re.DOTALL
        )
        prose_pattern = re.compile(
            r"\\sangprose\{(.*?)\}\s*\\idprose\{(.*?)\}", re.DOTALL
        )

        records: List[Tuple[str, str, str, str, str, str]] = []
        v_idx = 1
        for match in verse_pattern.finditer(content):
            s_raw, id_raw = match.groups()
            s_clean = clean_latex(s_raw)
            id_clean = clean_latex(id_raw)
            if s_clean and id_clean:
                records.append((
                    "himbawo",
                    f"himbawo:verse:{v_idx}",
                    s_clean,
                    normalize_sangihe(s_clean),
                    id_clean,
                    "",
                ))
                v_idx += 1

        p_idx = 1
        for match in prose_pattern.finditer(content):
            s_raw, id_raw = match.groups()
            s_clean = clean_latex(s_raw)
            id_clean = clean_latex(id_raw)
            if s_clean and id_clean:
                records.append((
                    "himbawo",
                    f"himbawo:prose:{p_idx}",
                    s_clean,
                    normalize_sangihe(s_clean),
                    id_clean,
                    "",
                ))
                p_idx += 1

        self._insert_records(records)
        return len(records)

    def index_dongeng(self, dongeng_dir: str) -> int:
        """Extract stories and paragraph pairs from dongeng chapters."""
        files = sorted(glob.glob(os.path.join(dongeng_dir, "story_*.tex")))
        records: List[Tuple[str, str, str, str, str, str]] = []

        for fpath in files:
            fname = Path(fpath).stem
            with open(fpath, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()

            s_sections = re.findall(
                r"\\section\*\{Teks Asli Bahasa Sangihe[^\}]*\}(.*?)(?=\\section\*|\\clearpage|\Z)",
                content,
                re.DOTALL,
            )
            id_sections = re.findall(
                r"\\section\*\{Terjemahan Bahasa Indonesia[^\}]*\}(.*?)(?=\\section\*|\\clearpage|\Z)",
                content,
                re.DOTALL,
            )

            for sec_idx, (s_sec, id_sec) in enumerate(zip(s_sections, id_sections), start=1):
                s_clean = clean_latex(s_sec)
                id_clean = clean_latex(id_sec)
                # Split into non-empty paragraphs
                s_paras = [p.strip() for p in s_clean.split("\n\n") if len(p.strip()) > 20]
                id_paras = [p.strip() for p in id_clean.split("\n\n") if len(p.strip()) > 20]

                # If same length of paragraphs, index 1-to-1
                if len(s_paras) == len(id_paras) and s_paras:
                    for p_i, (sp, idp) in enumerate(zip(s_paras, id_paras), start=1):
                        records.append((
                            "dongeng",
                            f"{fname}:{sec_idx}:{p_i}",
                            sp,
                            normalize_sangihe(sp),
                            idp,
                            "",
                        ))
                else:
                    # Index each paragraph or entire section
                    min_len = min(len(s_paras), len(id_paras))
                    if min_len > 0:
                        for p_i in range(min_len):
                            records.append((
                                "dongeng",
                                f"{fname}:{sec_idx}:{p_i+1}",
                                s_paras[p_i],
                                normalize_sangihe(s_paras[p_i]),
                                id_paras[p_i],
                                "",
                            ))
                    elif s_clean and id_clean:
                        records.append((
                            "dongeng",
                            f"{fname}:{sec_idx}",
                            s_clean[:1000],
                            normalize_sangihe(s_clean[:1000]),
                            id_clean[:1000],
                            "",
                        ))

        self._insert_records(records)
        return len(records)

    def index_tiga_kulano(self, jsonl_path: str = "data/tiga_kulano_aligned.jsonl") -> int:
        """Ingest aligned sentence pairs from 'Tiga Kulano dari Dagho'."""
        if not os.path.exists(jsonl_path):
            return 0
        import json
        records: List[Tuple[str, str, str, str, str, str]] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    records.append((
                        "tiga_kulano",
                        item["unit_id"],
                        item["regional_text"],
                        item["regional_normalized"],
                        item["indonesian_text"],
                        f"[{item['language'].upper()}] {item['story_title_id']}",
                    ))
        self._insert_records(records)
        return len(records)

    def index_percakapan(self, jsonl_path: str = "data/web_conversations_aligned.jsonl") -> int:
        """Ingest everyday conversational pairs from web sources."""
        if not os.path.exists(jsonl_path):
            return 0
        import json
        records: List[Tuple[str, str, str, str, str, str]] = []
        with open(jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    records.append((
                        "percakapan",
                        item["unit_id"],
                        item["regional_text"],
                        item["regional_normalized"],
                        item["indonesian_text"],
                        f"[PERCAKAPAN] {item.get('category', 'sehari-hari')}",
                    ))
        self._insert_records(records)
        return len(records)

    def _insert_records(self, records: List[Tuple[str, str, str, str, str, str]]):
        """Batch insert records into parallel_sentences and FTS5 table."""
        if not records:
            return
        with sqlite3.connect(self.db_path) as conn:
            c = conn.cursor()
            c.executemany("""
                INSERT INTO parallel_sentences 
                (source_domain, reference_id, sangihe_text, sangihe_normalized, indonesian_tb, indonesian_bimk)
                VALUES (?, ?, ?, ?, ?, ?);
            """, records)

            c.execute("""
                INSERT INTO parallel_fts(parallel_fts) VALUES('rebuild');
            """)
            conn.commit()


def build_corpus_database(
    db_out: str = "data/parallel_corpus.sqlite",
    merged_dir: str = "../Kamus/Sangihe/corpus/merged",
    himbawo_path: str = "../WoordenBoek/Himbawo/himbawo.tex",
    dongeng_dir: str = "../WoordenBoek/dongeng/chapters",
    tiga_kulano_path: str = "data/tiga_kulano_aligned.jsonl",
    percakapan_path: str = "data/web_conversations_aligned.jsonl",
) -> dict:
    """Build the complete parallel corpus database."""
    indexer = CorpusIndexer(db_out)
    indexer.init_db()

    counts = {}
    counts["bible"] = indexer.index_bible_corpus(merged_dir)
    counts["himbawo"] = indexer.index_himbawo(himbawo_path)
    counts["dongeng"] = indexer.index_dongeng(dongeng_dir)
    counts["tiga_kulano"] = indexer.index_tiga_kulano(tiga_kulano_path)
    counts["percakapan"] = indexer.index_percakapan(percakapan_path)
    counts["total"] = sum(counts.values())
    return counts


if __name__ == "__main__":
    counts = build_corpus_database()
    print("Indexed corpus sentences:", counts)
