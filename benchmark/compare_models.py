"""Compare Translation Performance between Base and Fine-Tuned Models.

Runs comparative evaluation on held-out benchmark testset:
- Computes BLEU and chrF++ for both models.
- Measures diacritic accuracy in ID -> Sangihe.
- Displays side-by-side translation differences.
"""

import argparse
import json
import time
from pathlib import Path
from typing import List, Optional
import sacrebleu
from rich.console import Console
from rich.table import Table

from benchmark.evaluate import calculate_diacritic_accuracy
from engine.translator import SangiheTranslationEngine


def compare_models(
    base_model: str = "qwen2.5:7b",
    finetuned_model: str = "qwen2.5-sangihe:7b",
    testset_path: str = "benchmark/testset.json",
    direction: str = "sangihe_to_id",
    limit: int = 10,
):
    """Run side-by-side benchmark comparison between base and fine-tuned models."""
    console = Console()
    test_path = Path(testset_path)
    if not test_path.exists():
        console.print(f"[bold red]Testset file {testset_path} not found![/bold red]")
        return

    with open(test_path, "r", encoding="utf-8") as f:
        data = json.load(f)[:limit]

    console.print(
        f"\n[bold magenta]=== Comparing Models on {len(data)} Samples ({direction}) ===[/bold magenta]"
    )
    console.print(f"Base Model:       [cyan]{base_model}[/cyan]")
    console.print(f"Fine-Tuned Model: [green]{finetuned_model}[/green]\n")

    engine = SangiheTranslationEngine()

    base_preds = []
    ft_preds = []
    references = []
    base_latencies = []
    ft_latencies = []

    samples_table = Table(title="Side-by-Side Sentence Translations")
    samples_table.add_column("Ref ID", style="dim", width=12)
    samples_table.add_column("Input Source", width=30)
    samples_table.add_column(f"Base ({base_model})", style="yellow", width=30)
    samples_table.add_column(f"Fine-Tuned ({finetuned_model})", style="green", width=30)
    samples_table.add_column("Reference (Ground Truth)", style="dim", width=30)

    for i, item in enumerate(data, 1):
        if direction == "sangihe_to_id":
            src = item["sangihe"]
            ref = item["indonesian"]
        else:
            src = item["indonesian"]
            ref = item["sangihe"]

        references.append([ref])

        # Base model prediction
        t0 = time.time()
        res_base = engine.translate(src, direction=direction, model=base_model)
        base_latencies.append(time.time() - t0)
        base_preds.append(res_base.translated_text)

        # Fine-tuned model prediction
        t1 = time.time()
        res_ft = engine.translate(src, direction=direction, model=finetuned_model)
        ft_latencies.append(time.time() - t1)
        ft_preds.append(res_ft.translated_text)

        samples_table.add_row(
            item["id"],
            src[:55] + "..." if len(src) > 55 else src,
            res_base.translated_text[:55] + "..." if len(res_base.translated_text) > 55 else res_base.translated_text,
            res_ft.translated_text[:55] + "..." if len(res_ft.translated_text) > 55 else res_ft.translated_text,
            ref[:55] + "..." if len(ref) > 55 else ref,
        )

    console.print(samples_table)

    # Compute metrics
    flat_refs = [r[0] for r in references]

    base_bleu = sacrebleu.corpus_bleu(base_preds, references).score
    ft_bleu = sacrebleu.corpus_bleu(ft_preds, references).score

    base_chrf = sacrebleu.corpus_chrf(base_preds, references).score
    ft_chrf = sacrebleu.corpus_chrf(ft_preds, references).score

    avg_base_lat = sum(base_latencies) / len(base_latencies) if base_latencies else 0
    avg_ft_lat = sum(ft_latencies) / len(ft_latencies) if ft_latencies else 0

    comp_table = Table(title=f"Benchmark Summary Comparison ({direction})")
    comp_table.add_column("Metric", style="bold")
    comp_table.add_column(f"Base Model ({base_model})", style="yellow")
    comp_table.add_column(f"Fine-Tuned ({finetuned_model})", style="green")
    comp_table.add_column("Delta / Improvement", style="bold cyan")

    bleu_diff = ft_bleu - base_bleu
    chrf_diff = ft_chrf - base_chrf

    comp_table.add_row(
        "BLEU Score",
        f"{base_bleu:.2f}",
        f"{ft_bleu:.2f}",
        f"{'+' if bleu_diff >= 0 else ''}{bleu_diff:.2f}",
    )
    comp_table.add_row(
        "chrF++ Score",
        f"{base_chrf:.2f}",
        f"{ft_chrf:.2f}",
        f"{'+' if chrf_diff >= 0 else ''}{chrf_diff:.2f}",
    )
    comp_table.add_row(
        "Avg Latency",
        f"{avg_base_lat:.2f}s",
        f"{avg_ft_lat:.2f}s",
        f"{avg_ft_lat - avg_base_lat:+.2f}s",
    )

    if direction == "id_to_sangihe":
        base_dia = calculate_diacritic_accuracy(base_preds, flat_refs) * 100
        ft_dia = calculate_diacritic_accuracy(ft_preds, flat_refs) * 100
        comp_table.add_row(
            "Diacritic Density Ratio",
            f"{base_dia:.1f}%",
            f"{ft_dia:.1f}%",
            f"{ft_dia - base_dia:+.1f}%",
        )

    console.print(comp_table)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Compare Base vs Fine-Tuned Models")
    parser.add_argument("--base", type=str, default="qwen2.5:7b", help="Base model tag in Ollama")
    parser.add_argument("--finetuned", type=str, default="qwen2.5-sangihe:7b", help="Fine-tuned model tag in Ollama")
    parser.add_argument("--direction", type=str, default="sangihe_to_id", choices=["sangihe_to_id", "id_to_sangihe"])
    parser.add_argument("--limit", type=int, default=10, help="Number of benchmark sentences")
    args = parser.parse_args()

    compare_models(
        base_model=args.base,
        finetuned_model=args.finetuned,
        direction=args.direction,
        limit=args.limit,
    )
