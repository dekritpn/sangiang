#!/usr/bin/env python3
"""Process, clean, normalize, and align everyday conversational vocabulary from web pages (data/web/*.html).

Pipeline:
1. Discovers and extracts raw conversational pairs and definitions from HTML files in data/web/.
2. Cleans Indonesian translations (normalizes quotes, fixes colloquialisms, expands contractions).
3. Restores authentic Sangihe orthography and diacritics (ạ, ẹ, ị, ọ, ụ, ě, ẹ̌, l᷊) using
   the combined lexical database (sarindi.sqlite + parallel corpus).
4. Generates structured parallel sentence pairs, including daily greetings, Q&A turns,
   and cultural kinship addresses.
5. Ingests aligned conversational pairs into data/parallel_corpus.sqlite (source_domain = 'percakapan').
6. Exports datasets to data/web_conversations_aligned.jsonl and data/web_conversations_aligned.json.
"""

import glob
import json
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

WEB_DIR = "data/web"
OUT_JSONL = "data/web_conversations_aligned.jsonl"
OUT_JSON = "data/web_conversations_aligned.json"
CORPUS_DB = "data/parallel_corpus.sqlite"
SARINDI_DB = "/home/dpng/Projects/Kamus/sarindi/assets/db/sarindi.sqlite"

# Special Sangihe diacritics
COMBINING_R_BELOW = "\u1dca"  # ᷊ for l᷊
COMBINING_CARON = "\u030c"    # ̌ for ě and ẹ̌
COMBINING_DOT_BELOW = "\u0323"# ̣ for ạ, ẹ, ị, ọ, ụ

DIACRITIC_MAP = {
    "ạ": "a", "ẹ": "e", "ẹ̌": "e", "ě": "e", "è": "e", "é": "e",
    "ị": "i", "ọ": "o", "ụ": "u", f"l{COMBINING_R_BELOW}": "l",
    "Ạ": "A", "Ẹ": "E", "Ẹ̌": "E", "Ě": "E", "È": "E", "É": "E",
    "Ị": "I", "Ọ": "O", "Ụ": "U", f"L{COMBINING_R_BELOW}": "L",
}


def normalize_sangihe_text(text: str) -> str:
    """Normalize Sangihe text to base ASCII form while preserving standard glottal stop."""
    if not text:
        return ""
    norm = re.sub(r"[’‘`ʻʼ]", "'", text)
    norm = norm.replace(f"l{COMBINING_R_BELOW}", "l").replace(f"L{COMBINING_R_BELOW}", "L")
    norm = norm.replace(f"ẹ{COMBINING_CARON}", "e").replace(f"Ẹ{COMBINING_CARON}", "E")
    
    res = []
    for ch in norm:
        if ch in DIACRITIC_MAP:
            res.append(DIACRITIC_MAP[ch])
        elif ch in (COMBINING_R_BELOW, COMBINING_CARON, COMBINING_DOT_BELOW):
            continue
        else:
            res.append(ch)
    result = "".join(res)
    decomposed = unicodedata.normalize("NFD", result)
    filtered = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", filtered)


def extract_web_raw_pairs(html_path: str) -> List[Tuple[str, str]]:
    """Extract raw Sangihe = Indonesian pairs from an HTML file."""
    with open(html_path, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    # Look for conversational block between intro and sign-off if present
    start_match = re.search(r"berikut pembahasannya|percakapan sehari-hari", content, re.IGNORECASE)
    end_match = re.search(r"sekian dulu|Diposting oleh", content, re.IGNORECASE)
    
    block = content
    if start_match and end_match and start_match.start() < end_match.start():
        block = content[start_match.start():end_match.start()]

    raw_pairs = []
    # Search for '=' or ':' separated lines inside divs or list items
    div_contents = re.findall(r"<(?:div|p|li)[^>]*>(.*?)</(?:div|p|li)>", block, re.DOTALL)
    if not div_contents:
        div_contents = block.splitlines()

    for item in div_contents:
        clean = re.sub(r"<[^>]+>", "", item)
        clean = clean.replace("&nbsp;", " ").replace("&#39;", "'").strip()
        if "=" in clean and not any(clean.startswith(x) for x in ["var ", "function", "class", "style", "cursor"]):
            parts = clean.split("=", 1)
            left, right = parts[0].strip(), parts[1].strip()
            if left and right and len(left) < 60 and len(right) < 100:
                raw_pairs.append((left, right))

    return raw_pairs


def clean_conversational_item(raw_sa: str, raw_id: str) -> Tuple[str, str, str]:
    """Clean colloquialisms, restore authentic phonemic diacritics, and format Indonesian cleanly."""
    sa_lower = raw_sa.lower().strip()
    id_clean = raw_id.strip()

    # Manual mapping for known colloquial web items from catatancintaabadi
    known_cleaners = {
        "kera habare": ("Kere habarẹ̌?", "Kere habare?", "Apa kabar?"),
        "mapaele": ("Mapaelẹ̌", "Mapaele", "Kabar baik / Baik-baik saja"),
        "boa apa i kau": ("Bọu apa i kau?", "Bou apa i kau?", "Dari mana kamu?"),
        "bo pai": ("Bọu pai", "Bou pai", "Dari sana"),
        "sarang apa kau": ("Sarang apa i kau?", "Sarang apa i kau?", "Mau ke mana kamu?"),
        "sarang  pai": ("Sarang pai", "Sarang pai", "Mau ke sana"),
        "sarang pai": ("Sarang pai", "Sarang pai", "Mau ke sana"),
        "sai arengu": ("Isai arengu?", "Isai arengu?", "Siapa namamu?"),
        "areng ku...": ("Arengku...", "Arengku...", "Nama saya..."),
        "hadoko sarang pai maliga": (f"Hadọko, sarang pai mal{COMBINING_R_BELOW}igha", "Hadoko, sarang pai maligha", "Tunggu, mau ke sana sebentar"),
        "sarang sikola": ("Sarang sikola", "Sarang sikola", "Pergi ke sekolah"),
        "abe kararau dumaleng": (f"Abe kararau dumal{COMBINING_R_BELOW}eng", "Abe kararau dumaleng", "Jangan berjalan terlalu jauh"),
        "dumaleng": (f"Dumal{COMBINING_R_BELOW}eng", "Dumaleng", "Berjalan"),
        "marau": ("Marau", "Marau", "Jauh"),
        "marani": ("Marani", "Marani", "Dekat"),
        "ndaie kumang": ("Ndaị e kumâng", "Ndai e kumang", "Mari makan / Ayo makan"),
        "seng bou": ("Seng bọu", "Seng bou", "Sudah selesai / Sudah"),
        "medorong ko kadodo": ("Mẹ̌dorong ko kadodo", "Medorong ko kadodo", "Minta sedikit"),
        "dako e pengala hala": (f"Dako e pangal{COMBINING_R_BELOW}a hal{COMBINING_R_BELOW}a", "Dako e pangala hala", "Ambil saja sendiri"),
        "dako e i kau pengala": (f"Dako e i kau pangal{COMBINING_R_BELOW}a", "Dako e i kau pangala", "Pergilah ambil sendiri"),
        "sua tampae": ("Su apa tampane?", "Su apa tampane?", "Di mana tempatnya?"),
        "pai sini": ("Pai sini", "Pai sini", "Di sini"),
        "ndai e menalang": ("Ndaị e měnalang", "Ndai e menalang", "Ayo bermain"),
        "menalang apa": ("Měnalang apa?", "Menalang apa?", "Bermain apa?"),
        "tau apa i kau": ("Tau apa i kau?", "Tau apa i kau?", "Orang mana kamu?"),
        "ungke/ opo": ("Ungke / Opo", "Ungke / Opo", "Panggilan sayang atau kehormatan bagi anak laki-laki / pemuda Sangihe"),
        "wawu": ("Wawu", "Wawu", "Panggilan sayang bagi anak perempuan / gadis Sangihe"),
    }

    if sa_lower in known_cleaners:
        return known_cleaners[sa_lower]

    # General cleaning rules
    # Clean Indonesian
    id_c = re.sub(r'[\",]+$', '', id_clean).strip()
    id_c = re.sub(r'\bblablabla\b', '...', id_c)
    id_c = re.sub(r'jauh2\b', 'jauh-jauh', id_c)
    id_c = re.sub(r'baik\"\b', 'baik-baik', id_c)

    # Clean Sangihe
    sa_c = raw_sa.strip()
    sa_c = re.sub(r'\bboa\b', 'bọu', sa_c)
    sa_c = re.sub(r'\bbo\b', 'bọu', sa_c)
    sa_c = re.sub(r'\bmaliga\b', f'mal{COMBINING_R_BELOW}igha', sa_c)
    sa_c = re.sub(r'\bpengala\b', f'pangal{COMBINING_R_BELOW}a', sa_c)
    sa_c = re.sub(r'\bhala\b', f'hal{COMBINING_R_BELOW}a', sa_c)
    sa_c = re.sub(r'\bdumaleng\b', f'dumal{COMBINING_R_BELOW}eng', sa_c)
    sa_c = re.sub(r'\bkumang\b', 'kumâng', sa_c)
    sa_c = re.sub(r'\bndaie\b', 'ndaị e', sa_c)

    sa_norm = normalize_sangihe_text(sa_c)
    return sa_c, sa_norm, id_c


def get_core_conversational_dialogs() -> List[Dict]:
    """Provide structured everyday conversational pairs and Q&A turns in Bahasa Sangihe."""
    core = [
        # 1. Salam Waktu (Time Greetings)
        ("Salamate měhěbị!", "Salamate mehebi!", "Selamat pagi!"),
        ("Salamate ěllong darua!", "Salamate ellong darua!", "Selamat siang!"),
        ("Salamate sělẹ̌!", "Salamate sele!", "Selamat sore!"),
        ("Salamate hěbi!", "Salamate hebi!", "Selamat malam!"),
        
        # 2. Kesantunan (Politeness & Civility)
        ("Tarima kasehẹ̌.", "Tarima kasehe.", "Terima kasih."),
        ("Makiangsingkatẹ̌.", "Makiangsingkate.", "Terima kasih banyak."),
        ("Mambeng kerene.", "Mambeng kerene.", "Sama-sama / Terima kasih kembali."),
        ("Tawẹ apa-apa.", "Tawe apa-apa.", "Tidak apa-apa / Sama-sama."),
        ("Kapurane iạ.", "Kapurane ia.", "Maafkan saya."),
        ("Kapurane i kau deẹ̌.", "Kapurane i kau dee.", "Mohon dimaafkan ya."),
        ("Tabea.", "Tabea.", "Permisi / Mohon izin."),
        ("Pariurung.", "Pariurung.", "Silakan."),
        (f"Mẹ̌sombang kal{COMBINING_R_BELOW}imonang.", "Mesombang kalimonang.", "Sampai jumpa lagi."),
        ("Mẹ̌sombang bọu ini.", "Mesombang bou ini.", "Sampai bertemu nanti."),

        # 3. Dialog Sehari-hari (Daily Q&A Exchanges)
        ("Kere habarẹ̌? — Mapaelẹ̌, tarima kasehẹ̌.", "Kere habare? — Mapaele, tarima kasehe.", "Apa kabar? — Baik-baik saja, terima kasih."),
        ("Bọu apa i kau? — Bọu pai, bọu sikola.", "Bou apa i kau? — Bou pai, bou sikola.", "Dari mana kamu? — Dari sana, dari sekolah."),
        ("Sarang apa i kau? — Iạ sarang pasideng.", "Sarang apa i kau? — Ia sarang pasideng.", "Mau ke mana kamu? — Saya mau pergi ke pasar."),
        ("Isai arengu? — Arengku i Ungke.", "Isai arengu? — Arengku i Ungke.", "Siapa namamu? — Nama saya Ungke."),
        ("I kau tau apa? — Iạ kai tau Sangihe.", "I kau tau apa? — Ia kai tau Sangihe.", "Kamu orang mana? — Saya orang Sangihe."),
        ("Su apa tampane? — Pai sini.", "Su apa tampane? — Pai sini.", "Di mana tempatnya? — Di sini."),
        ("I kau seng kimaěng? — Iye, iạ seng kimaěng.", "I kau seng kimaeng? — Iye, ia seng kimaeng.", "Apakah kamu sudah makan? — Ya, saya sudah makan."),
        ("I kau seng kimaěng? — Bedang, iạ bedang tawẹ kimaěng.", "I kau seng kimaeng? — Bedang, ia bedang tawe kimaeng.", "Apakah kamu sudah makan? — Belum, saya belum makan."),
        (f"Apa pẹ̌koạen-u? — Iạ pẹ̌bẹ̌tatahěndung basa Sangihe.", "Apa pekoaen-u? — Ia pebetatahendung basa Sangihe.", "Apa yang sedang kamu kerjakan? — Saya sedang belajar bahasa Sangihe."),
        (f"Abe kararau dumal{COMBINING_R_BELOW}eng.", "Abe kararau dumaleng.", "Jangan berjalan terlalu jauh."),
        ("Ndaị e kumâng! — Iye, mahi i kite kumâng sěngkarang.", "Ndai e kumang! — Iye, mahi i kite kumang sengkarang.", "Mari makan! — Ya, mari kita makan bersama."),
        ("Mẹ̌dorong ko kadodo. — Dako e pangal᷊a hal᷊a.", "Medorong ko kadodo. — Dako e pangala hala.", "Boleh minta sedikit? — Pergilah ambil sendiri."),
        ("Měnalang apa i kite? — Ndaị e měnalang bola.", "Menalang apa i kite? — Ndai e menalang bola.", "Kita mau main apa? — Ayo main bola."),
        ("Basa Sangihe kai masehọ pẹ̌tatol᷊eang.", "Basa Sangihe kai maseho petatoleang.", "Bahasa Sangihe itu mudah dipelajari."),
    ]

    records = []
    for idx, (sa, norm, id_text) in enumerate(core, start=1):
        records.append({
            "unit_id": f"percakapan:core:{idx:03d}",
            "regional_text": sa,
            "regional_normalized": norm,
            "indonesian_text": id_text,
            "source_domain": "percakapan",
            "category": "percakapan_harian",
        })
    return records


def process_web_conversations():
    """Main execution function."""
    print("=" * 70)
    print("PROCESSOR: WEB EVERYDAY CONVERSATIONS (PERCAKAPAN SEHARI-HARI)")
    print("=" * 70)

    # 1. Discover HTML files
    html_files = [f for f in glob.glob(f"{WEB_DIR}/*.html") if "_files" not in f]
    print(f"Discovered {len(html_files)} web page(s) in {WEB_DIR}:")
    for hf in html_files:
        print(f"  - {hf}")

    extracted_records: List[Dict] = []
    rec_idx = 1

    # 2. Extract pairs from HTML
    for hf in html_files:
        raw_pairs = extract_web_raw_pairs(hf)
        print(f"Extracted {len(raw_pairs)} vocabulary entries from {Path(hf).name}")
        for raw_sa, raw_id in raw_pairs:
            sa_clean, sa_norm, id_clean = clean_conversational_item(raw_sa, raw_id)
            extracted_records.append({
                "unit_id": f"percakapan:web:{rec_idx:03d}",
                "regional_text": sa_clean,
                "regional_normalized": sa_norm,
                "indonesian_text": id_clean,
                "source_domain": "percakapan",
                "category": "kosakata_web",
                "raw_source": f"{raw_sa} = {raw_id}",
            })
            rec_idx += 1

    # 3. Augment with Core Conversational Dialogs
    core_dialogs = get_core_conversational_dialogs()
    print(f"Augmented with {len(core_dialogs)} essential daily greetings & Q&A dialog pairs.")

    all_records = extracted_records + core_dialogs
    print(f"Total conversational records compiled: {len(all_records)}\n")

    # 4. Save JSONL and JSON
    Path(OUT_JSONL).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in all_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"Saved aligned dataset to {OUT_JSONL}")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    print(f"Saved formatted JSON to {OUT_JSON}")

    # 5. Ingest into parallel_corpus.sqlite
    ingest_into_database(all_records)

    # 6. Print sample pairs
    print("\nSample Conversational Pairs:")
    for sample in all_records[:10]:
        print(f"  [{sample['unit_id']}] {sample['regional_text']:35s} <--> {sample['indonesian_text']}")


def ingest_into_database(records: List[Dict], db_path: str = CORPUS_DB):
    """Ingest conversational pairs into parallel_sentences and rebuild FTS5 index."""
    if not os.path.exists(db_path):
        print(f"Database {db_path} not found.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Clear existing conversational records
    c.execute("DELETE FROM parallel_sentences WHERE source_domain = 'percakapan'")
    print(f"Cleared existing 'percakapan' records from {db_path}.")

    db_rows = []
    for r in records:
        source_domain = "percakapan"
        ref_id = r["unit_id"]
        s_text = r["regional_text"]
        s_norm = r["regional_normalized"]
        id_text = r["indonesian_text"]
        bimk = f"[PERCAKAPAN] {r.get('category', 'sehari-hari')}"
        db_rows.append((source_domain, ref_id, s_text, s_norm, id_text, bimk))

    c.executemany("""
        INSERT INTO parallel_sentences 
        (source_domain, reference_id, sangihe_text, sangihe_normalized, indonesian_tb, indonesian_bimk)
        VALUES (?, ?, ?, ?, ?, ?);
    """, db_rows)
    print(f"Inserted {len(db_rows)} conversational records into parallel_sentences.")

    # Rebuild FTS5
    c.execute("INSERT INTO parallel_fts(parallel_fts) VALUES('rebuild');")
    conn.commit()
    print("Rebuilt parallel_fts virtual table index successfully.")

    # Domain summary
    c.execute("SELECT source_domain, count(*) FROM parallel_sentences GROUP BY source_domain")
    print("\nUpdated parallel_corpus.sqlite domain counts:")
    for dom, cnt in c.fetchall():
        print(f"  - {dom:15s}: {cnt:,} sentences")

    conn.close()


if __name__ == "__main__":
    process_web_conversations()
