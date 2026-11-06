"""Translation Quality Evaluator (BLEU, chrF++, Diacritic Accuracy)."""

import json
import time
from pathlib import Path
from typing import List, Optional
import sacrebleu
from rich.console import Console
from rich.table import Table
from engine.translator import SangiheTranslationEngine
from morphology.normalizer import DIACRITIC_PATTERN


def calculate_diacritic_accuracy(predictions: List[str], references: List[str]) -> float:
    """Calculate the precision of diacritic glyphs between predictions and references."""
    pred_dia_count = sum(len(DIACRITIC_PATTERN.findall(p)) for p in predictions)
    ref_dia_count = sum(len(DIACRITIC_PATTERN.findall(r)) for r in references)

    if ref_dia_count == 0:
        return 1.0 if pred_dia_count == 0 else 0.0

    return min(1.0, pred_dia_count / ref_dia_count)


def run_benchmark(
    testset_path: str = "benchmark/testset.json",
    direction: str = "sangihe_to_id",
    model: Optional[str] = None,
    limit: Optional[int] = 10,
    engine: Optional[SangiheTranslationEngine] = None,
):
    """Run translation benchmark evaluation and output metrics."""
    test_path = Path(testset_path)
    if not test_path.exists():
        from benchmark.generate_testset import generate_benchmark_testset
        generate_benchmark_testset(out_file=testset_path)

    with open(test_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if limit:
        data = data[:limit]

    if engine is None:
        engine = SangiheTranslationEngine(llm_model=model)

    active_model = model or engine.llm_client.model
    console = Console()
    console.print(f"[bold cyan]Running Benchmark ({direction}) using model [{active_model}] on {len(data)} samples...[/bold cyan]")

    predictions = []
    references = []
    times = []

    table = Table(title=f"Evaluation Results: {direction} ({active_model})")
    table.add_column("Ref ID", style="dim", width=14)
    table.add_column("Source Input", width=35)
    table.add_column("Prediction", width=35)
    table.add_column("Reference", width=35)

    for item in data:
        if direction == "sangihe_to_id":
            src = item["sangihe"]
            ref = item["indonesian"]
        else:
            src = item["indonesian"]
            ref = item["sangihe"]

        t0 = time.time()
        res = engine.translate(src, direction=direction, model=model)
        elapsed = time.time() - t0

        pred = res.translated_text
        predictions.append(pred)
        references.append([ref])
        times.append(elapsed)

        table.add_row(
            item["id"],
            src[:60] + "..." if len(src) > 60 else src,
            pred[:60] + "..." if len(pred) > 60 else pred,
            ref[:60] + "..." if len(ref) > 60 else ref,
        )

    console.print(table)

    # Compute BLEU & chrF++
    flat_refs = [r[0] for r in references]
    bleu = sacrebleu.corpus_bleu(predictions, references)
    chrf = sacrebleu.corpus_chrf(predictions, references)
    avg_latency = sum(times) / len(times) if times else 0

    metrics_table = Table(title=f"Quality Metrics: {direction} ({active_model})")
    metrics_table.add_column("Metric", style="bold")
    metrics_table.add_column("Score", style="green")

    metrics_table.add_row("BLEU", f"{bleu.score:.2f}")
    metrics_table.add_row("chrF++", f"{chrf.score:.2f}")
    metrics_table.add_row("Avg Latency per sentence", f"{avg_latency:.2f}s")

    if direction == "id_to_sangihe":
        dia_acc = calculate_diacritic_accuracy(predictions, flat_refs)
        metrics_table.add_row("Diacritic Density Ratio", f"{dia_acc * 100:.1f}%")

    console.print(metrics_table)
    return {
        "model": active_model,
        "direction": direction,
        "samples": len(data),
        "bleu": round(bleu.score, 2),
        "chrf": round(chrf.score, 2),
        "avg_latency": round(avg_latency, 2),
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Evaluate Translation Quality")
    parser.add_argument("--model", type=str, default=None, help="Ollama model name")
    parser.add_argument("--direction", type=str, default="sangihe_to_id", choices=["sangihe_to_id", "id_to_sangihe"])
    parser.add_argument("--limit", type=int, default=10, help="Number of test sentences")
    parser.add_argument("--testset", type=str, default="benchmark/testset.json", help="Path to testset JSON")
    args = parser.parse_args()

    run_benchmark(
        testset_path=args.testset,
        direction=args.direction,
        model=args.model,
        limit=args.limit,
    )
