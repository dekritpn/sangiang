"""Diacritic restoration and alignment post-processor for Bahasa Sangihe.

Aligns generated Sangihe text with the Steller-Aebersold lexical repository
to ensure all vowels and consonants (e.g. ạ, ẹ̌, ě, l᷊) have accurate phonemic diacritics.
"""

import re
from typing import Dict, Optional
from morphology.normalizer import (
    DIACRITIC_MAP,
    has_diacritics,
    normalize_sangihe,
)


class DiacriticRestorer:
    """Post-processor that restores and validates diacritics in generated Sangihe text."""

    def __init__(self, lexical_cache: Optional[Dict[str, str]] = None):
        """Initialize restorer with an optional in-memory mapping of norm_word -> diacritic_word."""
        self._cache: Dict[str, str] = lexical_cache or {}

    def update_cache(self, mapping: Dict[str, str]):
        """Add new known (normalized -> diacritic) word pairs from retrieved context."""
        for norm, dia in mapping.items():
            if norm and dia and isinstance(norm, str) and isinstance(dia, str) and has_diacritics(dia):
                self._cache[norm.lower()] = dia

    def restore_token(self, token: str) -> str:
        """Restore diacritics to a single word token if found in cache and needed."""
        # Separate leading and trailing punctuation
        match = re.match(r"^(\W*)([\w'\-]+)(\W*)$", token)
        if not match:
            return token

        prefix, word, suffix = match.groups()
        norm_word = normalize_sangihe(word).lower()

        # If already has diacritics, keep as is
        if has_diacritics(word):
            return token

        # If found in cache with diacritics
        if norm_word in self._cache:
            restored = self._cache[norm_word]
            # Match capitalization of original word
            if word.isupper():
                restored = restored.upper()
            elif word[0].isupper():
                restored = restored[0].upper() + restored[1:]
            return f"{prefix}{restored}{suffix}"

        return token

    def restore_text(self, text: str, context_glossary: Optional[Dict[str, str]] = None) -> str:
        """Restore diacritics in a full sentence or paragraph.

        Args:
            text: Sangihe text output by LLM.
            context_glossary: Optional mapping of normalized words to diacritic words
                              extracted from the retrieved RAG context for this query.

        Returns:
            Text with accurate phonemic diacritics restored.
        """
        if not text:
            return ""

        if context_glossary:
            self.update_cache(context_glossary)

        # Tokenize by whitespace while preserving spacing
        parts = re.split(r"(\s+)", text)
        result = []
        for part in parts:
            if part.isspace() or not part:
                result.append(part)
            else:
                result.append(self.restore_token(part))

        return "".join(result)
