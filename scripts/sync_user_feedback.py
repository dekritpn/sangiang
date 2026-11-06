#!/usr/bin/env python3
"""
Sinkronisasi masukan & koreksi pengguna (`data/user_feedback.sqlite`) ke dalam:
1. Database Kamus Sangihe Modern (`data/kamus_sangihe_modern.sqlite`) - Tier 1
2. Korpus Kalimat Paralel BM25 (`data/parallel_corpus.sqlite`)
"""

import json
import sqlite3
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from morphology.normalizer import normalize_sangihe

FEEDBACK_DB = ROOT_DIR / "data" / "user_feedback.sqlite"
KAMUS_DB = ROOT_DIR / "data" / "kamus_sangihe_modern.sqlite"
PARALLEL_DB = ROOT_DIR / "data" / "parallel_corpus.sqlite"

# Lema kosakata penting yang terungkap dari feedback penutur publik
FEEDBACK_LEXICON_UPDATES = [
    {
        "lema": "sarangapa",
        "pos": "adv",
        "stem": "sarang",
        "meaning": "ke mana; mau ke mana; hendak ke mana",
        "example_sa": "Sarangapa i kamene?",
        "example_id": "Kalian mau ke mana?",
        "keywords": ["ke mana", "mau ke mana", "kemana"],
    },
    {
        "lema": "rendingane",
        "pos": "v",
        "stem": "dending",
        "meaning": "sertailah; dampingilah; lindungilah (bentuk permohonan/imperatif dari dending / rending)",
        "example_sa": "Oh Mawu, rendingane i kami manga ělang.",
        "example_id": "Ya Tuhan, sertailah kami para hamba.",
        "keywords": ["sertailah", "menyertai", "dampingilah", "mendampingi", "lindungilah"],
    },
    {
        "lema": "dending",
        "pos": "v",
        "stem": "dending",
        "meaning": "menyertai; mendampingi; menjaga; melindungi (berubah bunyi d -> r menjadi rending / rendingang / rendingane)",
        "example_sa": "Oh Mawu, rendingane i kami manga ělang.",
        "example_id": "Ya Tuhan, sertailah kami para hamba.",
        "keywords": ["menyertai", "sertai", "mendampingi", "melindungi"],
    },
    {
        "lema": "ělang",
        "pos": "n",
        "stem": "ělang",
        "meaning": "hamba; abdi; umat",
        "example_sa": "Oh Mawu, rendingane i kami manga ělang.",
        "example_id": "Ya Tuhan, sertailah kami para hamba.",
        "keywords": ["hamba", "abdi", "umat"],
    },
    {
        "lema": "wawu",
        "pos": "n",
        "stem": "bawu",
        "meaning": "ibu; putri; nona (sapaan hormat perempuan sesudah partikel i: i wawu, perubahan bunyi b -> w dari bawu)",
        "example_sa": "I wawu Dian masadada.",
        "example_id": "Ibu Dian cantik.",
        "keywords": ["ibu", "nona", "putri"],
    },
    {
        "lema": "masadada",
        "pos": "adj",
        "stem": "sadada",
        "meaning": "cantik; elok; rupawan; indah",
        "example_sa": "I wawu Dian masadada.",
        "example_id": "Ibu Dian cantik.",
        "keywords": ["cantik", "elok", "rupawan"],
    },
    {
        "lema": "Ghenggona",
        "pos": "n",
        "stem": "ghenggona",
        "meaning": "Tuhan Yang Mahatinggi; Sang Khalik; Allah (sebutan ilahi dalam tradisi Sangihe)",
        "example_sa": "Dalo sembah si Ghenggona.",
        "example_id": "Puji dan sembah kepada Allah.",
        "keywords": ["allah", "tuhan", "khalik"],
    },
    {
        "lema": "kindorẹ",
        "pos": "n",
        "stem": "kindorẹ",
        "meaning": "niat kuat; tekad bulat; kemauan keras",
        "example_sa": "Kindore menope langi, nolo kere anging daki.",
        "example_id": "Niat kuat meruntuhkan langit, susut seperti hembusan angin timur.",
        "keywords": ["niat kuat", "tekad"],
    },
    {
        "lema": "měnope",
        "pos": "v",
        "stem": "tope",
        "meaning": "meruntuhkan; merobohkan",
        "example_sa": "Kindore menope langi, nolo kere anging daki.",
        "example_id": "Niat kuat meruntuhkan langit, susut seperti hembusan angin timur.",
        "keywords": ["meruntuhkan", "merobohkan"],
    },
    {
        "lema": "nolo",
        "pos": "v",
        "stem": "tolo",
        "meaning": "susut; reda; surut",
        "example_sa": "Kindore menope langi, nolo kere anging daki.",
        "example_id": "Niat kuat meruntuhkan langit, susut seperti hembusan angin timur.",
        "keywords": ["susut", "reda", "surut"],
    },
    {
        "lema": "saghenu",
        "pos": "v",
        "stem": "saghenu",
        "meaning": "membawa/menjinjing menarik sesuatu barang dengan cara didekap atau dipeluk",
        "example_sa": "Saghenu",
        "example_id": "Membawa/menjinjing menarik sesuatu barang dengan cara didekap atau dipeluk",
        "keywords": ["mendekap", "memeluk", "menjinjing"],
    },
]


def sync_feedback():
    # 1. Perbaiki entri #9 di user_feedback.sqlite yang belum sempat diubah teks koreksinya oleh user
    if FEEDBACK_DB.exists():
        with sqlite3.connect(str(FEEDBACK_DB)) as conn:
            conn.execute(
                """
                UPDATE translation_feedback
                SET corrected_translation = 'Iạ hinong mạtěngkasụ tarima kasehẹ̌ su iamang dingangu inang apang seng nạkě̌bohe si siạ.'
                WHERE id = 9 AND corrected_translation = machine_translation;
                """
            )
            conn.commit()

    # 2. Suntikkan lema kosakata hasil feedback ke kamus_sangihe_modern.sqlite
    if KAMUS_DB.exists():
        with sqlite3.connect(str(KAMUS_DB)) as conn:
            c = conn.cursor()
            for item in FEEDBACK_LEXICON_UPDATES:
                lema = item["lema"]
                lema_norm = normalize_sangihe(lema).lower()
                pos = item["pos"]
                stem = item["stem"]
                stem_norm = normalize_sangihe(stem).lower()
                meaning = item["meaning"]
                summary = f"[{pos}] {meaning}" + (f" (akar: {stem})" if stem != lema else "")
                body = f'{summary} | Contoh: "{item["example_sa"]}" = "{item["example_id"]}" [Feedback Penutur]'

                c.execute("SELECT id FROM lemmas WHERE lema_normalized = ? LIMIT 1;", (lema_norm,))
                row = c.fetchone()
                if row:
                    lid = row[0]
                    c.execute(
                        """
                        UPDATE lemmas
                        SET lema_display = ?, summary_gloss = ?, body_plain = ?, body_rich = ?,
                            pos = ?, stem = ?, stem_normalized = ?, tier = 1,
                            confidence = 'terverifikasi', source_label = 'user_feedback'
                        WHERE id = ?;
                        """,
                        (lema, summary, body, body, pos, stem, stem_norm, lid),
                    )
                else:
                    c.execute("SELECT COALESCE(MAX(id), 0) + 1 FROM lemmas;")
                    lid = c.fetchone()[0]
                    c.execute(
                        """
                        INSERT INTO lemmas (
                            id, letter, lema_raw, lema_display, lema_normalized,
                            homonym_index, etymology, summary_gloss, body_plain, body_rich,
                            sublemmas_json, cross_refs_json, verses_json, id_keywords_json,
                            pos, stem, stem_normalized, freq_count, confidence, tier, source_label
                        ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, '[]', '[]', '[]', ?, ?, ?, ?, 100, 'terverifikasi', 1, 'user_feedback');
                        """,
                        (
                            lid,
                            lema_norm[0].upper(),
                            lema,
                            lema,
                            lema_norm,
                            stem if stem != lema else "",
                            summary,
                            body,
                            body,
                            json.dumps(item["keywords"], ensure_ascii=False),
                            pos,
                            stem,
                            stem_norm,
                        ),
                    )
                    c.execute(
                        "INSERT INTO lemmas_fts (rowid, lema_display, lema_normalized, sublemmas_text, id_keywords_text, summary_gloss) VALUES (?, ?, ?, '', ?, ?);",
                        (lid, lema, lema_norm, " ".join(item["keywords"]), summary),
                    )

                for kw in item["keywords"]:
                    kw_norm = normalize_sangihe(kw).lower()
                    c.execute(
                        "INSERT INTO id_index (id_keyword, id_keyword_normalized, lemma_id, is_primary) VALUES (?, ?, ?, 4);",
                        (kw, kw_norm, lid),
                    )
            conn.commit()
            print(f"[+] Berhasil menyinkronkan {len(FEEDBACK_LEXICON_UPDATES)} lema feedback ke kamus_sangihe_modern.sqlite.")

    # 3. Suntikkan kalimat terverifikasi/terkoreksi ke parallel_corpus.sqlite
    if FEEDBACK_DB.exists() and PARALLEL_DB.exists():
        with sqlite3.connect(str(FEEDBACK_DB)) as fb_conn:
            fb_conn.row_factory = sqlite3.Row
            fb_rows = fb_conn.execute("SELECT * FROM translation_feedback ORDER BY id ASC;").fetchall()

        added_count = 0
        with sqlite3.connect(str(PARALLEL_DB)) as p_conn:
            pc = p_conn.cursor()
            for r in fb_rows:
                direction = r["direction"]
                inp = r["input_text"].strip()
                target = r["corrected_translation"].strip() if (not r["is_correct"] and r["corrected_translation"].strip()) else r["machine_translation"].strip()
                if not inp or not target:
                    continue

                if direction == "sangihe_to_id":
                    sa_txt, id_txt = inp, target
                else:
                    sa_txt, id_txt = target, inp

                ref_id = f"USER_FB_{r['id']}"
                sa_norm = normalize_sangihe(sa_txt).lower()

                pc.execute("SELECT id FROM parallel_sentences WHERE reference_id = ?;", (ref_id,))
                existing = pc.fetchone()
                if not existing:
                    pc.execute(
                        """
                        INSERT INTO parallel_sentences (source_domain, reference_id, sangihe_text, sangihe_normalized, indonesian_tb, indonesian_bimk)
                        VALUES ('user_feedback', ?, ?, ?, ?, ?);
                        """,
                        (ref_id, sa_txt, sa_norm, id_txt, id_txt),
                    )
                    new_id = pc.lastrowid
                    pc.execute(
                        """
                        INSERT INTO parallel_fts (rowid, sangihe_normalized, indonesian_tb, indonesian_bimk)
                        VALUES (?, ?, ?, ?);
                        """,
                        (new_id, sa_norm, id_txt, id_txt),
                    )
                    added_count += 1
            p_conn.commit()
        print(f"[+] Berhasil menambahkan {added_count} pasangan kalimat feedback ke parallel_corpus.sqlite.")

    # 4. Bersihkan llm_cache.sqlite agar prompt baru dengan aturan perubahan bunyi digunakan segar
    cache_db = ROOT_DIR / "data" / "llm_cache.sqlite"
    if cache_db.exists():
        with sqlite3.connect(str(cache_db)) as c_conn:
            c_conn.execute("DELETE FROM llm_cache;")
            c_conn.commit()
        print("[+] Cache LLM dibersihkan agar aturan perubahan bunyi & koreksi terbaru langsung aktif.")


if __name__ == "__main__":
    sync_feedback()
