"""Sangihe text normalization and diacritic handling.

Handles mapping between diacritic forms and normalized base forms:
- Sublinear dots: ạ, ẹ, ị, ọ, ụ
- Caron: ě
- Combined sublinear dot + caron: ẹ̌
- Lateral flap retroflex: l᷊ / L᷊ (l + U+1DCA)
- Standardized glottal stops / apostrophes
"""

import re
import unicodedata
from typing import List, Tuple

# Special Sangihe combining characters
COMBINING_R_BELOW = "\u1dca"  # ᷊ used for l᷊
COMBINING_CARON = "\u030c"    # ̌ used in ě and ẹ̌
COMBINING_DOT_BELOW = "\u0323"# ̣

# Exact mapping for known single/compound glyphs
DIACRITIC_MAP = {
    # Lowercase
    "ạ": "a",
    "ẹ": "e",
    "ẹ̌": "e",
    "ě": "e",
    "è": "e",
    "é": "e",
    "ị": "i",
    "ọ": "o",
    "ụ": "u",
    f"l{COMBINING_R_BELOW}": "l",
    # Uppercase
    "Ạ": "A",
    "Ẹ": "E",
    "Ẹ̌": "E",
    "Ě": "E",
    "È": "E",
    "É": "E",
    "Ị": "I",
    "Ọ": "O",
    "Ụ": "U",
    f"L{COMBINING_R_BELOW}": "L",
}

# Regex to match any Sangihe diacritic marker
DIACRITIC_PATTERN = re.compile(
    r"[ạẹịọụẠẸỊỌỤěĚèéÈÉ]|" +
    r"l\u1dca|L\u1dca|" +
    r"[\u1dca\u030c\u0323]"
)

# Standardize apostrophes / glottal stops
APOSTROPHE_PATTERN = re.compile(r"[’‘`ʻʼ]")


def normalize_sangihe(text: str, keep_apostrophe: bool = True) -> str:
    """Normalize Sangihe text to base ASCII form while preserving case and words.

    Args:
        text: Input Sangihe text with or without diacritics.
        keep_apostrophe: If True, keeps standard single quote ' for glottal stop.

    Returns:
        Normalized text with diacritics removed.
    """
    if not text:
        return ""

    # Replace stylized apostrophes with standard single quote
    normalized = APOSTROPHE_PATTERN.sub("'", text) if keep_apostrophe else APOSTROPHE_PATTERN.sub("", text)

    # First handle compound diacritics explicitly
    normalized = normalized.replace(f"l{COMBINING_R_BELOW}", "l")
    normalized = normalized.replace(f"L{COMBINING_R_BELOW}", "L")
    normalized = normalized.replace(f"ẹ{COMBINING_CARON}", "e")
    normalized = normalized.replace(f"Ẹ{COMBINING_CARON}", "E")

    # Character-by-character replacement
    res = []
    for ch in normalized:
        if ch in DIACRITIC_MAP:
            res.append(DIACRITIC_MAP[ch])
        elif ch in (COMBINING_R_BELOW, COMBINING_CARON, COMBINING_DOT_BELOW):
            continue
        else:
            res.append(ch)

    result = "".join(res)
    # Further ensure any decomposed combining marks are stripped
    decomposed = unicodedata.normalize("NFD", result)
    filtered = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", filtered)


def has_diacritics(text: str) -> bool:
    """Check if the text contains any Sangihe phonemic diacritics."""
    return bool(DIACRITIC_PATTERN.search(text))


def tokenize_words(text: str) -> List[str]:
    """Extract clean lowercase word tokens for dictionary matching."""
    cleaned = normalize_sangihe(text).lower()
    # Match words including hyphenated reduplications and glottals
    tokens = re.findall(r"\b[a-z0-9'\-]+\b", cleaned)
    return tokens
