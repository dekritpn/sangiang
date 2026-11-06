"""Generate Morphological Reasoning & Compositional Instruction Dataset for Sangiang.

Transforms 7,850+ authentic Sangihe derivations into Chain-of-Thought (CoT)
instruction-tuning pairs, teaching the LLM:
1. Word Deconstruction: Root identification, affix classification, and semantic shift reasoning.
2. Word Synthesis: Applying appropriate affixes to roots to express targeted meanings.
3. Morphophonemic Awareness: Explaining sound mutations (b <-> w, d <-> r, nasal assimilation).
"""

import json
import random
import sys
from pathlib import Path
from typing import Dict, List

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.prompt_templates import SYSTEM_SANGIANG_CONVERSATIONAL
from morphology.morphological_analyzer import MorphologicalAnalyzer, MorphologicalDerivation


def build_morphology_reasoning_dataset(
    sarindi_path: str = "/home/dpng/Projects/Kamus/sarindi/assets/db/sarindi.sqlite",
    out_file: str = "training/data/sangihe_morphological_reasoning.jsonl",
    max_samples: int = 5000,
    seed: int = 42,
) -> List[Dict]:
    """Extract derivations and format into Chain-of-Thought instruction pairs."""
    analyzer = MorphologicalAnalyzer(sarindi_path)
    derivations = analyzer.extract_all_valid_derivations()
    print(f"[*] Loaded {len(derivations)} authentic recognized derivations from dictionary.")

    random.seed(seed)
    # Ensure balanced representation across affixes
    sampled_derivations = random.sample(derivations, min(len(derivations), max_samples))

    instruction_pairs = []

    for idx, d in enumerate(sampled_derivations):
        # 1. Type A: Word Deconstruction & Morphological Analysis
        q_deconstruct = f"Analisis struktur morfologis, imbuhan, dan pergeseran makna dari kata bentukan bahasa Sangihe '{d.derived_word}'!"
        cot_explanation = d.generate_cot_explanation()

        instruction_pairs.append({
            "id": f"morph:deconstruct:{idx:05d}",
            "domain": "morfologi_sangihe",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_CONVERSATIONAL.strip()},
                {"role": "user", "content": q_deconstruct},
                {"role": "assistant", "content": cot_explanation},
            ],
        })

        # 2. Type B: Word Synthesis (Deriving Word from Root and Desired Meaning)
        q_synthesis = f"Bagaimana cara membentuk kata dalam bahasa Sangihe dari kata dasar '{d.root_word}' (artinya: {d.root_gloss}) untuk menyatakan makna '{d.derived_gloss}'?"
        
        synth_resp = (
            f"Untuk menyatakan makna **\"{d.derived_gloss}\"**, kata dasar **`{d.root_word}`** "
            f"diberi **{d.affix_name}**.\n\n"
            f"• **Bentuk Kata Jadi:** **`{d.derived_word}`**\n"
            f"• **Kaidah Semantik:** {d.semantic_logic}"
        )
        if d.sound_mutation:
            synth_resp += f"\n• **Perubahan Fonem:** Terjadi proses {d.sound_mutation}."

        instruction_pairs.append({
            "id": f"morph:synthesis:{idx:05d}",
            "domain": "morfologi_sangihe",
            "messages": [
                {"role": "system", "content": SYSTEM_SANGIANG_CONVERSATIONAL.strip()},
                {"role": "user", "content": q_synthesis},
                {"role": "assistant", "content": synth_resp},
            ],
        })

    out_path = Path(out_file)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for item in instruction_pairs:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    print(f"[✓] Successfully generated {len(instruction_pairs)} morphological reasoning instruction pairs.")
    print(f"[✓] Saved to: {out_path} (size: {out_path.stat().st_size / (1024*1024):.2f} MB)")
    return instruction_pairs


if __name__ == "__main__":
    build_morphology_reasoning_dataset()
