"""Benchmark Testset Generator.

Samples a stratified held-out evaluation test set from:
1. Biblical texts across distinct genres: Genesis (narrative), Psalms (poetic), Proverbs (wisdom), Matthew (gospel), Romans (epistolary).
2. Folk literature (Dongeng).
3. Classical literature (Himbawo).

Saves to benchmark/testset.json for BLEU / chrF++ evaluation.
"""

import json
import sqlite3
from pathlib import Path


def generate_benchmark_testset(
    db_path: str = "data/parallel_corpus.sqlite",
    out_file: str = "benchmark/testset.json",
    sample_size: int = 150,
):
    """Generate a balanced test set for translation quality evaluation."""
    db = Path(db_path)
    if not db.exists():
        raise FileNotFoundError(f"Database {db_path} does not exist.")

    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    items = []
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()

        # 1. Sample from Himbawo
        c.execute("""
            SELECT reference_id, source_domain, sangihe_text, indonesian_tb 
            FROM parallel_sentences 
            WHERE source_domain = 'himbawo' AND LENGTH(sangihe_text) > 25
            LIMIT 20;
        """)
        for r in c.fetchall():
            items.append({
                "id": r["reference_id"],
                "domain": "himbawo",
                "sangihe": r["sangihe_text"],
                "indonesian": r["indonesian_tb"],
            })

        # 2. Sample from Dongeng
        c.execute("""
            SELECT reference_id, source_domain, sangihe_text, indonesian_tb 
            FROM parallel_sentences 
            WHERE source_domain = 'dongeng' AND LENGTH(sangihe_text) > 30
            LIMIT 20;
        """)
        for r in c.fetchall():
            items.append({
                "id": r["reference_id"],
                "domain": "dongeng",
                "sangihe": r["sangihe_text"],
                "indonesian": r["indonesian_tb"],
            })

        # 3. Stratified sampling from Bible books
        bible_books = [
            ("GEN", "Narrative / Pentateuch"),
            ("PSA", "Poetry / Hymns"),
            ("PRO", "Wisdom Literature"),
            ("MAT", "Gospel Narrative"),
            ("ROM", "Epistolary / Doctrine"),
        ]
        per_book = (sample_size - len(items)) // len(bible_books)

        for prefix, genre in bible_books:
            c.execute("""
                SELECT reference_id, source_domain, sangihe_text, indonesian_tb 
                FROM parallel_sentences 
                WHERE source_domain = 'bible' AND reference_id LIKE ? 
                  AND LENGTH(sangihe_text) BETWEEN 30 AND 250
                ORDER BY RANDOM()
                LIMIT ?;
            """, (f"{prefix}%", per_book))
            for r in c.fetchall():
                items.append({
                    "id": r["reference_id"],
                    "domain": f"bible_{genre.lower()}",
                    "sangihe": r["sangihe_text"],
                    "indonesian": r["indonesian_tb"],
                })

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(items, f, indent=2, ensure_ascii=False)

    print(f"Generated benchmark testset with {len(items)} samples saved to {out_file}")
    return items


if __name__ == "__main__":
    generate_benchmark_testset()
