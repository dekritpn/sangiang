#!/usr/bin/env python3
"""
Membangun database SQLite Kamus Sangihe-Indonesia Modern (`data/kamus_sangihe_modern.sqlite`)
berdasarkan seluruh capaian terkini dari proyek `/home/dpng/Projects/Kamus/Sangihe`.

Sumber data yang digabungkan (berdasarkan urutan prioritas tertinggi):
1. `data/manual_overrides.json` (1.293 entri tinjauan manual & audit)
2. `data/kamus_mini_1000_verified.json` (1.000 kosakata inti terverifikasi)
3. `data/audit_kandidat_batch2_1000.csv` (159 lema teraudit Batch-2 + 841 kandidat leksikon baru)
4. `analisis_linguistik/data/kutipan_alkitab_terverifikasi.json` (112 lema terverifikasi)
5. `analisis_linguistik/data/kutipan_tambahan_korpus.json` (74 lema terverifikasi)
6. `analisis_linguistik/data/keluarga_kata_dan_derivasi.json` (687 turunan keluarga kata)
7. `analisis_linguistik/data/inventaris_afiks_lengkap.json` & `perubahan_bunyi_dan_morfofonemik.json`
8. `data/dictionary_master.json` (38.151 lema hasil penyelaras kata korpus Sangihe - Indonesia Masa Kini / BIMK & TB)

Skema database dirancang 100% kompatibel dengan `LexicalRetriever` (`lemmas`, `sublemmas`,
`id_index`, `lemmas_fts`) ditambah kolom dan tabel pengayaan linguistik (`pos`, `stem`,
`freq_count`, `confidence`, `tier`, `word_families`, `morphology_rules`).
"""

import csv
import json
import os
import re
import sqlite3
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from morphology.normalizer import normalize_sangihe

KAMUS_SANGIHE_DIR = Path("/home/dpng/Projects/Kamus/Sangihe")
DATA_DIR = KAMUS_SANGIHE_DIR / "data"
LING_DATA_DIR = KAMUS_SANGIHE_DIR / "analisis_linguistik" / "data"

OUTPUT_DB_PATH = ROOT_DIR / "data" / "kamus_sangihe_modern.sqlite"

INDONESIAN_STOPWORDS = {
    "dan", "di", "ke", "dari", "yang", "pada", "untuk", "dengan", "ini", "itu",
    "atau", "adalah", "ia", "dia", "mereka", "kita", "kami", "kamu", "aku", "saya",
    "akan", "telah", "sudah", "bisa", "dapat", "ada", "tidak", "bukan", "pun",
    "juga", "lalu", "kemudian", "maka", "bahwa", "oleh", "karena", "kepadanya",
    "kepada", "sang", "seekor", "seorang", "sebuah", "para", "sedang", "dalam",
    "sebagai", "seperti", "kata", "partikel", "penanda", "awalan", "akhiran",
    "sisipan", "bentuk", "jamak", "tunggal", "orang", "hal", "sesuatu", "tempat",
}


def extract_id_keywords(meaning: str) -> List[Tuple[str, bool]]:
    """Ekstrak kata kunci bahasa Indonesia dari string definisi untuk tabel id_index."""
    if not meaning:
        return []
    # Hapus keterangan dalam kurung seperti (objek), (subjek), dll.
    cleaned = re.sub(r"\([^)]*\)", " ", meaning)
    # Pisahkan berdasarkan titik koma atau koma
    parts = [p.strip() for p in re.split(r"[;,/]", cleaned) if p.strip()]
    keywords: List[Tuple[str, bool]] = []
    seen: Set[str] = set()

    for idx, part in enumerate(parts):
        is_primary = (idx < 2)
        # Jika frasa pendek (1-2 kata), simpan utuh dan per kata
        words = [w.strip().lower() for w in re.findall(r"[a-zA-Z\-]+", part) if len(w.strip()) >= 2]
        if not words:
            continue
        if len(words) == 1:
            w = words[0]
            if w not in seen:
                seen.add(w)
                keywords.append((w, is_primary))
        else:
            phrase = " ".join(words)
            if len(words) <= 2 and phrase not in seen:
                seen.add(phrase)
                keywords.append((phrase, is_primary))
            for w in words:
                if len(w) >= 3 and w not in INDONESIAN_STOPWORDS and w not in seen:
                    seen.add(w)
                    keywords.append((w, False))
    return keywords


def load_all_sources() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    """Muat dan gabungkan seluruh sumber data Kamus/Sangihe berdasarkan prioritas."""
    # 1. Daftar nama diri Alkitab yang harus dikecualikan jika belum disetujui manual
    proper_names: Set[str] = set()
    proper_path = DATA_DIR / "biblical_proper_names.json"
    if proper_path.exists():
        with open(proper_path, "r", encoding="utf-8") as f:
            bpn_data = json.load(f)
            if isinstance(bpn_data, list):
                for item in bpn_data:
                    if isinstance(item, dict) and item.get("lemma"):
                        proper_names.add(item["lemma"].strip().lower())
            elif isinstance(bpn_data, dict):
                proper_names.update(k.strip().lower() for k in bpn_data.keys())

    # 2. Muat dictionary_master.json sebagai dasar
    master_path = DATA_DIR / "dictionary_master.json"
    with open(master_path, "r", encoding="utf-8") as f:
        master_raw: Dict[str, Dict[str, Any]] = json.load(f)

    # 3. Muat manual_overrides.json
    overrides_path = DATA_DIR / "manual_overrides.json"
    overrides_raw: Dict[str, Dict[str, Any]] = {}
    if overrides_path.exists():
        with open(overrides_path, "r", encoding="utf-8") as f:
            overrides_raw = json.load(f)

    # 4. Muat kamus_mini_1000_verified.json
    mini_path = DATA_DIR / "kamus_mini_1000_verified.json"
    mini_raw: Dict[str, Dict[str, Any]] = {}
    if mini_path.exists():
        with open(mini_path, "r", encoding="utf-8") as f:
            mini_raw = json.load(f)

    # 5. Muat audit_kandidat_batch2_1000.csv
    batch2_path = DATA_DIR / "audit_kandidat_batch2_1000.csv"
    batch2_audited: Dict[str, Dict[str, Any]] = {}
    batch2_candidates: Dict[str, Dict[str, Any]] = {}
    if batch2_path.exists():
        with open(batch2_path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                lema = row.get("lema_sangihe", "").strip()
                if not lema:
                    continue
                status = row.get("status_audit", "").strip().upper()
                pos = (row.get("koreksi_pos") or row.get("dugaan_pos") or "").strip()
                stem = (row.get("koreksi_kata_dasar") or row.get("kata_dasar") or lema).strip()
                meaning = (row.get("koreksi_padanan") or row.get("dugaan_padanan") or "").strip()
                freq = int(row.get("frekuensi_residu") or 0)
                ex_list = []
                if row.get("contoh_sangihe") and row.get("contoh_indonesia"):
                    ex_list.append({
                        "ref": row.get("rujukan_ayat", ""),
                        "sangihe": row.get("contoh_sangihe", ""),
                        "indonesia": row.get("contoh_indonesia", ""),
                    })
                item_data = {
                    "lemma": lema,
                    "pos": pos,
                    "stem": stem,
                    "meaning": meaning,
                    "count": freq,
                    "status_audit": status,
                    "examples": ex_list,
                    "alternatives": row.get("alternatif_indonesia", ""),
                }
                if status in ("OK", "UBAH", "BENAR", "EDIT", "HAPUS", "NAMA"):
                    batch2_audited[lema] = item_data
                else:
                    batch2_candidates[lema] = item_data

    # 6. Muat data terverifikasi dari analisis_linguistik/data
    kutipan_ver_path = LING_DATA_DIR / "kutipan_alkitab_terverifikasi.json"
    kutipan_ver: Dict[str, Dict[str, Any]] = {}
    if kutipan_ver_path.exists():
        with open(kutipan_ver_path, "r", encoding="utf-8") as f:
            kutipan_ver = json.load(f)

    kutipan_tam_path = LING_DATA_DIR / "kutipan_tambahan_korpus.json"
    kutipan_tam: Dict[str, Dict[str, Any]] = {}
    if kutipan_tam_path.exists():
        with open(kutipan_tam_path, "r", encoding="utf-8") as f:
            kutipan_tam = json.load(f)

    keluarga_path = LING_DATA_DIR / "keluarga_kata_dan_derivasi.json"
    keluarga_raw: Dict[str, Dict[str, Any]] = {}
    keluarga_lemmas: Dict[str, Dict[str, Any]] = {}
    if keluarga_path.exists():
        with open(keluarga_path, "r", encoding="utf-8") as f:
            keluarga_raw = json.load(f)
            for root_key, fam in keluarga_raw.items():
                base_gloss = fam.get("base_gloss", "")
                for form in fam.get("forms", []):
                    fl = form.get("lemma", "").strip()
                    if fl:
                        ex = form.get("example")
                        keluarga_lemmas[fl] = {
                            "lemma": fl,
                            "pos": form.get("pos", ""),
                            "stem": root_key,
                            "meaning": form.get("meaning", ""),
                            "count": form.get("count", 0),
                            "confidence": "tinggi",
                            "examples": [ex] if ex else [],
                            "root_gloss": base_gloss,
                        }

    afiks_path = LING_DATA_DIR / "inventaris_afiks_lengkap.json"
    afiks_raw: Dict[str, Any] = {}
    if afiks_path.exists():
        with open(afiks_path, "r", encoding="utf-8") as f:
            afiks_raw = json.load(f)

    fonem_path = LING_DATA_DIR / "perubahan_bunyi_dan_morfofonemik.json"
    fonem_raw: Dict[str, Any] = {}
    if fonem_path.exists():
        with open(fonem_path, "r", encoding="utf-8") as f:
            fonem_raw = json.load(f)

    # Kumpulkan daftar hitam (deleted / proper name)
    excluded_lemmas: Set[str] = set()
    for k, v in overrides_raw.items():
        if v.get("review") in ("delete", "name"):
            excluded_lemmas.add(k)
    for k, v in batch2_audited.items():
        if v.get("status_audit") in ("HAPUS", "NAMA"):
            excluded_lemmas.add(k)

    # Gabungkan semua kandidat kunci lema
    all_keys: Set[str] = set()
    all_keys.update(master_raw.keys())
    all_keys.update(overrides_raw.keys())
    all_keys.update(mini_raw.keys())
    all_keys.update(batch2_audited.keys())
    all_keys.update(batch2_candidates.keys())
    all_keys.update(kutipan_ver.keys())
    all_keys.update(kutipan_tam.keys())
    all_keys.update(keluarga_lemmas.keys())

    merged: Dict[str, Dict[str, Any]] = {}

    for lema in sorted(all_keys):
        if not lema or lema in excluded_lemmas:
            continue

        # Jika ada di daftar nama diri dan TIDAK diverifikasi eksplisit di overrides/mini/batch2, lewati
        is_explicitly_verified = (
            lema in overrides_raw
            or lema in mini_raw
            or lema in batch2_audited
            or lema in kutipan_ver
            or lema in kutipan_tam
            or lema in keluarga_lemmas
        )
        if not is_explicitly_verified and lema.lower() in proper_names:
            continue

        base = master_raw.get(lema, {})
        ov = overrides_raw.get(lema, {})
        mn = mini_raw.get(lema, {})
        b2a = batch2_audited.get(lema, {})
        b2c = batch2_candidates.get(lema, {})
        kv = kutipan_ver.get(lema, {})
        kt = kutipan_tam.get(lema, {})
        kl = keluarga_lemmas.get(lema, {})

        # Tentukan meaning, pos, stem berdasarkan hierarki prioritas:
        # batch2_audited > manual_overrides > kamus_mini_1000 > kutipan_ver/tam/keluarga > master > batch2_candidates
        meaning = (
            b2a.get("meaning")
            or ov.get("meaning")
            or mn.get("meaning")
            or kv.get("meaning")
            or kt.get("meaning")
            or kl.get("meaning")
            or base.get("meaning")
            or b2c.get("meaning")
            or ""
        ).strip()

        if not meaning:
            continue

        pos = (
            b2a.get("pos")
            or ov.get("pos")
            or mn.get("pos")
            or kv.get("pos")
            or kt.get("pos")
            or kl.get("pos")
            or base.get("pos")
            or b2c.get("pos")
            or ""
        ).strip()

        stem = (
            b2a.get("stem")
            or ov.get("stem")
            or mn.get("stem")
            or kl.get("stem")
            or base.get("stem")
            or b2c.get("stem")
            or lema
        ).strip()

        freq_count = max(
            int(base.get("count") or 0),
            int(mn.get("count") or 0),
            int(b2a.get("count") or 0),
            int(b2c.get("count") or 0),
            int(kv.get("count") or 0),
            int(kt.get("count") or 0),
            int(kl.get("count") or 0),
        )

        # Kumpulkan contoh kalimat
        examples = (
            b2a.get("examples")
            or mn.get("examples")
            or kv.get("examples")
            or ([kt["ex"]] if kt.get("ex") else None)
            or kl.get("examples")
            or base.get("examples")
            or b2c.get("examples")
            or []
        )

        # Tentukan tier & confidence
        if is_explicitly_verified:
            tier = 1
            confidence = "terverifikasi"
            if lema in b2a:
                source_label = "audit_batch2"
            elif lema in mn:
                source_label = "kamus_mini_1000"
            elif lema in ov:
                source_label = "manual_override"
            elif lema in kl:
                source_label = "keluarga_kata_terverifikasi"
            else:
                source_label = "kutipan_linguistik"
        elif lema in b2c:
            tier = 2
            confidence = "tinggi"
            source_label = "kandidat_batch2"
        else:
            conf_raw = base.get("confidence", "rendah")
            source_label = base.get("source", "korpus")
            if conf_raw == "tinggi":
                tier = 2
                confidence = "tinggi"
            elif conf_raw == "sedang":
                tier = 3
                confidence = "sedang"
            else:
                tier = 4
                confidence = "rendah"

        merged[lema] = {
            "lemma": lema,
            "lema_normalized": normalize_sangihe(lema).lower(),
            "pos": pos,
            "stem": stem,
            "stem_normalized": normalize_sangihe(stem).lower(),
            "meaning": meaning,
            "freq_count": freq_count,
            "confidence": confidence,
            "tier": tier,
            "source_label": source_label,
            "examples": examples,
            "alternatives": base.get("alternatives") or b2a.get("alternatives") or b2c.get("alternatives") or [],
        }

    ling_rules = {
        "affixes": afiks_raw,
        "morphophonemics": fonem_raw,
    }
    return merged, keluarga_raw, ling_rules


def build_sqlite_database():
    print("=" * 68)
    print("  MEMBANGUN DATABASE SQLITE KAMUS SANGIHE MODERN (Kamus/Sangihe)")
    print("=" * 68)

    merged, keluarga_raw, ling_rules = load_all_sources()

    OUTPUT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DB_PATH.exists():
        OUTPUT_DB_PATH.unlink()

    conn = sqlite3.connect(str(OUTPUT_DB_PATH))
    c = conn.cursor()

    # 1. Buat skema yang 100% kompatibel dengan sarindi.sqlite + kolom perluasan modern
    c.executescript(
        """
        PRAGMA journal_mode = WAL;
        PRAGMA synchronous = NORMAL;

        CREATE TABLE metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );

        CREATE TABLE lemmas (
            id INTEGER PRIMARY KEY,
            letter TEXT NOT NULL,
            lema_raw TEXT NOT NULL,
            lema_display TEXT NOT NULL,
            lema_normalized TEXT NOT NULL,
            homonym_index INTEGER NOT NULL DEFAULT 1,
            etymology TEXT,
            summary_gloss TEXT NOT NULL,
            body_plain TEXT NOT NULL,
            body_rich TEXT NOT NULL,
            sublemmas_json TEXT NOT NULL,
            cross_refs_json TEXT NOT NULL,
            verses_json TEXT NOT NULL,
            id_keywords_json TEXT NOT NULL,
            pos TEXT DEFAULT '',
            stem TEXT DEFAULT '',
            stem_normalized TEXT DEFAULT '',
            freq_count INTEGER DEFAULT 0,
            confidence TEXT DEFAULT '',
            tier INTEGER DEFAULT 3,
            source_label TEXT DEFAULT ''
        );

        CREATE TABLE sublemmas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lemma_id INTEGER NOT NULL,
            sublema TEXT NOT NULL,
            sublema_normalized TEXT NOT NULL,
            gloss TEXT NOT NULL,
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );

        CREATE TABLE id_index (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_keyword TEXT NOT NULL,
            id_keyword_normalized TEXT NOT NULL,
            lemma_id INTEGER NOT NULL,
            is_primary INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (lemma_id) REFERENCES lemmas(id)
        );

        CREATE TABLE word_families (
            root TEXT PRIMARY KEY,
            root_normalized TEXT NOT NULL,
            base_gloss TEXT NOT NULL,
            total_verified_forms INTEGER NOT NULL,
            forms_json TEXT NOT NULL
        );

        CREATE TABLE morphology_rules (
            rule_key TEXT PRIMARY KEY,
            category TEXT NOT NULL,
            payload_json TEXT NOT NULL
        );

        CREATE VIRTUAL TABLE lemmas_fts USING fts5(
            lema_display,
            lema_normalized,
            sublemmas_text,
            id_keywords_text,
            summary_gloss,
            content=''
        );
        """
    )

    # Kelompokkan turunan berdasarkan stem agar setiap kata dasar juga memiliki daftar sublema keluarga katanya
    stem_derivatives: Dict[str, List[Dict[str, str]]] = defaultdict(list)
    for lema, item in merged.items():
        st = item["stem"]
        if st and st != lema:
            stem_derivatives[st].append({
                "sublema": lema,
                "pos": item["pos"],
                "gloss": item["meaning"],
                "tier": item["tier"],
                "freq": item["freq_count"],
            })

    # Urutkan lema: Tier terbaik (1 -> 4), lalu frekuensi tertinggi, lalu abjad
    sorted_items = sorted(
        merged.values(),
        key=lambda x: (x["tier"], -x["freq_count"], x["lema_normalized"]),
    )

    tier_counts = defaultdict(int)
    pos_counts = defaultdict(int)
    sublemma_rows = []
    id_index_rows = []
    fts_rows = []

    for idx, item in enumerate(sorted_items, start=1):
        lema = item["lemma"]
        lema_norm = item["lema_normalized"]
        letter = lema_norm[0].upper() if lema_norm else "?"
        pos = item["pos"]
        stem = item["stem"]
        stem_norm = item["stem_normalized"]
        meaning = item["meaning"]
        freq = item["freq_count"]
        conf = item["confidence"]
        tier = item["tier"]
        source_label = item["source_label"]
        examples = item["examples"]

        tier_counts[tier] += 1
        pos_counts[pos or "tanpa_pos"] += 1

        # Susun ringkasan gloss & body_plain yang informatif untuk RAG prompt
        pos_tag = f"[{pos}] " if pos else ""
        stem_tag = f" (akar: {stem})" if (stem and stem != lema) else ""
        summary_gloss = f"{pos_tag}{meaning}{stem_tag}"

        body_parts = [summary_gloss]
        if examples and isinstance(examples, list):
            ex0 = examples[0]
            if isinstance(ex0, dict) and ex0.get("sangihe") and ex0.get("indonesia"):
                ref = f" [{ex0['ref']}]" if ex0.get("ref") else ""
                body_parts.append(f"Contoh: \"{ex0['sangihe']}\" = \"{ex0['indonesia']}\"{ref}")

        body_plain = " | ".join(body_parts)

        # Sublemmas untuk lema ini (jika lema ini merupakan kata dasar yang punya turunan)
        derivs = sorted(
            stem_derivatives.get(lema, []),
            key=lambda d: (d["tier"], -d["freq"]),
        )[:25]
        sublemmas_json = json.dumps(derivs, ensure_ascii=False)
        verses_json = json.dumps(examples[:3] if isinstance(examples, list) else [], ensure_ascii=False)

        # Ekstrak kata kunci Indonesia
        kw_pairs = extract_id_keywords(meaning)
        id_keywords_list = [kw for kw, _ in kw_pairs]
        id_keywords_json = json.dumps(id_keywords_list, ensure_ascii=False)

        c.execute(
            """
            INSERT INTO lemmas (
                id, letter, lema_raw, lema_display, lema_normalized,
                homonym_index, etymology, summary_gloss, body_plain, body_rich,
                sublemmas_json, cross_refs_json, verses_json, id_keywords_json,
                pos, stem, stem_normalized, freq_count, confidence, tier, source_label
            ) VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, '[]', ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                idx,
                letter,
                lema,
                lema,
                lema_norm,
                stem if stem != lema else "",
                summary_gloss,
                body_plain,
                body_plain,
                sublemmas_json,
                verses_json,
                id_keywords_json,
                pos,
                stem,
                stem_norm,
                freq,
                conf,
                tier,
                source_label,
            ),
        )

        # Tambahkan ke tabel sublemmas agar pencarian stemmer juga mengenai turunan
        for d in derivs:
            sub_str = d["sublema"]
            sub_norm = normalize_sangihe(sub_str).lower()
            sublemma_rows.append((idx, sub_str, sub_norm, d["gloss"]))

        # Tambahkan juga relasi stem dirinya sendiri sebagai sublema jika berbeda dari lema
        if stem and stem != lema:
            sublemma_rows.append((idx, stem, stem_norm, f"kata dasar dari {lema} ({meaning})"))

        # Tambahkan ke id_index
        # Skor is_primary lebih tinggi untuk Tier 1 & 2 agar tampil paling atas saat cari ID -> Sangihe
        for kw, is_prim in kw_pairs:
            kw_norm = normalize_sangihe(kw).lower()
            if tier == 1:
                prim_score = 3 if is_prim else 2
            elif tier == 2:
                prim_score = 2 if is_prim else 1
            elif tier == 3:
                prim_score = 1 if is_prim else 0
            else:
                prim_score = 0
            id_index_rows.append((kw, kw_norm, idx, prim_score))

        sublemmas_text = " ".join(d["sublema"] for d in derivs)
        id_keywords_text = " ".join(id_keywords_list)
        fts_rows.append((idx, lema, lema_norm, sublemmas_text, id_keywords_text, summary_gloss))

    c.executemany(
        "INSERT INTO sublemmas (lemma_id, sublema, sublema_normalized, gloss) VALUES (?, ?, ?, ?)",
        sublemma_rows,
    )
    c.executemany(
        "INSERT INTO id_index (id_keyword, id_keyword_normalized, lemma_id, is_primary) VALUES (?, ?, ?, ?)",
        id_index_rows,
    )
    c.executemany(
        "INSERT INTO lemmas_fts (rowid, lema_display, lema_normalized, sublemmas_text, id_keywords_text, summary_gloss) VALUES (?, ?, ?, ?, ?, ?)",
        fts_rows,
    )

    # Simpan keluarga kata terverifikasi
    for root_key, fam in keluarga_raw.items():
        c.execute(
            "INSERT INTO word_families (root, root_normalized, base_gloss, total_verified_forms, forms_json) VALUES (?, ?, ?, ?, ?)",
            (
                root_key,
                normalize_sangihe(root_key).lower(),
                fam.get("base_gloss", ""),
                fam.get("total_verified_forms", len(fam.get("forms", []))),
                json.dumps(fam.get("forms", []), ensure_ascii=False),
            ),
        )

    # Simpan aturan morfologi & morfofonemik
    for cat_key, payload in ling_rules.get("affixes", {}).items():
        c.execute(
            "INSERT INTO morphology_rules (rule_key, category, payload_json) VALUES (?, ?, ?)",
            (f"affix_{cat_key}", "affixes", json.dumps(payload, ensure_ascii=False)),
        )
    for rule_key, payload in ling_rules.get("morphophonemics", {}).items():
        c.execute(
            "INSERT INTO morphology_rules (rule_key, category, payload_json) VALUES (?, ?, ?)",
            (rule_key, "morphophonemics", json.dumps(payload, ensure_ascii=False)),
        )

    # Buat indeks kecepatan tinggi
    c.executescript(
        """
        CREATE INDEX idx_lemmas_norm ON lemmas(lema_normalized, tier, freq_count DESC);
        CREATE INDEX idx_lemmas_stem_norm ON lemmas(stem_normalized, tier, freq_count DESC);
        CREATE INDEX idx_lemmas_letter ON lemmas(letter, id);
        CREATE INDEX idx_sublemmas_norm ON sublemmas(sublema_normalized);
        CREATE INDEX idx_sublemmas_lemma_id ON sublemmas(lemma_id);
        CREATE INDEX idx_id_index_norm ON id_index(id_keyword_normalized, is_primary DESC);
        CREATE INDEX idx_id_index_lemma_id ON id_index(lemma_id);
        """
    )

    metadata_entries = [
        ("title", "Kamus Sangihe-Indonesia Modern (Berbasis Korpus & Kurasi)"),
        ("source_project", "/home/dpng/Projects/Kamus/Sangihe"),
        ("created_at", datetime.now().isoformat()),
        ("total_lemmas", str(len(sorted_items))),
        ("tier1_verified_count", str(tier_counts[1])),
        ("tier2_high_conf_count", str(tier_counts[2])),
        ("tier3_med_conf_count", str(tier_counts[3])),
        ("tier4_low_conf_count", str(tier_counts[4])),
    ]
    c.executemany("INSERT INTO metadata (key, value) VALUES (?, ?)", metadata_entries)

    conn.commit()
    conn.close()

    size_mb = OUTPUT_DB_PATH.stat().st_size / (1024 * 1024)
    print(f"Database berhasil dibuat : {OUTPUT_DB_PATH} ({size_mb:.2f} MB)")
    print("-" * 68)
    print(f"Total Lema Aktif         : {len(sorted_items):,}")
    print(f"  - Tier 1 (Terverifikasi Manual/Audit/Linguistik) : {tier_counts[1]:,}")
    print(f"  - Tier 2 (Keyakinan Tinggi & Kandidat Baru)      : {tier_counts[2]:,}")
    print(f"  - Tier 3 (Keyakinan Sedang Korpus BIMK/TB)       : {tier_counts[3]:,}")
    print(f"  - Tier 4 (Keyakinan Rendah / Kandidat Tambahan)  : {tier_counts[4]:,}")
    print(f"Total Relasi Sublema     : {len(sublemma_rows):,}")
    print(f"Total Indeks Indonesia   : {len(id_index_rows):,}")
    print(f"Total Keluarga Kata Inti : {len(keluarga_raw):,}")
    print("=" * 68)


if __name__ == "__main__":
    build_sqlite_database()

