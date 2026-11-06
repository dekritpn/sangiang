"""Rule-based Sangihe Morphological Analyzer and Stemmer.

Analyzes Sangihe affixation patterns (prefixes, infixes, suffixes, enclitics, reduplication)
and generates candidate root/stem forms to lookup in the Steller-Aebersold dictionary.
Can be tuned and extended with additional rules.
"""

import re
from dataclasses import dataclass, field
from typing import List, Set
from morphology.normalizer import normalize_sangihe


@dataclass
class MorphologicalAnalysis:
    surface: str
    normalized: str
    is_reduplicated: bool = False
    prefixes: List[str] = field(default_factory=list)
    infixes: List[str] = field(default_factory=list)
    suffixes: List[str] = field(default_factory=list)
    candidate_stems: List[str] = field(default_factory=list)


# Sangihe prefixes in normalized form (sorted by length descending to match longest first)
PREFIXES = [
    # Compound prefixes
    "pangang", "mangang", "nangang",
    "makipang", "nakipang", "pekipang",
    "manga", "nanga", "panga",
    "makiki", "nakiki", "pekiki",
    "makapa", "nakapa", "pakapa",
    "makipi", "nakipi", "pekipi",
    "makape", "nakape", "pakape",
    "maki", "naki", "peki", "piki",
    "maka", "naka", "paka", "poko",
    "mako", "nako", "peko",
    "mang", "nang", "pang",
    "many", "nany", "pany",
    "mam", "nam", "pam",
    "man", "nan", "pan",
    "neng", "meng", "peng",
    "toko", "taka", "toka",
    "medu", "nedu", "pedu",
    # Basic prefixes
    "me", "ne", "pe",
    "ma", "na", "pa",
    "mi", "ni", "pi",
    "mo", "no", "po",
    "mu", "nu", "pu",
    "ka", "ki", "ko", "ku",
    "ta", "te", "to",
    "sa", "se", "so",
    "i",
]

# Common enclitics and suffixes
ENCLITICS_AND_SUFFIXES = [
    # Complex enclitics
    "kewewe", "tewewe", "pewewe",
    "sarang", "kewe", "tewe", "pewe", "tade",
    # Possessive & definite enclitics
    "angku", "engku", "engne", "angne",
    "kue", "neu", "kue",
    # Basic suffixes
    "ang", "eng", "ing", "ong",
    # Enclitics
    "ku", "mu", "ne", "we", "ko",
    "e", "u",
]

# Infixes
INFIXES = ["um", "in", "im"]


class SangiheStemmer:
    """Configurable rule-based stemmer for Bahasa Sangihe."""

    def __init__(self):
        self.prefixes = sorted(PREFIXES, key=len, reverse=True)
        self.suffixes = sorted(ENCLITICS_AND_SUFFIXES, key=len, reverse=True)
        self.infixes = INFIXES

    def analyze(self, word: str) -> MorphologicalAnalysis:
        """Analyze a single word token and return candidate stems and affix breakdowns."""
        norm = normalize_sangihe(word).lower()
        analysis = MorphologicalAnalysis(surface=word, normalized=norm)

        # Base candidate is always the word itself
        candidates: List[str] = [norm]

        # 1. Check for hyphenated forms (reduplication e.g. kata-kata or clitics e.g. waes-u, areng-u)
        if "-" in norm:
            parts = norm.split("-")
            if len(parts) == 2:
                if parts[0] == parts[1]:
                    analysis.is_reduplicated = True
                candidates.append(parts[0])
                current = parts[0]
            else:
                current = norm
        else:
            current = norm

        # 2. Check and strip enclitics/suffixes
        matched_suffixes = []
        for suf in self.suffixes:
            if len(current) >= len(suf) + 2 and current.endswith(suf):
                base = current[:-len(suf)]
                matched_suffixes.append(suf)
                candidates.append(base)
                # If root originally ended in paragogic -ẹ̌ / -ě (normalized 'e'), stripping -e / -u / -ang / -eng leaves a consonant-final stem; restore '+e' candidate
                if base and base[-1] not in "aiueo":
                    candidates.append(base + "e")
                current = base
                break

        # Check for secondary suffix (e.g., -ang + -e)
        for suf in self.suffixes:
            if len(current) >= len(suf) + 2 and current.endswith(suf):
                base = current[:-len(suf)]
                matched_suffixes.append(suf)
                candidates.append(base)
                current = base
                break

        analysis.suffixes = matched_suffixes

        # 3. Check and strip prefixes on the current base and the original norm
        stems_to_try = [current, norm]
        for stem in stems_to_try:
            for pref in self.prefixes:
                if len(stem) > len(pref) + 2 and stem.startswith(pref):
                    stripped = stem[len(pref):]
                    analysis.prefixes.append(pref)
                    candidates.append(stripped)

                    # Morphophonemic restoration (nasal assimilation):
                    # mang + stem:
                    # - if stripped begins with vowel, stem might originally start with k, g, or vowel
                    if pref in ("mang", "nang", "pang"):
                        candidates.append("k" + stripped)
                        candidates.append("g" + stripped)
                    elif pref in ("mam", "nam", "pam"):
                        candidates.append("b" + stripped)
                        candidates.append("p" + stripped)
                        candidates.append("w" + stripped)
                    elif pref in ("man", "nan", "pan"):
                        candidates.append("t" + stripped)
                        candidates.append("d" + stripped)
                        candidates.append("s" + stripped)
                    elif pref in ("many", "nany", "pany"):
                        candidates.append("s" + stripped)
                        candidates.append("t" + stripped)

                    # Also try secondary prefix
                    for pref2 in ("pa", "pe", "ka", "ki"):
                        if len(stripped) > len(pref2) + 2 and stripped.startswith(pref2):
                            candidates.append(stripped[len(pref2):])

        # 4. Check for infixes (-um-, -in-)
        # Usually placed after first consonant: C + infix + V...
        # e.g. dumolong -> dolong, kumiang -> kiang, sinimbang -> simbang
        for c_word in list(candidates):
            if len(c_word) >= 5:
                for infix in self.infixes:
                    if c_word[1:1+len(infix)] == infix and c_word[0] not in "aeiou":
                        # C + infix + rest -> C + rest
                        unfixed = c_word[0] + c_word[1+len(infix):]
                        analysis.infixes.append(infix)
                        candidates.append(unfixed)

        # 5. Partial CV-reduplication (e.g. kakano -> kano, boboto -> boto, seseba -> seba)
        for c_word in list(candidates):
            if len(c_word) >= 4 and c_word[0] == c_word[2] and c_word[1] == c_word[3]:
                candidates.append(c_word[2:])
            elif len(c_word) >= 5 and c_word[0:2] == c_word[2:4]:
                candidates.append(c_word[2:])

        # 6. Sangihe Root Morphophonemic Alternations:
        # - w <-> b (e.g. waes <-> baes, wale <-> bale, welli <-> belli)
        # - r <-> d (e.g. redua <-> dadua, rario <-> dario, ruan <-> duan)
        # - Consonant endings: Sangihe lemmas typically end in echo-vowel 'e' (e.g. baes -> baese, luhud -> luhude)
        mutation_cands = []
        for c in list(candidates):
            c_clean = c.split("-")[0].split("'")[0]
            if len(c_clean) >= 3:
                mutation_cands.append(c_clean)
                if c_clean.startswith("w"):
                    mutation_cands.append("b" + c_clean[1:])
                elif c_clean.startswith("b"):
                    mutation_cands.append("w" + c_clean[1:])
                elif c_clean.startswith("r"):
                    mutation_cands.append("d" + c_clean[1:])
                elif c_clean.startswith("d"):
                    mutation_cands.append("r" + c_clean[1:])

        for mc in list(mutation_cands):
            if mc and mc[-1] not in "aeiou":
                mutation_cands.append(mc + "e")

        candidates.extend(mutation_cands)

        # Clean, unique, and ordered candidates (shortest/simplest roots usually most lemmatic)
        seen: Set[str] = set()
        ordered_candidates = []
        for cand in candidates:
            c = cand.strip("'-")
            if len(c) >= 2 and c not in seen:
                seen.add(c)
                ordered_candidates.append(c)

        # Sort so that exact word is first, followed by shortest distinct root candidates
        ordered_candidates.sort(key=lambda x: (x != norm, len(x)))
        analysis.candidate_stems = ordered_candidates
        return analysis


# Global stemmer singleton
_stemmer = SangiheStemmer()


def analyze_word(word: str) -> MorphologicalAnalysis:
    """Convenience function to analyze a Sangihe word."""
    return _stemmer.analyze(word)
