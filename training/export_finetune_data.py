"""Export Parallel Corpus into LoRA / Fine-Tuning Datasets (Alpaca & ShareGPT formats).

Prepares dataset for fine-tuning Qwen2.5:7b using Unsloth, TRL, or PEFT.
Generates bidirectional instruction-tuning pairs with diacritic adherence instructions.
"""

import json
import sqlite3
from pathlib import Path
from typing import Optional
from engine.prompt_templates import (
    SYSTEM_INDONESIAN_TO_SANGIHE,
    SYSTEM_SANGIHE_TO_INDONESIAN,
)


def export_finetune_dataset(
    db_path: str = "data/parallel_corpus.sqlite",
    out_dir: str = "training/data",
    format_type: str = "sharegpt",  # 'sharegpt' or 'alpaca'
    max_samples: Optional[int] = None,
    min_length: int = 15,
):
    """Export parallel corpus into instruction tuning pairs."""
    db = Path(db_path)
    if not db.exists():
        raise FileNotFoundError(f"Database {db_path} does not exist.")

    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    records = []
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("""
            SELECT reference_id, source_domain, sangihe_text, indonesian_tb
            FROM parallel_sentences
            WHERE LENGTH(sangihe_text) >= ? AND LENGTH(indonesian_tb) >= ?
        """, (min_length, min_length))
        records = c.fetchall()

    if max_samples:
        records = records[:max_samples]

    dataset = []

    for r in records:
        sangihe = r["sangihe_text"]
        indonesian = r["indonesian_tb"]

        # Pair 1: Sangihe -> Indonesian
        if format_type == "sharegpt":
            dataset.append({
                "id": f"{r['reference_id']}_sa2id",
                "messages": [
                    {"role": "system", "content": SYSTEM_SANGIHE_TO_INDONESIAN.strip()},
                    {"role": "user", "content": f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n{sangihe}"},
                    {"role": "assistant", "content": indonesian},
                ],
            })
            # Pair 2: Indonesian -> Sangihe (with diacritics)
            dataset.append({
                "id": f"{r['reference_id']}_id2sa",
                "messages": [
                    {"role": "system", "content": SYSTEM_INDONESIAN_TO_SANGIHE.strip()},
                    {"role": "user", "content": f"Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap:\n{indonesian}"},
                    {"role": "assistant", "content": sangihe},
                ],
            })
        else:  # Alpaca format
            dataset.append({
                "instruction": "Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal.",
                "input": sangihe,
                "output": indonesian,
            })
            dataset.append({
                "instruction": "Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap.",
                "input": indonesian,
                "output": sangihe,
            })

    output_file = out_path / f"sangihe_finetune_{format_type}.jsonl"
    with open(output_file, "w", encoding="utf-8") as f:
        for entry in dataset:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    print(f"Exported {len(dataset)} instruction pairs ({len(records)} parallel sentences) to {output_file}")
    return str(output_file)


if __name__ == "__main__":
    export_finetune_dataset(max_samples=5000)
