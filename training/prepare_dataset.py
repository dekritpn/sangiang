"""Prepare Clean Train & Validation Splits with Strict Benchmark Exclusion.

Builds bidirectional instruction tuning datasets (ShareGPT / ChatML format)
strictly excluding test benchmark samples to prevent data leakage.
"""

import json
import random
import sqlite3
import sys
import zipfile
from pathlib import Path
from typing import Dict, List, Set

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.prompt_templates import (
    SYSTEM_INDONESIAN_TO_SANGIHE,
    SYSTEM_SANGIHE_TO_INDONESIAN,
)


def prepare_splits(
    db_path: str = "data/parallel_corpus.sqlite",
    testset_path: str = "benchmark/testset.json",
    out_dir: str = "training/data",
    val_ratio: float = 0.05,
    seed: int = 42,
) -> Dict[str, int]:
    """Extract, filter, split and format parallel corpus for fine-tuning."""
    db = Path(db_path)
    if not db.exists():
        raise FileNotFoundError(f"Database not found at {db_path}")

    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # 1. Load testset IDs to strictly prevent data leakage
    test_ids: Set[str] = set()
    test_file = Path(testset_path)
    if test_file.exists():
        with open(test_file, "r", encoding="utf-8") as f:
            test_data = json.load(f)
            for item in test_data:
                test_ids.add(item["id"])
        print(f"Loaded {len(test_ids)} benchmark test IDs to exclude from training.")
    else:
        print("Warning: testset.json not found, proceeding without explicit exclusion.")

    # 2. Fetch parallel sentences from database
    records = []
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT reference_id, source_domain, sangihe_text, indonesian_tb
            FROM parallel_sentences
            WHERE (LENGTH(sangihe_text) >= 12 AND LENGTH(indonesian_tb) >= 12)
               OR source_domain = 'percakapan';
        """)
        for r in c.fetchall():
            ref_id = r["reference_id"]
            if ref_id in test_ids:
                continue
            sangihe = r["sangihe_text"].strip()
            indo = r["indonesian_tb"].strip()
            if sangihe and indo:
                records.append({
                    "id": ref_id,
                    "domain": r["source_domain"],
                    "sangihe": sangihe,
                    "indonesian": indo,
                })

    print(f"Total available training parallel pairs after test exclusion: {len(records)}")

    # 3. Deduplicate based on (sangihe, indonesian)
    seen: Set[str] = set()
    deduped_records = []
    for r in records:
        key = f"{r['sangihe']}|||{r['indonesian']}"
        if key not in seen:
            seen.add(key)
            deduped_records.append(r)

    # 4. Shuffle with fixed seed
    random.seed(seed)
    random.shuffle(deduped_records)

    # 5. Split train and validation
    val_size = max(100, int(len(deduped_records) * val_ratio))
    val_records = deduped_records[:val_size]
    train_records = deduped_records[val_size:]

    print(f"Split: {len(train_records)} sentences for Training, {len(val_records)} sentences for Validation.")

    def format_to_sharegpt(sentence_records: List[dict]) -> List[dict]:
        dataset = []
        for r in sentence_records:
            sa = r["sangihe"]
            id_txt = r["indonesian"]

            # Direction 1: Sangihe -> Indonesian
            dataset.append({
                "id": f"{r['id']}_sa2id",
                "domain": r["domain"],
                "messages": [
                    {"role": "system", "content": SYSTEM_SANGIHE_TO_INDONESIAN.strip()},
                    {
                        "role": "user",
                        "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n{sa}",
                    },
                    {"role": "assistant", "content": id_txt},
                ],
            })

            # Direction 2: Indonesian -> Sangihe (with strict diacritics)
            dataset.append({
                "id": f"{r['id']}_id2sa",
                "domain": r["domain"],
                "messages": [
                    {"role": "system", "content": SYSTEM_INDONESIAN_TO_SANGIHE.strip()},
                    {
                        "role": "user",
                        "content": f"Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap:\n{id_txt}",
                    },
                    {"role": "assistant", "content": sa},
                ],
            })
        return dataset

    train_data = format_to_sharegpt(train_records)
    val_data = format_to_sharegpt(val_records)

    train_file = out / "train.jsonl"
    val_file = out / "val.jsonl"

    with open(train_file, "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    with open(val_file, "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # 6. Bundle into a zip for easy Google Colab upload
    zip_path = out / "sangihe_finetune_colab_data.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        zipf.write(train_file, arcname="train.jsonl")
        zipf.write(val_file, arcname="val.jsonl")

    print(f"Saved {len(train_data)} training instruction pairs to {train_file}")
    print(f"Saved {len(val_data)} validation instruction pairs to {val_file}")
    print(f"Bundled archive created at {zip_path}")

    return {
        "train_pairs": len(train_data),
        "val_pairs": len(val_data),
        "train_file": str(train_file),
        "val_file": str(val_file),
        "zip_file": str(zip_path),
    }


if __name__ == "__main__":
    prepare_splits()
