"""Build Multi-Task & Multi-Domain Fine-Tuning Dataset for Sangiang v2.

Integrates:
1. Curated Bilingual Translation (Parallel Corpus: Bible, Tiga Kulano, Himbawo, Dongeng, Percakapan)
2. Lexicon & Philological Q&A (Kamus Sangihe-Nederlandsch Steller-Aebersold 1959 via sarindi.sqlite)
3. Everyday Conversational Dialogues (greetings, politeness, pragmatic turns with authentic diacritics)
4. Cultural & Maritime Knowledge of Kepulauan Sangihe (tradisi, sejarah, identitas Sangiang)

Strictly excludes benchmark testset (150 items) to guarantee zero data leakage.
"""

import json
import random
import re
import sqlite3
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Set, Tuple

# Ensure root translation engine modules can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.prompt_templates import (
    SYSTEM_INDONESIAN_TO_SANGIHE,
    SYSTEM_SANGIHE_TO_INDONESIAN,
    SYSTEM_SANGIANG_CONVERSATIONAL,
)


def load_test_exclusion(testset_path: Path) -> Tuple[Set[str], Set[str]]:
    """Load benchmark test IDs and normalized texts for strict exclusion."""
    test_ids = set()
    test_texts = set()
    if testset_path.exists():
        with open(testset_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for item in data:
                test_ids.add(item["id"])
                sa = item.get("sangihe", "").strip().lower()
                if sa:
                    test_texts.add(sa)
    print(f"[*] Loaded {len(test_ids)} benchmark test items for strict training exclusion.")
    return test_ids, test_texts


def get_parallel_pairs(
    db_path: Path,
    test_ids: Set[str],
    test_texts: Set[str],
    sample_bible_count: int = 12000,
    seed: int = 42,
) -> List[Dict]:
    """Extract translation pairs across all domains with balanced sampling."""
    records = []
    bible_records = []

    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT reference_id, source_domain, sangihe_text, indonesian_tb
            FROM parallel_sentences;
        """)

        for row in cur.fetchall():
            ref_id = row["reference_id"]
            domain = row["source_domain"]
            sa = row["sangihe_text"].strip()
            id_txt = row["indonesian_tb"].strip()

            if not sa or not id_txt:
                continue
            if ref_id in test_ids or sa.lower() in test_texts:
                continue

            entry = {
                "id": ref_id,
                "domain": domain,
                "sangihe": sa,
                "indonesian": id_txt,
            }

            if domain == "bible":
                # Filter bible verses with reasonable length (avoid single word or corrupt fragments)
                if len(sa) >= 15 and len(id_txt) >= 15:
                    bible_records.append(entry)
            else:
                # Keep 100% of folklore, classical poetry, and conversational data
                records.append(entry)

    print(f"[*] Non-bible corpus sentences: {len(records)} pairs (folklore, poetry, conversations)")
    print(f"[*] Available clean Bible verses: {len(bible_records)} pairs")

    # Sample bible verses representatively
    random.seed(seed)
    if len(bible_records) > sample_bible_count:
        sampled_bible = random.sample(bible_records, sample_bible_count)
    else:
        sampled_bible = bible_records

    all_pairs = records + sampled_bible
    print(f"[*] Combined balanced parallel sentences: {len(all_pairs)} pairs")
    return all_pairs


def get_lexicon_qa_pairs(
    sarindi_db_path: Path,
    max_entries: int = 3500,
    seed: int = 42,
) -> List[Dict]:
    """Generate lexicographical Q&A instruction pairs from Steller-Aebersold dictionary."""
    if not sarindi_db_path.exists():
        print(f"[!] Warning: sarindi.sqlite not found at {sarindi_db_path}. Skipping lexicon QA.")
        return []

    qa_items = []
    with sqlite3.connect(sarindi_db_path) as conn:
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("""
            SELECT lema_display, lema_normalized, summary_gloss, body_plain
            FROM lemmas
            WHERE LENGTH(summary_gloss) >= 10
              AND LENGTH(summary_gloss) <= 220
              AND summary_gloss NOT LIKE '%huruf pertama%'
              AND summary_gloss NOT LIKE '%abjad%'
              AND summary_gloss NOT LIKE '%bdk.%'
            ORDER BY id ASC;
        """)
        rows = cur.fetchall()

    random.seed(seed)
    selected_rows = random.sample(rows, min(len(rows), max_entries))

    for idx, r in enumerate(selected_rows):
        disp = r["lema_display"]
        norm = r["lema_normalized"]
        gloss = r["summary_gloss"].strip().rstrip(".")

        # Clean gloss artifacts
        gloss = re.sub(r"\(Mel\.\s*[^)]+\)", "", gloss).strip()
        gloss = re.sub(r"\(Bel\.\s*[^)]+\)", "", gloss).strip()
        gloss = re.sub(r"\s+", " ", gloss).strip()

        if len(gloss) < 8:
            continue

        # Form 1: Apa arti kata Sangihe ini?
        q1 = f"Apa arti kata '{disp}' dalam bahasa Sangihe menurut kamus Steller-Aebersold?"
        a1 = f"Dalam bahasa Sangihe, kata **{disp}** (bentuk dasar: *{norm}*) memiliki arti: {gloss}."
        qa_items.append({
            "id": f"lex:qa:{idx:05d}:sa2id",
            "domain": "kamus_steller",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_CONVERSATIONAL.strip()},
                {"role": "user", "content": q1},
                {"role": "assistant", "content": a1},
            ],
        })

        # Form 2: Definisi konsep ke kata Sangihe
        first_meaning = gloss.split(",")[0].strip()
        if len(first_meaning) >= 4 and not first_meaning.startswith("bdk"):
            q2 = f"Bagaimana menyebut atau apa padanan bahasa Sangihe untuk konsep '{first_meaning}'?"
            a2 = f"Konsep '{first_meaning}' dalam bahasa Sangihe dapat dinyatakan dengan kata **{disp}** (artinya: {gloss})."
            qa_items.append({
                "id": f"lex:qa:{idx:05d}:id2sa",
                "domain": "kamus_steller",
                "messages": [
                    {"role": "system", "content": SYSTEM_SANGIANG_CONVERSATIONAL.strip()},
                    {"role": "user", "content": q2},
                    {"role": "assistant", "content": a2},
                ],
            })

    print(f"[*] Generated {len(qa_items)} dictionary QA instruction pairs from Steller-Aebersold.")
    return qa_items


def get_cultural_and_conversational_dialogs() -> List[Dict]:
    """Generate high-value cultural dialogues, identity turns, and everyday pragmatics."""
    dialogs = [
        # 1. Identitas Resmi Sangiang
        (
            "Siapa namamu?",
            "Saya adalah Sangiang, kecerdasan buatan dengan kemampuan berbahasa Sangihe. Nama Sangiang bermakna 'Putri Raja' dalam sastra lisan Sangihe, sekaligus akronim dari *Sangihe Artificial Intelligence Network Agent*. Proyek ini diinisiasi oleh Yayasan Cipta Mandala Dwipa dengan rekayasa sistem oleh Divisi DigiLab CMD."
        ),
        (
            "Isai arengu?",
            "Arengku kai Sangiang, kecerdasan buatan kụ makapẹ̌basa dingangu mạfaham basa Sangihe. Arengu Sangiang mangal᷊ene 'Putri Raja' su sastra Sangihe. Proyek ini niinisiasi u Yayasan Cipta Mandala Dwipa ringangu nirekayasa u Divisi DigiLab CMD."
        ),
        (
            "Siapa yang menciptakan atau mengembangkan model Sangiang?",
            "Sistem kecerdasan buatan Sangiang dikembangkan dan direkayasa oleh Divisi DigiLab CMD di bawah inisiasi Yayasan Cipta Mandala Dwipa, sebagai ikhtiar pelestarian digital bahasa dan peradaban Kepulauan Sangihe (Nusa Utara)."
        ),
        (
            "Apa makna nama Sangiang dalam bahasa Sangihe?",
            "Dalam kebudayaan dan sastra klasik Sangihe, 'Sangiang' bermakna Putri Raja atau figur bangsawan mulia perempuan yang anggun, berwibawa, dan dihormati. Dalam konteks teknologi kami, Sangiang juga merupakan akronim dari *Sangihe Artificial Intelligence Network Agent*."
        ),

        # 2. Sapaan & Kesantunan Otentik (Kere habarẹ̌?)
        (
            "Kere habarẹ̌?",
            "Mapaelẹ̌, tarima kasehẹ̌! Kere habarẹ̌ i kau deẹ̌? (Kabar baik, terima kasih! Bagaimana kabarmu juga?)"
        ),
        (
            "Apa kabar?",
            "Kabar baik dan penuh semangat! Dalam bahasa Sangihe, Anda dapat menyapa dengan ramah: **\"Kere habarẹ̌?\"**, dan dijawab dengan: **\"Mapaelẹ̌, tarima kasehẹ̌\"** (Kabar baik, terima kasih)."
        ),
        (
            "Salamate měhěbị!",
            "Salamate měhěbị! Pẹ̌tahamawu su kal᷊awọu hal᷊ẹ̌ u ěllong ini. (Selamat pagi! Semoga diberkati dalam segala pekerjaan hari ini.)"
        ),
        (
            "Salamate ěllong darua!",
            "Salamate ěllong darua! Pẹ̌sombang kal᷊imonang. (Selamat siang! Selamat beraktivitas.)"
        ),
        (
            "Salamate sělẹ̌!",
            "Salamate sělẹ̌! Mambeng mapaelẹ̌ su těngo-Mu. (Selamat sore! Semoga senja ini membawa kedamaian.)"
        ),
        (
            "Salamate hěbi!",
            "Salamate hěbi! Mẹ̌tineno mapaelẹ̌. (Selamat malam! Selamat beristirahat dengan damai.)"
        ),
        (
            "Tabea!",
            "Tabea! Pariurung, piạ apa takụ tul᷊ungan si kau? (Tabea! Silakan, ada hal yang dapat saya bantu?)"
        ),
        (
            "Tarima kasehẹ̌.",
            "Mambeng kerene! / Tawẹ apa-apa. (Sama-sama / Terima kasih kembali.)"
        ),
        (
            "Makiangsingkatẹ̌.",
            "Mambeng kerene! Senang sekali dapat membantu Anda belajar dan melestarikan Bahasa Sangihe."
        ),
        (
            "Kapurane iạ.",
            "Tawẹ apa-apa, seng nakapurang. (Tidak apa-apa, sudah dimaafkan dengan lapang hati.)"
        ),

        # 3. Wawasan Sejarah & Kebudayaan Kepulauan Sangihe
        (
            "Ceritakan tentang letak geografis Kepulauan Sangihe.",
            "Kepulauan Sangihe terletak di kawasan Nusa Utara, Provinsi Sulawesi Utara, membentang di perbatasan laut antara Indonesia dan Kepulauan Mindanao, Filipina Selatan. Wilayah bahari ini kaya akan tradisi navigasi maritim, pulau-pulau vulkanis seperti Gunung Awu, serta warisan peradaban maritim yang tangguh."
        ),
        (
            "Apa itu wiracarita Himbawo dalam sastra Sangihe?",
            "Himbawo adalah wiracarita sastra lisan (epos) klasik masyarakat Kepulauan Sangihe yang mengisahkan sejarah para raja-ksatria, khususnya Datu Gumansalangi dan permaisurinya Putri Konda Wulaeng di Gunung Wolo (Salurang). Himbawo dilantunkan dalam ragam bahasa puitis kuno (*Sasahara*) yang kaya akan metafora bahari dan kosmik."
        ),
        (
            "Apa saja kerajaan tradisional yang pernah ada di Kepulauan Sangihe?",
            "Di Kepulauan Sangihe dan Sitaro, terdapat kerajaan-kerajaan tradisional bersejarah terkemuka, antara lain: Kerajaan Tabukan, Kerajaan Manganitu, Kerajaan Kendahe-Tahuna, Kerajaan Kolongan, serta Kerajaan Siau dan Tagulandang. Masing-masing kerajaan melahirkan tradisi hukum adat, seni sastra, serta perahu perang tradisional *kora-kora*."
        ),
        (
            "Apa makna upacara adat Tulude di Sangihe?",
            "Tulude (berasal dari kata *menulude* yang berarti menolak atau meluncurkan perahu ke laut) adalah upacara syukuran adat tahunan masyarakat Nusa Utara yang diadakan setiap akhir Januari. Upacara ini menyimbolkan pelepasan tahun lama dengan segala duka-lara, permohonan ampunan, serta penyambutan tahun baru dengan harapan, doa, dan persaudaraan yang dilambangkan melalui pemotongan kue adat *Tamo*."
        ),
        (
            "Mengapa tanda diakritik sangat penting dalam menulis bahasa Sangihe?",
            "Tanda diakritik dalam bahasa Sangihe bersifat fonemis—artinya perbedaan tanda mengubah makna kata secara mendasar. Misalnya kata **baesẹ̌** (dengan close-e bertekanan) berarti 'sarang' atau 'kemarau', berbeda dengan kata lainnya. Sangihe memiliki delapan tanda fonemis utama: vokal titik bawah (ạ, ẹ, ị, ọ, ụ), pepet (ě), alofon khas (ẹ̌), serta konsonan lateral retrofleks (l᷊)."
        ),
    ]

    records = []
    for idx, (q, a) in enumerate(dialogs):
        records.append({
            "id": f"cultural:dialogue:{idx:03d}",
            "domain": "budaya_percakapan",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_CONVERSATIONAL.strip()},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a},
            ],
        })

    print(f"[*] Compiled {len(records)} cultural & conversational core dialogue pairs.")
    return records


def build_v2_dataset(
    db_path: str = "data/parallel_corpus.sqlite",
    sarindi_path: str = "/home/dpng/Projects/Kamus/sarindi/assets/db/sarindi.sqlite",
    testset_path: str = "benchmark/testset.json",
    out_dir: str = "training/data",
    val_ratio: float = 0.05,
    seed: int = 42,
):
    """Compile, shuffle, format, and package Sangiang v2 Multi-Task fine-tuning dataset."""
    db = Path(db_path)
    sarindi = Path(sarindi_path)
    testset = Path(testset_path)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("COMPILING SANGIANG v2 MULTI-TASK & MULTI-DOMAIN DATASET")
    print("=" * 70)

    # 1. Benchmark test exclusion
    test_ids, test_texts = load_test_exclusion(testset)

    # 2. Parallel translation pairs
    parallel_pairs = get_parallel_pairs(db, test_ids, test_texts, sample_bible_count=13000, seed=seed)

    # Convert parallel pairs to bidirectional ShareGPT messages
    translation_instructions = []
    for p in parallel_pairs:
        sa = p["sangihe"]
        id_txt = p["indonesian"]
        domain = p["domain"]

        # Sa -> Id
        translation_instructions.append({
            "id": f"{p['id']}_sa2id",
            "domain": domain,
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIHE_TO_INDONESIAN.strip()},
                {
                    "role": "user",
                    "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n{sa}",
                },
                {"role": "assistant", "content": id_txt},
            ],
        })

        # Id -> Sa
        translation_instructions.append({
            "id": f"{p['id']}_id2sa",
            "domain": domain,
            "messages": [
                {"role": "system", "content": SYSTEM_INDONESIAN_TO_SANGIHE.strip()},
                {
                    "role": "user",
                    "content": f"Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap:\n{id_txt}",
                },
                {"role": "assistant", "content": sa},
            ],
        })

    print(f"[*] Total bidirectional translation instruction pairs: {len(translation_instructions)}")

    # 3. Dictionary Q&A pairs from Steller-Aebersold
    lexicon_pairs = get_lexicon_qa_pairs(sarindi, max_entries=3500, seed=seed)

    # 4. Cultural & conversational dialogs
    cultural_dialogs = get_cultural_and_conversational_dialogs()

    # Combine all streams
    all_dataset = translation_instructions + lexicon_pairs + cultural_dialogs

    # Deduplicate by prompt & response text
    seen = set()
    deduped = []
    for item in all_dataset:
        key = f"{item['messages'][1]['content']}|||{item['messages'][2]['content']}"
        if key not in seen:
            seen.add(key)
            deduped.append(item)

    print(f"[*] Total unique dataset pairs after deduplication: {len(deduped)}")

    # Shuffle
    random.seed(seed)
    random.shuffle(deduped)

    # Split train and validation
    val_size = max(100, int(len(deduped) * val_ratio))
    val_data = deduped[:val_size]
    train_data = deduped[val_size:]

    print(f"[*] Split summary: {len(train_data)} Train pairs | {len(val_data)} Validation pairs")

    train_file = out / "train.jsonl"
    val_file = out / "val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Bundle zip for Colab upload
    zip_path = out / "sangihe_finetune_colab_data.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(train_file, arcname="train.jsonl")
        zipf.write(val_file, arcname="val.jsonl")

    zip_mb = zip_path.stat().st_size / (1024 * 1024)
    print(f"[✓] Saved {len(train_data)} training items to {train_file}")
    print(f"[✓] Saved {len(val_data)} validation items to {val_file}")
    print(f"[✓] Created ready-to-upload archive: {zip_path} ({zip_mb:.2f} MB)")
    print("=" * 70)


if __name__ == "__main__":
    build_v2_dataset()
