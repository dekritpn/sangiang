#!/usr/bin/env python3
"""Sync project statistics directly into LaTeX macros.

Reads real-time database counts, corpus sizes, and benchmark stats
from the main translation engine project and writes them to stats_autogen.tex.
"""

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path


def sync_project_stats():
    base_dir = Path(__file__).resolve().parent.parent
    book_dir = Path(__file__).resolve().parent

    # 1. Corpus stats
    parallel_db = base_dir / "data" / "parallel_corpus.sqlite"
    corpus_total = 0
    domain_counts = {}
    if parallel_db.exists():
        with sqlite3.connect(parallel_db) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM parallel_sentences;")
            corpus_total = c.fetchone()[0]

            c.execute("SELECT source_domain, COUNT(*) FROM parallel_sentences GROUP BY source_domain;")
            for dom, cnt in c.fetchall():
                domain_counts[dom] = cnt

    # 2. Sarindi dictionary stats
    sarindi_db = base_dir.parent / "Kamus" / "sarindi" / "assets" / "db" / "sarindi.sqlite"
    lemma_total = 0
    if sarindi_db.exists():
        with sqlite3.connect(sarindi_db) as conn:
            c = conn.cursor()
            c.execute("SELECT COUNT(*) FROM lemmas;")
            lemma_total = c.fetchone()[0]

    # 3. Training and validation data stats
    train_file = base_dir / "training" / "data" / "train.jsonl"
    val_file = base_dir / "training" / "data" / "val.jsonl"
    train_count = 0
    val_count = 0

    if train_file.exists():
        with open(train_file, "r", encoding="utf-8") as f:
            train_count = sum(1 for _ in f)

    if val_file.exists():
        with open(val_file, "r", encoding="utf-8") as f:
            val_count = sum(1 for _ in f)

    # 4. Benchmark stats
    bench_file = base_dir / "benchmark" / "testset.json"
    bench_count = 0
    if bench_file.exists():
        with open(bench_file, "r", encoding="utf-8") as f:
            bench_data = json.load(f)
            bench_count = len(bench_data)

    # 5. Generate LaTeX definitions
    out_file = book_dir / "stats_autogen.tex"
    now_str = datetime.now().strftime("%d %B %Y")

    content = f"""% Auto-generated statistics from main translation engine project.
% Do NOT edit manually; updated via sync_project_status.py
\\newcommand{{\\StatLastSyncDate}}{{{now_str}}}
\\newcommand{{\\StatCorpusTotal}}{{{corpus_total:,}}}
\\newcommand{{\\StatCorpusBible}}{{{domain_counts.get('bible', 0):,}}}
\\newcommand{{\\StatCorpusDongeng}}{{{domain_counts.get('dongeng', 0):,}}}
\\newcommand{{\\StatCorpusHimbawo}}{{{domain_counts.get('himbawo', 0):,}}}
\\newcommand{{\\StatCorpusTigaKulano}}{{{domain_counts.get('tiga_kulano', 0):,}}}
\\newcommand{{\\StatCorpusPercakapan}}{{{domain_counts.get('percakapan', 0):,}}}
\\newcommand{{\\StatLemmaTotal}}{{{lemma_total:,}}}
\\newcommand{{\\StatTrainPairs}}{{{train_count:,}}}
\\newcommand{{\\StatValPairs}}{{{val_count:,}}}
\\newcommand{{\\StatBenchmarkSamples}}{{{bench_count:,}}}
\\newcommand{{\\StatBaseModel}}{{Qwen2.5-7B-Instruct}}
\\newcommand{{\\StatFinetunedModel}}{{sangiang:7b}}
\\newcommand{{\\StatModelCodename}}{{Sangiang}}
"""

    with open(out_file, "w", encoding="utf-8") as f:
        f.write(content)

    print(f"✅ Successfully synchronized project stats to {out_file}:")
    print(f"   - Korpus Paralel: {corpus_total:,} kalimat")
    print(f"   - Lema Kamus: {lemma_total:,} entri")
    print(f"   - Data Latih Instruction Tuning: {train_count:,} pasang")
    print(f"   - Data Validasi: {val_count:,} pasang")
    print(f"   - Sampel Uji Benchmark: {bench_count:,} kalimat")


if __name__ == "__main__":
    sync_project_stats()
