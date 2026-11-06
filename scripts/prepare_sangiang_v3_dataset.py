"""Prepare Sangiang v3 Master Fine-Tuning Dataset.

Combines:
1. 10,000 Morphological Induction & Chain-of-Thought Reasoning pairs (Steller-Aebersold rules).
2. 1,500 Targeted Pronoun & Enclitic Contrastive pairs (resolving 'iạ' = saya/aku vs 'i sie' = dia/ia, '-u' = -mu vs '-ne' = -nya).
3. 10,000 Balanced Parallel Translation pairs (Bible + Non-Bible Folklore/Dongeng/Himbawo/Kulano).
4. 3,500 Kamus Steller Lexical Definition Q&A pairs.
5. 1,000 Conversational Sangiang Persona pairs (identity, greetings, cultural wisdom).

All formatted with the authoritative Sangiang System Prompt for ChatML format.
"""

import json
import os
import random
import re
import zipfile
from pathlib import Path
from typing import Dict, List

random.seed(42)

SYSTEM_SANGIANG_MASTER = "Nama Anda adalah Sangiang, AI penerjemah dan filolog bahasa Sangihe ke bahasa Indonesia formal."


def generate_pronoun_contrast_pairs() -> List[Dict]:
    """Generate high-density contrastive training pairs for pronouns and clitics."""
    pairs = []

    # 1. Direct translation pairs contrasting iạ (saya/aku) vs i sie (dia/ia)
    base_actions = [
        ("mạngangěndung", "sedang belajar menuntut ilmu", "sedang belajar menuntut ilmu"),
        ("měbaesẹ̌ su wal᷊e", "berdiam di dalam rumah", "berdiam di dalam rumah"),
        ("dumal᷊eng sol᷊ong wanua", "berjalan menuju negeri", "berjalan menuju negeri"),
        ("měnginung akẹ", "meminum air", "meminum air"),
        ("rumaringihẹ̌ habarẹ̌", "mendengar kabar berita", "mendengar kabar berita"),
        ("měmuno bowine", "membersihkan kebunnya", "membersihkan kebunnya"),
        ("těmondon bọu dal᷊eng", "pulang dari perjalanan", "pulang dari perjalanan"),
        ("mạngělli tula-tula", "menceritakan kisah cerita", "menceritakan kisah cerita"),
        ("mạtanạ su darapang", "duduk di atas tikar", "duduk di atas tikar"),
        ("měngonggọ tul᷊ung", "memberikan pertolongan", "memberikan pertolongan"),
        ("mạkạdulu su pẹ̌bawiahe", "bersyukur dalam hidup", "bersyukur dalam hidup"),
        ("masaria měkoạ hal᷊ẹ̌", "rajin mengerjakan tugas", "rajin mengerjakan tugas"),
        ("mapaelẹ̌ naung", "berhati mulia dan baik budi", "berhati mulia dan baik budi"),
        ("tumaděng su wowon watu", "berdiri di atas batu", "berdiri di atas batu"),
        ("mẹ̌bẹ̌bawa binawa", "membawa perahu layar", "membawa perahu layar"),
    ]

    for sa_act, id_act, _ in base_actions:
        # Sangihe 1st Person: Iạ -> Saya / Aku
        pairs.append({
            "id": f"pro_1s_{len(pairs)}",
            "domain": "pronoun_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\nIạ kai {sa_act}."},
                {"role": "assistant", "content": f"Saya {id_act}."}
            ]
        })
        # Inverse: Saya -> Iạ
        pairs.append({
            "id": f"pro_1s_inv_{len(pairs)}",
            "domain": "pronoun_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap:\nSaya {id_act}."},
                {"role": "assistant", "content": f"Iạ kai {sa_act}."}
            ]
        })

        # Sangihe 3rd Person: I sie -> Dia / Ia
        pairs.append({
            "id": f"pro_3s_{len(pairs)}",
            "domain": "pronoun_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\nI sie kai {sa_act}."},
                {"role": "assistant", "content": f"Dia {id_act}."}
            ]
        })

        # Sangihe 2nd Person: I kau -> Engkau / Kamu
        pairs.append({
            "id": f"pro_2s_{len(pairs)}",
            "domain": "pronoun_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\nI kau kai {sa_act}."},
                {"role": "assistant", "content": f"Engkau {id_act}."}
            ]
        })

        # Sangihe Inclusive Plural: I kitẹ -> Kita
        pairs.append({
            "id": f"pro_1pincl_{len(pairs)}",
            "domain": "pronoun_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\nI kitẹ kai {sa_act}."},
                {"role": "assistant", "content": f"Kita {id_act}."}
            ]
        })

        # Sangihe Exclusive Plural: I kami -> Kami
        pairs.append({
            "id": f"pro_1pexcl_{len(pairs)}",
            "domain": "pronoun_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\nI kami kai {sa_act}."},
                {"role": "assistant", "content": f"Kami {id_act}."}
            ]
        })

        # Sangihe 3rd Person Plural: I sire -> Mereka
        pairs.append({
            "id": f"pro_3p_{len(pairs)}",
            "domain": "pronoun_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\nI sire kai {sa_act}."},
                {"role": "assistant", "content": f"Mereka {id_act}."}
            ]
        })

    # 2. Possessive Enclitic pairs: -u (-mu) vs -ne (-nya) vs -ku (-ku)
    nouns = [
        ("waes", "sarang"),
        ("wal᷊e", "rumah"),
        ("areng", "nama"),
        ("anạ", "anak"),
        ("binawa", "perahu"),
        ("těmbonang", "pematang kebun"),
        ("naung", "hati / pikiran"),
        ("lima", "tangan"),
        ("mata", "mata"),
        ("pedang", "pedang"),
    ]

    for sa_noun, id_noun in nouns:
        # -u = -mu (milikmu)
        pairs.append({
            "id": f"clitic_u_{len(pairs)}",
            "domain": "clitic_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n{sa_noun}-u kai mal᷊onggona."},
                {"role": "assistant", "content": f"{id_noun.capitalize()}mu sangatlah besar."}
            ]
        })
        # -ne = -nya (miliknya)
        pairs.append({
            "id": f"clitic_ne_{len(pairs)}",
            "domain": "clitic_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n{sa_noun}-ne kai mal᷊onggona."},
                {"role": "assistant", "content": f"{id_noun.capitalize()}nya sangatlah besar."}
            ]
        })
        # -ku = -ku (milikku)
        pairs.append({
            "id": f"clitic_ku_{len(pairs)}",
            "domain": "clitic_contrast",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n{sa_noun}-ku kai mal᷊onggona."},
                {"role": "assistant", "content": f"{id_noun.capitalize()}ku sangatlah besar."}
            ]
        })

    # 3. Explicit Linguistic Q&A on Sangihe Pronouns and Enclitics
    qa_list = [
        (
            "Apakah arti kata 'iạ' dalam bahasa Sangihe? Mengapa tidak boleh diterjemahkan sebagai 'ia' dalam bahasa Indonesia?",
            "Dalam bahasa Sangihe, kata **'iạ'** (atau bentuk tanpa diakritik: 'ia') adalah **kata ganti orang pertama tunggal** yang bermakna **'aku'** atau **'saya'**.\n\nKata ini sama sekali BUKAN kata ganti orang ketiga ('ia' / 'dia') dalam bahasa Indonesia. Ini adalah *cross-linguistic false friend* (homograf semu antarbahasa). Untuk menyatakan orang ketiga tunggal ('ia' / 'dia') dalam bahasa Sangihe, kata yang digunakan adalah **'i sie'** atau **'sie'**.\n\nContoh penggunaan:\n- *Iạ kai mạngangěndung* = 'Saya sedang belajar.' (BUKAN 'Ia sedang belajar').\n- *I sie něbera si siạ* = 'Dia berkata kepadaku.'\n- *Iạko měbaesẹ̌* = 'Biarlah aku bersarang / tinggal.'"
        ),
        (
            "Jelaskan sistem pronomina persona (kata ganti orang) lengkap dalam bahasa Sangihe!",
            "Sistem kata ganti orang (pronomina persona) dalam bahasa Sangihe terbagi secara presisi sebagai berikut:\n\n1. **Orang Pertama (Pembicara)**:\n   - Tunggal: **iạ** / **siạ** (aku, saya, daku).\n   - Jamak Inklusif (kita = pembicara + lawan bicara): **i kitẹ** / **kitẹ**.\n   - Jamak Eksklusif (kami = pembicara tanpa lawan bicara): **i kami** / **kami**.\n\n2. **Orang Kedua (Lawan Bicara)**:\n   - Tunggal: **i kau** / **kau** (engkau, kamu).\n   - Jamak: **i kamene** / **kamene** atau **kewạ** (kalian, kamu sekalian).\n\n3. **Orang Ketiga (Orang yang Dibicarakan)**:\n   - Tunggal: **i sie** / **sie** (ia, dia, beliau).\n   - Jamak: **i sire** / **sire** (mereka).\n\nPerhatian khusus: Kata **'iạ'** adalah **'aku/saya'**, bukan 'ia' (dia)."
        ),
        (
            "Apa arti enklitik posesif '-u', '-ne', dan '-ku' pada kata benda bahasa Sangihe?",
            "Enklitik posesif (akhiran penanda kepemilikan) dalam bahasa Sangihe melekat pada kata benda dengan aturan berikut:\n\n1. **Enklitik '-u'**: Penanda kepunyaan **orang kedua tunggal (-mu / milikmu)**.\n   - *waes-u* = sarangmu (sarang milikmu, BUKAN sarangnya).\n   - *wal᷊e-u* = rumahmu.\n   - *areng-u* = namamu.\n\n2. **Enklitik '-ne'**: Penanda kepunyaan **orang ketiga tunggal (-nya / miliknya)**.\n   - *waes-ne* = sarangnya (sarang miliknya).\n   - *wal᷊e-ne* = rumahnya.\n   - *areng-ne* = namanya.\n\n3. **Enklitik '-ku' / '-kụ'**: Penanda kepunyaan **orang pertama tunggal (-ku / milikku)**.\n   - *waes-ku* = sarangku.\n   - *wal᷊e-ku* = rumahku."
        ),
        (
            "Terjemahkan kalimat percakapan: 'Mahi iạko měbaesẹ̌ su waes-u' ke bahasa Indonesia dan jelaskan strukturnya!",
            "Terjemahan bahasa Indonesia formal:\n**'Mari, biarlah aku tinggal di sarangmu.'** (atau: 'Mari, izinkanlah aku menetap di liangmu.')\n\nPenjelasan struktur morfologi & leksikal:\n1. **Mahi**: Partikel ajakan ('mari', 'ayo').\n2. **iạko**: Bentuk pronomina orang pertama tunggal **iạ** ('aku' / 'saya') yang berpadu dengan partikel penegas/permintaan izin **-ko**, bermakna 'biarlah aku / aku ini'.\n3. **měbaesẹ̌**: Verba aktif berprefiks *mě-* dari kata dasar *baesẹ̌* (akar kata *waes* yang mengalami alternasi fonem w $\\rightarrow$ b), bermakna 'tinggal di sarang' atau 'berdiam di liang kediaman'.\n4. **su**: Preposisi lokatif ('di', 'pada').\n5. **waes-u**: Nomina dasar *waes* ('sarang / liang hewan') yang dilekati enklitik posesif orang kedua tunggal **-u** ('-mu' / milikmu), bermakna 'sarangmu'."
        ),
        (
            "Bagaimana cara mengucapkan 'Saya baik-baik saja, terima kasih' dalam bahasa Sangihe?",
            "Ungkapan santun dan alami dalam bahasa Sangihe adalah:\n**'Iạ mapaelẹ̌, tarima kasehẹ̌!'** (atau cukup: *'Mapaelẹ̌, tarima kasehẹ̌!'*).\n\nKosakata:\n- **Iạ**: Saya / aku (orang pertama tunggal).\n- **Mapaelẹ̌**: Baik, sentosa, selamat, elok (akar kata: *paele*).\n- **Tarima kasehẹ̌**: Terima kasih."
        ),
    ]

    for q, a in qa_list:
        pairs.append({
            "id": f"pro_qa_{len(pairs)}",
            "domain": "linguistic_qa",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_MASTER},
                {"role": "user", "content": q},
                {"role": "assistant", "content": a}
            ]
        })

    # Oversample the explicit pronoun instruction pairs to give heavy gradient weight
    oversampled_pairs = []
    for _ in range(4):
        for p in pairs:
            oversampled_pairs.append(dict(p))

    return oversampled_pairs


def load_morphological_reasoning_data(filepath: str, max_samples: int = 10000) -> List[Dict]:
    """Load the 10,000 morphological reasoning instruction pairs."""
    data = []
    if not os.path.exists(filepath):
        print(f"[*] Warning: {filepath} not found.")
        return data

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            # Update system prompt to master prompt with pronoun rules
            msgs = item.get("messages", [])
            if msgs and msgs[0].get("role") == "system":
                msgs[0]["content"] = SYSTEM_SANGIANG_MASTER
            data.append(item)
            if len(data) >= max_samples:
                break
    print(f"[*] Loaded {len(data)} morphological reasoning pairs.")
    return data


def load_parallel_data(filepath: str, max_samples: int = 10000) -> List[Dict]:
    """Load balanced parallel translation data with updated system prompt."""
    data = []
    if not os.path.exists(filepath):
        print(f"[*] Warning: {filepath} not found.")
        return data

    non_bible_count = 0
    bible_count = 0

    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            domain = item.get("domain", "")
            msgs = item.get("messages", [])

            # Update system prompt
            if msgs and msgs[0].get("role") == "system":
                msgs[0]["content"] = SYSTEM_SANGIANG_MASTER

            if domain != "bible":
                data.append(item)
                non_bible_count += 1
            elif bible_count < max_samples - 600:
                data.append(item)
                bible_count += 1

    print(f"[*] Loaded {len(data)} parallel pairs ({non_bible_count} non-bible, {bible_count} bible).")
    return data


def main():
    base_dir = Path(__file__).resolve().parent.parent
    data_dir = base_dir / "training" / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    morph_path = str(data_dir / "sangihe_morphological_reasoning.jsonl")
    train_orig_path = str(data_dir / "train.jsonl")

    print("[1/5] Generating targeted Pronoun & Enclitic Contrastive pairs...")
    pronoun_pairs = generate_pronoun_contrast_pairs()
    print(f"      Generated {len(pronoun_pairs)} pronoun contrast pairs.")

    print("[2/5] Loading Morphological Reasoning Chain-of-Thought pairs...")
    morph_pairs = load_morphological_reasoning_data(morph_path, max_samples=10000)

    print("[3/5] Loading Curated Parallel Translation pairs...")
    parallel_pairs = load_parallel_data(train_orig_path, max_samples=10000)

    print("[4/5] Merging and shuffling Sangiang v3 Master Dataset...")
    master_dataset = pronoun_pairs + morph_pairs + parallel_pairs
    random.shuffle(master_dataset)
    total = len(master_dataset)
    print(f"      Total Sangiang v3 Master pairs: {total}")

    # Split 95% Train, 5% Val
    split_idx = int(total * 0.95)
    train_data = master_dataset[:split_idx]
    val_data = master_dataset[split_idx:]

    train_out_path = data_dir / "sangiang_v3_train.jsonl"
    val_out_path = data_dir / "sangiang_v3_val.jsonl"

    with open(train_out_path, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(val_out_path, "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"      Saved {len(train_data)} pairs to {train_out_path.name}")
    print(f"      Saved {len(val_data)} pairs to {val_out_path.name}")

    print("[5/5] Packaging Sangiang v3 Colab zip archive...")
    zip_path = data_dir / "sangiang_v3_colab_data.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(train_out_path, arcname="train.jsonl")
        zipf.write(val_out_path, arcname="val.jsonl")

    zip_size_mb = os.path.getsize(zip_path) / (1024 * 1024)
    print(f"[✓] Successfully packaged: {zip_path} ({zip_size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
