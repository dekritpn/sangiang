#!/usr/bin/env python3
"""
Exports the local SQLite databases (`kamus_sangihe_modern.sqlite`, `parallel_corpus.sqlite`,
and `user_feedback.sqlite`) into Cloudflare D1-compatible SQL chunk files in `cloudflare_d1/`.
"""

import sqlite3
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT_DIR / "cloudflare_d1"
KAMUS_DB = ROOT_DIR / "data" / "kamus_sangihe_modern.sqlite"
PARALLEL_DB = ROOT_DIR / "data" / "parallel_corpus.sqlite"
FEEDBACK_DB = ROOT_DIR / "data" / "user_feedback.sqlite"


def sql_escape(val) -> str:
    if val is None:
        return "NULL"
    if isinstance(val, (int, float)):
        return str(val)
    s = str(val).replace("'", "''")
    return f"'{s}'"


def write_batched_inserts(prefix: str, table: str, cols: list, rows: list, rows_per_file: int = 4000):
    col_str = ", ".join(cols)
    file_idx = 1
    for i in range(0, len(rows), rows_per_file):
        chunk = rows[i : i + rows_per_file]
        lines = []
        # Group 25 rows per multi-value INSERT statement for fast D1 import
        for j in range(0, len(chunk), 25):
            sub = chunk[j : j + 25]
            vals_list = [
                "(" + ", ".join(sql_escape(v) for v in r) + ")"
                for r in sub
            ]
            lines.append(f"INSERT OR IGNORE INTO {table} ({col_str}) VALUES\n" + ",\n".join(vals_list) + ";\n")
        out_file = OUT_DIR / f"{prefix}_{file_idx:02d}.sql"
        out_file.write_text("".join(lines), encoding="utf-8")
        print(f"  -> Wrote {out_file.name} ({len(chunk)} rows)")
        file_idx += 1


def export_d1():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for old in OUT_DIR.glob("*.sql"):
        old.unlink()

    # 1. Schema file
    schema_sql = """-- Cloudflare D1 Schema for Sangiang Ecosystem (sangihe.org)
CREATE TABLE IF NOT EXISTS lemmas (
    id INTEGER PRIMARY KEY,
    lema_display TEXT NOT NULL,
    lema_normalized TEXT NOT NULL,
    summary_gloss TEXT NOT NULL,
    body_plain TEXT NOT NULL,
    sublemmas_json TEXT NOT NULL DEFAULT '[]',
    tier INTEGER DEFAULT 3,
    freq_count INTEGER DEFAULT 0
);
CREATE INDEX IF NOT EXISTS idx_lemmas_norm ON lemmas(lema_normalized);

CREATE TABLE IF NOT EXISTS sublemmas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lemma_id INTEGER NOT NULL,
    sublema TEXT NOT NULL,
    sublema_normalized TEXT NOT NULL,
    gloss TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sublemmas_norm ON sublemmas(sublema_normalized);

CREATE TABLE IF NOT EXISTS id_index (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    id_keyword TEXT NOT NULL,
    id_keyword_normalized TEXT NOT NULL,
    lemma_id INTEGER NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_id_index_norm ON id_index(id_keyword_normalized);

CREATE TABLE IF NOT EXISTS parallel_sentences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_domain TEXT NOT NULL,
    reference_id TEXT NOT NULL,
    sangihe_text TEXT NOT NULL,
    sangihe_normalized TEXT NOT NULL,
    indonesian_tb TEXT NOT NULL,
    indonesian_bimk TEXT DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_parallel_domain ON parallel_sentences(source_domain);

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

CREATE TABLE IF NOT EXISTS llm_cache (
    cache_key TEXT PRIMARY KEY,
    response_text TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""
    (OUT_DIR / "00_schema.sql").write_text(schema_sql, encoding="utf-8")
    print("[+] Wrote 00_schema.sql")

    # 2. Export lemmas, sublemmas, id_index from kamus_sangihe_modern.sqlite
    with sqlite3.connect(str(KAMUS_DB)) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, lema_display, lema_normalized, summary_gloss, substr(body_plain, 1, 360), sublemmas_json, tier, freq_count FROM lemmas ORDER BY id ASC;"
        )
        lemmas_rows = c.fetchall()
        write_batched_inserts(
            "01_lemmas",
            "lemmas",
            ["id", "lema_display", "lema_normalized", "summary_gloss", "body_plain", "sublemmas_json", "tier", "freq_count"],
            lemmas_rows,
            rows_per_file=5000,
        )

        c.execute("SELECT id, lemma_id, sublema, sublema_normalized, gloss FROM sublemmas ORDER BY id ASC;")
        sub_rows = c.fetchall()
        write_batched_inserts(
            "02_sublemmas",
            "sublemmas",
            ["id", "lemma_id", "sublema", "sublema_normalized", "gloss"],
            sub_rows,
            rows_per_file=6000,
        )

        c.execute("SELECT id, id_keyword, id_keyword_normalized, lemma_id, is_primary FROM id_index ORDER BY id ASC;")
        idx_rows = c.fetchall()
        write_batched_inserts(
            "03_id_index",
            "id_index",
            ["id", "id_keyword", "id_keyword_normalized", "lemma_id", "is_primary"],
            idx_rows,
            rows_per_file=10000,
        )

    # 3. Export parallel_sentences from parallel_corpus.sqlite
    with sqlite3.connect(str(PARALLEL_DB)) as conn:
        c = conn.cursor()
        c.execute(
            "SELECT id, source_domain, reference_id, sangihe_text, sangihe_normalized, indonesian_tb, COALESCE(indonesian_bimk, '') FROM parallel_sentences ORDER BY id ASC;"
        )
        par_rows = c.fetchall()
        write_batched_inserts(
            "04_parallel",
            "parallel_sentences",
            ["id", "source_domain", "reference_id", "sangihe_text", "sangihe_normalized", "indonesian_tb", "indonesian_bimk"],
            par_rows,
            rows_per_file=5000,
        )

    # 4. Export translation_feedback from user_feedback.sqlite
    if FEEDBACK_DB.exists():
        with sqlite3.connect(str(FEEDBACK_DB)) as conn:
            c = conn.cursor()
            c.execute(
                "SELECT id, created_at, direction, input_text, machine_translation, is_correct, corrected_translation, notes, client_ip FROM translation_feedback ORDER BY id ASC;"
            )
            fb_rows = c.fetchall()
            if fb_rows:
                write_batched_inserts(
                    "05_feedback",
                    "translation_feedback",
                    ["id", "created_at", "direction", "input_text", "machine_translation", "is_correct", "corrected_translation", "notes", "client_ip"],
                    fb_rows,
                    rows_per_file=1000,
                )

    # 5. Create helper shell script to import all SQL chunks into Cloudflare D1
    import_sh = """#!/usr/bin/env bash
set -e
DB_NAME="${1:-sangiang-db}"
echo "=========================================================="
echo "  Mengimpor Database Sangiang ke Cloudflare D1: $DB_NAME"
echo "=========================================================="
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for sql_file in "$DIR"/*.sql; do
  echo "[*] Menjalankan $(basename "$sql_file") ..."
  npx wrangler d1 execute "$DB_NAME" --remote --file="$sql_file"
done
echo "[+] Selesai! Seluruh data kamus, korpus paralel, dan feedback telah masuk ke Cloudflare D1 ($DB_NAME)."
"""
    sh_path = OUT_DIR / "import_to_d1.sh"
    sh_path.write_text(import_sh, encoding="utf-8")
    sh_path.chmod(0o755)
    print(f"[+] Wrote {sh_path}")


if __name__ == "__main__":
    export_d1()

