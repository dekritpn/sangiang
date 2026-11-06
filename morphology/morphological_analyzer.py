"""Morphological Decomposition and Derivation Analyzer for Bahasa Sangihe.

Pairs root lemmas with derived sublemmas, identifies affixes/sound mutations,
and generates structured Chain-of-Thought (CoT) linguistic explanations.
"""

import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from morphology.affix_semantics import AFFIX_SEMANTIC_RULES, explain_affix_logic
from morphology.normalizer import normalize_sangihe


@dataclass
class MorphologicalDerivation:
    root_word: str
    root_normalized: str
    root_gloss: str
    derived_word: str
    derived_normalized: str
    derived_gloss: str
    affix_key: str
    affix_name: str
    sound_mutation: Optional[str] = None
    semantic_logic: str = ""

    def generate_cot_explanation(self) -> str:
        """Generate structured Chain-of-Thought linguistic explanation."""
        steps = [
            f"1. **Bentuk Dasar (Root):** `{self.root_word}` (normalisasi: *{self.root_normalized}*), yang memiliki makna dasar: *{self.root_gloss}*.",
            f"2. **Pola Imbuhan / Sisipan:** Menggunakan **{self.affix_name}**.",
        ]
        if self.sound_mutation:
            steps.append(f"3. **Perubahan Bunyi (Morfonofonemik):** Terjadi pergeseran fonem `{self.sound_mutation}` pada proses penggabungan morfem.")
        
        rule = explain_affix_logic(self.affix_key)
        rule_desc = rule["semantic_effect"] if rule else "Mengubah kelas kata atau orientasi fokus tindakan."
        steps.append(f"4. **Fungsi Semantik:** {rule_desc}")
        steps.append(f"5. **Hasil Bentukan & Makna Akhir:** Kata bentukan `{self.derived_word}` bermakna: **\"{self.derived_gloss}\"**.")

        return "\n".join(steps)


class MorphologicalAnalyzer:
    """Automated engine for deconstructing and explaining Sangihe derivations."""

    def __init__(self, sarindi_db_path: str = "/home/dpng/Projects/Kamus/sarindi/assets/db/sarindi.sqlite"):
        self.db_path = Path(sarindi_db_path)

    def detect_affix_pattern(self, root: str, derived: str) -> Tuple[str, str, Optional[str]]:
        """Identify the morphological affix and any morphophonemic sound changes."""
        r_norm = normalize_sangihe(root).lower().strip()
        d_norm = normalize_sangihe(derived).lower().strip()

        mutation = None

        # 1. Infix check (-um-, -in-, -im-)
        # Pattern: c1 + inf + rest vs c1 + rest
        if len(r_norm) >= 3 and len(d_norm) >= 5:
            if r_norm[0] == d_norm[0]:
                if d_norm[1:3] == "um" and d_norm[3:] == r_norm[1:]:
                    return "-um-", "Sisipan Aktif / Pelaku (-um-)", None
                if d_norm[1:3] == "in" and d_norm[3:] == r_norm[1:]:
                    return "-in-", "Sisipan Realis / Lampau (-in-)", None
                if d_norm[1:3] == "im" and d_norm[3:] == r_norm[1:]:
                    return "-in-", "Sisipan Realis Asimilatif (-im-)", "asimilasi labial in -> im"

        # 2. Sound shift b -> w check
        r_mut = r_norm
        if r_norm.startswith("b"):
            r_mut = "w" + r_norm[1:]
            if "w" in d_norm and not d_norm.startswith("b"):
                mutation = "b -> w (pelunakan konsonan bibir)"

        # 3. Sound shift d -> r check
        if r_norm.startswith("d"):
            r_mut_r = "r" + r_norm[1:]
            if "r" in d_norm and not d_norm.startswith("d"):
                mutation = "d -> r (pelunakan konsonan alveolar)"
                r_mut = r_mut_r

        # 4. Circumfix check
        if d_norm.startswith("ka") and (d_norm.endswith("ang") or d_norm.endswith("eng")):
            return "ka-...-ang", "Konfiks Lokatif / Wadah / Abstrak (ka-...-ang)", mutation
        if (d_norm.startswith("pe") or d_norm.startswith("pě")) and (d_norm.endswith("ang") or d_norm.endswith("eng")):
            return "pe-...-ang", "Konfiks Lokatif Aktivitas (pe-...-ang)", mutation

        # 5. Compound & Basic Prefix check (sorted longest first)
        known_prefixes = [
            ("makapa", "Awalan Kausatif Potensial (makapa-)"),
            ("makipe", "Awalan Permohonan Bersama (makipe-)"),
            ("mangang", "Awalan Verba Aktif Jamak (mangang-)"),
            ("manga", "Awalan Verba Aktif Transitif (manga-)"),
            ("maka", "Awalan Potensial Kesanggupan (maka-)"),
            ("naka", "Awalan Potensial Lampau (naka-)"),
            ("paka", "Awalan Kausatif Pengintensif (paka-)"),
            ("ipang", "Awalan Instrumen Alat (ipang-)"),
            ("maki", "Awalan Permohonan / Permintaan (maki-)"),
            ("mang", "Awalan Verba Aktif Nasal (mang-)"),
            ("pang", "Awalan Nomina Pelaku / Alat (pang-)"),
            ("ma", "Awalan Keadaan / Statif (ma-)"),
            ("mě", "Awalan Verba Aktif / Menjadi (mě-)"),
            ("me", "Awalan Verba Aktif (me-)"),
            ("na", "Awalan Keadaan Lampau (na-)"),
            ("pa", "Awalan Kausatif Imperatif (pa-)"),
            ("ka", "Awalan Nomina Abstrak / Derajat (ka-)"),
            ("i", "Awalan Fokus Sasaran (i-)"),
        ]

        for p_str, p_name in known_prefixes:
            p_norm = normalize_sangihe(p_str).lower()
            if d_norm.startswith(p_norm):
                stem_part = d_norm[len(p_norm):]
                if stem_part in (r_norm, r_mut) or r_norm.startswith(stem_part[:3]):
                    affix_key = p_str if p_str in AFFIX_SEMANTIC_RULES else (p_str + "-")
                    return affix_key, p_name, mutation

        # 6. Suffix check
        for s in ["ang", "eng"]:
            if d_norm.endswith(s):
                stem_part = d_norm[:-len(s)]
                if stem_part in (r_norm, r_mut) or r_norm.startswith(stem_part[:3]):
                    return "-" + s, f"Akhiran Fokus Sasaran (-{s})", mutation

        return "afiks_khusus", "Pola Derivasi Khusus", mutation

    def analyze_single_derivation(
        self,
        root_word: str,
        root_gloss: str,
        derived_word: str,
        derived_gloss: str,
    ) -> MorphologicalDerivation:
        """Deconstruct a single root -> derived pair."""
        r_norm = normalize_sangihe(root_word).strip()
        d_norm = normalize_sangihe(derived_word).strip()

        affix_key, affix_name, mutation = self.detect_affix_pattern(root_word, derived_word)
        rule = explain_affix_logic(affix_key)
        logic = rule["semantic_effect"] if rule else "Pergeseran fungsi kata dan nuansa makna."

        return MorphologicalDerivation(
            root_word=root_word.strip(),
            root_normalized=r_norm,
            root_gloss=root_gloss.strip().rstrip("."),
            derived_word=derived_word.strip(),
            derived_normalized=d_norm,
            derived_gloss=derived_gloss.strip().rstrip("."),
            affix_key=affix_key,
            affix_name=affix_name,
            sound_mutation=mutation,
            semantic_logic=logic,
        )

    def extract_all_valid_derivations(self, limit: Optional[int] = None) -> List[MorphologicalDerivation]:
        """Extract and analyze clean derivations from sarindi.sqlite."""
        if not self.db_path.exists():
            raise FileNotFoundError(f"Database not found at {self.db_path}")

        query = """
            SELECT 
                l.lema_display,
                l.summary_gloss AS root_gloss,
                s.sublema,
                s.gloss AS derived_gloss
            FROM sublemmas s
            JOIN lemmas l ON s.lemma_id = l.id
            WHERE LENGTH(s.sublema) >= 3
              AND LENGTH(s.gloss) >= 5
              AND s.gloss NOT LIKE '%bdk.%'
              AND s.gloss NOT LIKE '%Spr.%'
              AND s.gloss != '.'
            ORDER BY s.id ASC
        """
        if limit:
            query += f" LIMIT {limit};"
        else:
            query += ";"

        results = []
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(query)
            for row in cur.fetchall():
                r_word = row["lema_display"]
                r_gloss = row["root_gloss"]
                d_word = row["sublema"]
                d_gloss = row["derived_gloss"]

                # Skip if identical
                if normalize_sangihe(r_word).lower() == normalize_sangihe(d_word).lower():
                    continue

                deriv = self.analyze_single_derivation(r_word, r_gloss, d_word, d_gloss)
                # Keep if recognized affix pattern
                if deriv.affix_key != "afiks_khusus":
                    results.append(deriv)

        return results
