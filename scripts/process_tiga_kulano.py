#!/usr/bin/env python3
"""Philological text cleaning, normalization, diacritic restoration, and parallel alignment
for 'Tiga Kulano dari Dagho' (Kumpulan Cerita Sangir Talaud, Paul Nebath et al., 1983).

Features:
1. Reconstitutes manuscript structure, catching and repairing the 1983 typesetting page swap
   between Story 7 (Walawo, Urang, Lipang...) and Story 12 (Datu I Dalero).
2. Cleans Indonesian and Regional texts of OCR artifacts, line break hyphenations, and typos.
3. Restores authentic Sangihe diacritics (ạ, ẹ, ị, ọ, ụ, ě, ẹ̌, l᷊) using a 62,000+ word lexical
   repository combining the Steller-Aebersold dictionary (sarindi.sqlite) and the Bible corpus.
4. Aligns parallel texts into sentence and stanza pairs using dynamic programming alignment.
5. Ingests aligned pairs into data/parallel_corpus.sqlite and rebuilds the FTS5 search index.
6. Exports datasets to data/tiga_kulano_aligned.jsonl and data/tiga_kulano_aligned.json.
"""

import json
import math
import os
import re
import sqlite3
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

# Path constants
RAW_FILE = "/tmp/tiga_kulano_raw.txt"
SARINDI_DB = "/home/dpng/Projects/Kamus/sarindi/assets/db/sarindi.sqlite"
CORPUS_DB = "data/parallel_corpus.sqlite"
OUT_JSONL = "data/tiga_kulano_aligned.jsonl"
OUT_JSON = "data/tiga_kulano_aligned.json"

# Sangihe combining characters
COMBINING_R_BELOW = "\u1dca"  # ᷊ for l᷊
COMBINING_CARON = "\u030c"    # ̌ for ě and ẹ̌
COMBINING_DOT_BELOW = "\u0323"# ̣ for ạ, ẹ, ị, ọ, ụ

# Diacritic mapping for normalization
DIACRITIC_MAP = {
    "ạ": "a", "ẹ": "e", "ẹ̌": "e", "ě": "e", "è": "e", "é": "e",
    "ị": "i", "ọ": "o", "ụ": "u", f"l{COMBINING_R_BELOW}": "l",
    "Ạ": "A", "Ẹ": "E", "Ẹ̌": "E", "Ě": "E", "È": "E", "É": "E",
    "Ị": "I", "Ọ": "O", "Ụ": "U", f"L{COMBINING_R_BELOW}": "L",
}


def normalize_sangihe_text(text: str) -> str:
    """Normalize Sangihe text to base ASCII form while preserving standard glottal stop."""
    if not text:
        return ""
    # Standardize apostrophes
    norm = re.sub(r"[’‘`ʻʼ]", "'", text)
    norm = norm.replace(f"l{COMBINING_R_BELOW}", "l").replace(f"L{COMBINING_R_BELOW}", "L")
    norm = norm.replace(f"ẹ{COMBINING_CARON}", "e").replace(f"Ẹ{COMBINING_CARON}", "E")
    
    res = []
    for ch in norm:
        if ch in DIACRITIC_MAP:
            res.append(DIACRITIC_MAP[ch])
        elif ch in (COMBINING_R_BELOW, COMBINING_CARON, COMBINING_DOT_BELOW):
            continue
        else:
            res.append(ch)
    result = "".join(res)
    decomposed = unicodedata.normalize("NFD", result)
    filtered = "".join(c for c in decomposed if unicodedata.category(c) != "Mn")
    return unicodedata.normalize("NFC", filtered)


class LexiconManager:
    """Manages lexical lookup and diacritic restoration."""

    def __init__(self, sarindi_path: str = SARINDI_DB, corpus_path: str = CORPUS_DB):
        self.lexicon: Dict[str, str] = {}
        self.load_sarindi(sarindi_path)
        self.load_corpus(corpus_path)
        print(f"Loaded {len(self.lexicon)} distinct vocabulary items into LexiconManager.")

    def load_sarindi(self, path: str):
        if not os.path.exists(path):
            print(f"Warning: Sarindi database not found at {path}")
            return
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("SELECT lema_display, lema_normalized, sublemmas_json FROM lemmas")
        for disp, norm, sublemmas in c.fetchall():
            if norm and disp:
                self.lexicon[norm.lower()] = disp
            if sublemmas:
                try:
                    items = json.loads(sublemmas)
                    for it in items:
                        snorm = it.get("normalized")
                        sdisp = it.get("sublema")
                        if snorm and sdisp:
                            self.lexicon[snorm.lower()] = sdisp
                except Exception:
                    pass
        conn.close()

    def load_corpus(self, path: str):
        if not os.path.exists(path):
            print(f"Warning: Corpus database not found at {path}")
            return
        conn = sqlite3.connect(path)
        c = conn.cursor()
        c.execute("SELECT sangihe_text, sangihe_normalized FROM parallel_sentences")
        for s_dia, s_norm in c.fetchall():
            toks_dia = re.findall(r"[\w\u1dca\u030c\u0323']+", s_dia)
            toks_norm = re.findall(r"[\w']+", s_norm)
            for td, tn in zip(toks_dia, toks_norm):
                tn_l = tn.lower()
                if tn_l not in self.lexicon:
                    self.lexicon[tn_l] = td
        conn.close()

    def restore_word(self, word: str) -> str:
        """Restore diacritics for a single word token if in lexicon."""
        # Strip leading/trailing punctuation
        m = re.match(r"^(\W*)([\w'\-]+)(\W*)$", word)
        if not m:
            return word
        prefix, w, suffix = m.groups()
        w_norm = normalize_sangihe_text(w).lower()
        
        # If already has diacritics, keep
        if any(c in word for c in "ạẹịọụěẹ̌") or COMBINING_R_BELOW in word:
            return word

        if w_norm in self.lexicon:
            restored = self.lexicon[w_norm]
            if w.isupper():
                restored = restored.upper()
            elif w[0].isupper():
                restored = restored[0].upper() + restored[1:]
            return f"{prefix}{restored}{suffix}"
        return word


def clean_indonesian_text(raw_text: str) -> str:
    """Clean OCR scan errors, headers, page numbers, and line wraps in Indonesian text."""
    lines = raw_text.splitlines()
    filtered = []
    for line in lines:
        l = line.strip()
        # Skip empty lines, page numbers, and title headers
        if not l or re.match(r"^\s*\d{1,3}\s*$", l) or re.match(r"^[-–—0•\.\,\'\"\s]{2,}$", l):
            continue
        if re.match(r"^\s*Terjemahan\s*:\s*$", l, re.IGNORECASE):
            continue
        filtered.append(l)

    text = "\n".join(filtered)
    # Unhyphenate line-broken words: "ber- \n mula" -> "bermula"
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
    # Join standard line breaks into single space
    text = re.sub(r"(\S)\s*\n\s*(\S)", r"\1 \2", text)

    # Standard OCR typo fixes in Indonesian text
    subs = [
        (r"\bdctn\b", "dan"),
        (r"\bpacta\b", "pada"),
        (r"\b3aerah\b", "daerah"),
        (r"\brriembunuh\b", "membunuh"),
        (r"\bsay a\b", "saya"),
        (r"\bIa par\b", "lapar"),
        (r"\bhuang jangkar\b", "buang jangkar"),
        (r"\bTfkus\b", "Tikus"),
        (r"\bberrnusyawarah\b", "bermusyawarah"),
        (r"\b1-a:u\b", "lalu"),
        (r"\bmemalran\b", "memakan"),
        (r"\brnayang\b", "moyang"),
        (r"\bd~ri\b", "dari"),
        (r"\bdalarn\b", "dalam"),
        (r"\brneliputi\b", "meliputi"),
        (r"\blak\.ilak\.i\b", "laki-laki"),
        (r"\btierubah\b", "terubah"),
        (r"\bm ulai\b", "mulai"),
        (r"\bHirnbawo\b", "Himbawo"),
        (r"\bOmpuilg\b", "Ompung"),
        (r"\bkelantok\b", "kalantok"),
        (r"\bDAFfARISI\b", "DAFTAR ISI"),
        (r"\bMilik Dep\..*", ""),
        (r"\bPPS/In/.*", ""),
        (r"\bDepartemen Pendidikan.*", ""),
        (r"\s+", " "),
    ]
    for pattern, replacement in subs:
        text = re.sub(pattern, replacement, text)

    return text.strip()


def clean_regional_text(raw_text: str, lexicon: LexiconManager, language: str) -> Tuple[str, str]:
    """Clean OCR scan errors, un-hyphenate, restore diacritics and normalize regional text."""
    lines = raw_text.splitlines()
    filtered = []
    for line in lines:
        l = line.strip()
        if not l or re.match(r"^\s*\d{1,3}\s*$", l) or re.match(r"^[-–—0•\.\,\'\"\s]{2,}$", l):
            continue
        filtered.append(l)

    text = "\n".join(filtered)
    # Unhyphenate line-broken words
    text = re.sub(r"(\w+)-\s*\n\s*(\w+)", r"\1\2", text)
    # Join standard line breaks into single space
    text = re.sub(r"(\S)\s*\n\s*(\S)", r"\1 \2", text)

    # Systematic OCR pattern corrections for Sangihe / Regional texts
    ocr_subs = [
        # Handwriting pen marks for pepet and vowel diacritics
        (r"~keng\b", "Běkeng"),
        (r"\b[B|b]~keng\b", "Běkeng"),
        (r"\bsi\'srba\b", "isěsěbạ"),
        (r"k11kimin[~ě]", "kụ kiminạ"),
        (r"\bntmua su \" ě\b", "nětumpa su"),
        (r"\bnakol!\b", "nakoạ"),
        (r"\bnaol!a\b", "naola"),
        (r"is[rf]s~?b[f|l]", "isěsěbạ"),
        (r"\b[r|R]fdua\b", "rědua"),
        (r"\b[r|R]~dua\b", "rědua"),
        (r"\b[s|S]fsane\b", "sěsane"),
        (r"\b[s|S]~sane\b", "sěsane"),
        (r"\b[t|T]Ellu\b", "těllu"),
        (r"\b[t|T]~llu\b", "těllu"),
        (r"\bdari9\b", "dario"),
        (r"\bdari\'i>\b", "dario"),
        (r"\bk~bi\b", "kěbi"),
        (r"\bs~mbay\b", "sěmbau"),
        (r"\bs~mbau\b", "sěmbau"),
        (r"\bternpong\b", "těmpong"),
        (r"\bt~mpong\b", "těmpong"),
        (r"\bnJkoa\b", "někoa"),
        (r"\bUa[J\.,]ingu\b", f"Ual{COMBINING_R_BELOW}ingu"),
        (r"\bUaJ\.ingu\b", f"Ual{COMBINING_R_BELOW}ingu"),
        (r"\bUa!!ngu\b", f"Ual{COMBINING_R_BELOW}ingu"),
        (r"\bua!ingu\b", f"ual{COMBINING_R_BELOW}ingu"),
        (r"\bpunda[L|l][,e|e]\b", f"pundal{COMBINING_R_BELOW}ẹ"),
        (r"\bpundale\b", f"pundal{COMBINING_R_BELOW}ẹ"),
        (r"\bkaka[L|l]abe\b", "kakalabẹ̌"),
        (r"\bn~dal_ahapi\b", f"nědal{COMBINING_R_BELOW}ahapi"),
        (r"\bTaghu[L|l]andang\b", f"Taghul{COMBINING_R_BELOW}andang"),
        (r"\bso[L|l]ong\b", f"sol{COMBINING_R_BELOW}ong"),
        (r"\bNolibagu\b", "Molibagu"),
        (r"\bky\b", "kụ"),
        (r"\bwaty\b", "watu"),
        (r"\btuhv\b", "tuhụ"),
        (r"\bOrnpung\b", "Ompung"),
        (r"\bghlguwa\b", "ghaguwa"),
        (r"\bmempeghaghighil~\b", "mempěghaghighilẹ̌"),
        (r"\bn~baelr\b", "něbaeli"),
        (r"\brldua\b", "rědua"),
        (r"\bbaelf\b", "baelẹ̌"),
        (r"\bnakha\b", "naběha"),
        (r"\bnabha\b", "naběha"),
        (r"\bnl!palingtakubf\b", "něpalingtakubẹ̌"),
        (r"\bt~Jako\b", "tělakọ"),
        (r"\bpahe\'pa\b", "pahepa"),
        (r"\bkuteukinatehceng\b", "kutẹu kinatẹ̌heang"),
        (r"\bkinaseng\b", "kinasěng"),
        (r"\bdurungc\b", "durunge"),
        (r"\bnahwtung\b", "nahutung"),
        (r"\blewohf\b", "lewọhe"),
        (r"\bm\(ngkate\b", "měngkate"),
        (r"\bm~1gkai\b", "měngkai"),
        (r"\bm~ngkate\b", "měngkate"),
        (r"\bmart!ngy\b", "marěngu"),
        (r"\bsengg9e\b", "sěnggọe"),
        (r"\bsasusq\b", "sasusẹ̌"),
        (r"\bkakuahe\b", "kakuahẹ̌"),
        (r"\bpaliahenge\b", "paliahengẹ̌"),
        (r"\bn~berae\b", "něberae"),
        (r"\bnetingkaraudf\b", "nětingkaraudẹ̌"),
        (r"\bru:nar\'ttoe\b", "rumanto"),
        (r"\bse~gka\b", "sěngka"),
        (r"\bmaremisl!\'\b", "marěmisẹ̌"),
        (r"\bkadod9\b", "kadodo"),
        (r"\bwe9\b", "wenga"),
        (r"\bbe9\b", "beo"),
        (r"\brari9\b", "dario"),
        (r"\bB9u\b", "Bọu"),
        (r"\bB9uene\b", "Bọu ene"),
        (r"\bkot9u\b", "kotau"),
        (r"\bkot9\b", "koto"),
        (r"\bnapel9\b", "napelo"),
        (r"\bmadarok9\b", "madaroko"),
        (r"\bMěnden9\b", "Měndeno"),
        (r"\bměnden9\b", "měndeno"),
        (r"\bKakěd1\b", "Kakědi"),
        (r"\bghag21\b", "ghaghurang"),
        (r"kl\}", "kụ"),
        (r"ir\{dua\b", "irědua"),
        (r"b<\]U\b", "bọu"),
        (r"b\)>U\b", "bọu"),
        (r"b<Y,e\b", "bọue"),
        (r"bc\]u\b", "bọu"),
        (r"katel<\]e\b", "katele"),
        (r"<!ndaung\b", "ěndaung"),
        (r"r<!dua\b", "rědua"),
        (r"m<!nsang\b", "mẹ̌nsang"),
        (r"\\ikitě\b", "i kite"),
        (r"\\arang\b", "sarang"),
        (r"k1J\b", "kụ"),
        (r"k11\b", "kụ"),
        (r"s1e\b", "siẹ"),
        (r"\ba_renge\b", "arenge"),
        (r"\btan&\.u\b", "tangu"),
        (r"\bbrdarl&\b", "bẹ̌dawe"),
        (r"\bwinang41!\b", "winangwaeng"),
        (r"\bbat11u\b", "battiu"),
        (r"\bbat11\b", "battiu"),
        (r"\bnas4\.e\b", "nasuẹ"),
        (r"\bk11kimině\b", "kụ kiminạ"),
        (r"\bk11kimin~\b", "kụ kiminạ"),
        (r"l,\{nggihě\b", f"l{COMBINING_R_BELOW}inggihě"),
        (r"\bmaintt!Iang\b", "naintalang"),
        (r"\braJ_ungu\b", f"ral{COMBINING_R_BELOW}ungu"),
        (r"\bdal_engu\b", f"dal{COMBINING_R_BELOW}engu"),
        (r"tt!luht!\'", "těluhe"),
        (r"\bgt!guwa\b", "gěguwa"),
        (r"\bmfb!bera\b", "měběbera"),
        (r"\bma!eno-leno\b", f"mal{COMBINING_R_BELOW}eno-leno"),
        (r"\bniwa!isang\b", f"niwal{COMBINING_R_BELOW}isang"),
        (r"\bda!ukang\b", f"dal{COMBINING_R_BELOW}ukang"),
        (r"\bba!agě\b", f"bal{COMBINING_R_BELOW}agẹ̌"),
        (r"\bgal!poho\b", f"gal{COMBINING_R_BELOW}poho"),
        (r"\bwa!eng\b", f"wal{COMBINING_R_BELOW}eng"),
        (r"\bpě datu\b", "piạ datu"),
        (r"\bpě\b", "piạ"),
        (r"\bslndokateng\b", "sindokateng"),
        (r"\bGumansa!angi\b", f"Gumansal{COMBINING_R_BELOW}angi"),
        (r"\bnibaJ\.i\b", f"nibal{COMBINING_R_BELOW}i"),
        (r"\bKondawu1aeng\b", f"Kondawul{COMBINING_R_BELOW}aeng"),
        (r"\bKondawu~eng\b", f"Kondawul{COMBINING_R_BELOW}aeng"),
        (r"\bap:Wntu\b", "apuintu"),
        (r"\btakasěngkulang Ua!!ngu\b", f"takasěngkulang. Ual{COMBINING_R_BELOW}ingu"),
        (r"\btua1inge\b", f"tual{COMBINING_R_BELOW}inge"),
        (r"\bso1ong\b", f"sol{COMBINING_R_BELOW}ong"),
        (r"\bso15>ng\b", f"sol{COMBINING_R_BELOW}ong"),
        (r"\bSangianghia1Jě\b", "Sangianghiabẹ̌"),
        (r"\bnapa1\b", f"napal{COMBINING_R_BELOW}a"),
        (r"\bsura1ungu\b", f"sural{COMBINING_R_BELOW}ungu"),
        (r"\bb9ě\b", "bọue"),
        (r"\bru1unge\b", f"rul{COMBINING_R_BELOW}unge"),
        (r"\btabel2-ko\b", "tabelo-ko"),
        (r"\}Gi_lighae\b", "Ngiangnilighide"),
        (r"\bna1,tdě\b", f"naintal{COMBINING_R_BELOW}ang"),
        (r"\bnempanga1,ll\b", f"němpangal{COMBINING_R_BELOW}a"),
        (r"\bma!9ang\b", f"mal{COMBINING_R_BELOW}ang"),
        (r"\bTun1elae\b", f"Tumel{COMBINING_R_BELOW}a"),
        (r"\bweng61\b", "wengko"),
        (r"\bPinal,<J\.\b", f"Pinal{COMBINING_R_BELOW}ang."),
        (r"\bměMba11\b", "měmbali"),
        (r"tinta\]png\b", "tintahong"),
        (r"\běkeng\b", "Běkeng"),
        # Tilde over e as pepet
        (r"~", "ě"),
        (r"([a-zA-Z]+)[\{\}]\b", r"\1e"),
        (r"([a-zA-Z]+)[\{\}]", r"\1"),
        (r"([a-zA-Z]+)9\b", r"\1o"),
        (r"([a-zA-Z]+)9([a-zA-Z]+)", r"\1o\2"),
        (r"([bcdfghjklmnprstvwzBCDFGHJKLMNPRSTVWZ])!([bcdfghjklmnprstvwzBCDFGHJKLMNPRSTVWZ])", r"\1ě\2"),
        (r"([aeiouAEIOU])!([aeiouAEIOU])", rf"\1l{COMBINING_R_BELOW}\2"),
        (r"([aeiouAEIOU])!([bcdfghjklmnprstvwz])", rf"\1l{COMBINING_R_BELOW}\2"),
        (r"([bcdfghjklmnprstvwz])!([aeiouAEIOU])", rf"\1l{COMBINING_R_BELOW}\2"),
        (r"c!", "cẹ̌"),
        (r"t!", "tẹ̌"),
        (r"\s+", " "),
    ]
    for pattern, replacement in ocr_subs:
        text = re.sub(pattern, replacement, text)

    # Word-by-word lexicon restoration if Sangihe/Siau/Tagulandang
    words = text.split(" ")
    restored_words = []
    for w in words:
        if language in ("sangihe", "tagulandang", "siau"):
            restored_words.append(lexicon.restore_word(w))
        else:
            restored_words.append(w)
    
    sangihe_text = " ".join(restored_words).strip()
    sangihe_normalized = normalize_sangihe_text(sangihe_text)
    return sangihe_text, sangihe_normalized


def split_sentences(text: str) -> List[str]:
    """Split text into sentences while preserving abbreviations and quotes."""
    text = re.sub(r"\s+", " ", text).strip()
    # Protect common abbreviations: e.g. no., dsb., etc.
    text = re.sub(r"\b(no|dsb|hal|dst|sbb|dll)\.", r"\1<DOT>", text, flags=re.IGNORECASE)
    parts = re.split(r"(?<=[\.\!\?])\s+(?=[A-Z\"\'“‘\d])", text)
    sentences = []
    for p in parts:
        p = p.replace("<DOT>", ".").strip()
        # Clean leading story title numbering if any (e.g. "1.", "12.")
        p = re.sub(r"^\d{1,2}\.\s*", "", p)
        if len(p) > 5:
            sentences.append(p)
    return sentences


def align_story_sentences_dp(id_sents: List[str], reg_sents: List[str]) -> List[Tuple[str, str]]:
    """Dynamic programming sentence aligner based on character length ratio and anchor bonuses."""
    n, m = len(id_sents), len(reg_sents)
    if n == 0 or m == 0:
        return []

    def score(sa_list: List[str], sb_list: List[str]) -> float:
        len_a = sum(len(s) for s in sa_list)
        len_b = sum(len(s) for s in sb_list)
        if len_a == 0 or len_b == 0:
            return -999.0
        # Expected ratio len_b / len_a is ~ 1.02
        ratio = len_b / len_a
        diff = abs(math.log(ratio / 1.02))
        cost = - (diff ** 2) * 12.0
        
        # Check shared proper nouns / numbers as anchor bonus
        words_a = set(re.findall(r"\b[A-Z0-9][a-z0-9]+\b", " ".join(sa_list)))
        words_b = set(re.findall(r"\b[A-Z0-9][a-z0-9]+\b", " ".join(sb_list)))
        shared = words_a.intersection(words_b)
        bonus = len(shared) * 8.0
        return cost + bonus

    # DP table: key is (i, j), value is max score
    dp: Dict[Tuple[int, int], float] = {(0, 0): 0.0}
    backtrack: Dict[Tuple[int, int], Tuple[int, int]] = {}

    for i in range(n + 1):
        for j in range(m + 1):
            if (i, j) not in dp:
                continue
            curr_score = dp[(i, j)]
            # Transition steps: (1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1)
            steps = [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (3, 1)]
            for di, dj in steps:
                if i + di <= n and j + dj <= m:
                    step_score = score(id_sents[i:i+di], reg_sents[j:j+dj])
                    tot = curr_score + step_score
                    target = (i + di, j + dj)
                    if target not in dp or tot > dp[target]:
                        dp[target] = tot
                        backtrack[target] = (i, j)

    # Reconstruct alignment path
    path = []
    curr = (n, m)
    while curr != (0, 0):
        prev = backtrack.get(curr)
        if not prev:
            break
        path.append((prev, curr))
        curr = prev
    path.reverse()

    aligned_pairs = []
    for prev, nxt in path:
        pi, pj = prev
        ni, nj = nxt
        a_text = " ".join(id_sents[pi:ni])
        b_text = " ".join(reg_sents[pj:nj])
        aligned_pairs.append((a_text, b_text))
    return aligned_pairs


def extract_all_stories(raw_pages: List[str]) -> List[Dict]:
    """Extract all 14 stories, accurately handling the Story 7 & 12 layout swap."""
    stories = []

    # Story metadata definitions: (id_start, id_end, reg_start, reg_end, lang, title_id, title_reg)
    meta = [
        (1, 10, 14, 15, 20, "sangihe", "Cerita Putri Bernama Tomatiti", "Běkeng Sangiang I Sěsěbạ Si Tomatiti"),
        (2, 21, 25, 26, 30, "sangihe", "Gumansalangi", "Gumansalangi"),
        (3, 31, 34, 35, 39, "sangihe", "Putri Ngiangnilighide Ditawan oleh Himbawo Raja Siau", "Běkeng Ngiang Nilighide Nitangihe Himbawo Ratung Siau"),
        (4, 40, 43, 44, 46, "talaud", "Manusia Pertama di Kepulauan Talaud", "Alamona Ntaumata Ntaloda"),
        (5, 47, 50, 51, 54, "sangihe", "Ompung", "Ompung"),
        (6, 55, 57, 58, 60, "talaud", "Karena Anak Tidak Mendengar Orang Tua", "Battiu Anao Tawe Mangisingngu Timmade"),
        (7, 61, 62, 63, 65, "sangihe", "Cerita Tikus, Udang, Lipan, Meleo, Belut, Jarum dan Palu", "Běkeng I Walawo, I Urang, I Lipang, I Melle, I Kasili, I Rarahung Dingangu I Ransilang"),
        (8, 66, 69, 70, 72, "sangihe", "Ceritera Ampuang Pertama", "Běkeng Ampuang Humotonge"),
        (9, 73, 76, 77, 80, "tagulandang", "Tanjung Terputus", "Tonggeng Napoto"),
        (10, 81, 84, 85, 89, "sangihe", "Ceritra Tiga Orang Pemberani Dari Dagho", "Běkeng Isire Těllu Wawahani Su Ragho"),
        (11, 90, 92, 93, 95, "siau", "Cerita Ikan Tongkol dan Ayam Burik", "Běkeng Kina Hetung Dingangu Manu Banggiung"),
        (12, 96, 98, 99, 100, "sangihe", "Ceritera Raja Dalero", "Běkeng Datu I Ralero"),
        (13, 101, 102, 103, 104, "sangihe", "Cerita Kera dengan Bangau", "Běkeng Baha Reduang Bahoa"),
        (14, 105, 106, 107, 108, "sangihe", "Cerita Elang Laut dengan Siput", "Běkeng Baralang Deduang Komang"),
    ]

    for num, id_s, id_e, reg_s, reg_e, lang, title_id, title_reg in meta:
        id_raw = "\n".join(raw_pages[id_s-1:id_e])

        if num == 7:
            # Reconstruct Story 7:
            # Part 1: Page 63 up to 'nahungkaiangke su wowong'
            p63 = raw_pages[62]
            split_p63 = "nahungkaiangke su wowong"
            idx_split = p63.find(split_p63) + len(split_p63)
            s7_part1 = p63[:idx_split]
            # Part 2: Page 99 from '"Jadi tang. Ene I Walawo' + Page 100
            p99 = raw_pages[98]
            split_marker_p99 = '"Jadi tang. Ene I Walawo'
            _, s7_p2_raw = p99.split(split_marker_p99, 1)
            s7_part2 = split_marker_p99 + s7_p2_raw + "\n" + raw_pages[99]
            reg_raw = s7_part1 + "\n" + s7_part2

        elif num == 12:
            # Reconstruct Story 12:
            # Part 1: Page 99 up to '"Jadi tang. Ene I Walawo'
            p99 = raw_pages[98]
            split_marker_p99 = '"Jadi tang. Ene I Walawo'
            s12_part1, _ = p99.split(split_marker_p99, 1)
            # Part 2: Page 63 from 'nahungkaiangke su wowong' + Pages 64 & 65
            p63 = raw_pages[62]
            split_p63 = "nahungkaiangke su wowong"
            idx_split = p63.find(split_p63) + len(split_p63)
            s12_part2_a = p63[idx_split:]
            s12_part2_b = raw_pages[63] + "\n" + raw_pages[64]
            reg_raw = s12_part1 + "\n" + s12_part2_a + "\n" + s12_part2_b

        else:
            reg_raw = "\n".join(raw_pages[reg_s-1:reg_e])

        stories.append({
            "story_id": num,
            "title_id": title_id,
            "title_reg": title_reg,
            "language": lang,
            "id_raw": id_raw,
            "reg_raw": reg_raw,
        })

    return stories


def process_and_align_all():
    """Main pipeline execution."""
    print("=" * 70)
    print("PROCESSOR: TIGA KULANO DARI DAGHO (PARALLEL CORPUS ALIGNMENT)")
    print("=" * 70)

    # 1. Initialize Lexicon Manager
    lexicon = LexiconManager()

    # 2. Read raw pages
    if not os.path.exists(RAW_FILE):
        raise FileNotFoundError(f"Raw file {RAW_FILE} not found.")

    with open(RAW_FILE, "r", encoding="utf-8") as f:
        full_text = f.read()

    pages = full_text.split("\x0c")
    print(f"Extracted {len(pages)} pages from {RAW_FILE}.")

    # 3. Extract and stitch stories
    raw_stories = extract_all_stories(pages)
    print(f"Parsed {len(raw_stories)} stories with typesetting swap repairs.\n")

    all_aligned_records: List[Dict] = []
    stats_per_story = []

    # 4. Clean, restore, and align each story
    for st in raw_stories:
        s_id = st["story_id"]
        t_id = st["title_id"]
        t_reg = st["title_reg"]
        lang = st["language"]

        # Clean texts
        id_cleaned = clean_indonesian_text(st["id_raw"])
        reg_cleaned, reg_norm = clean_regional_text(st["reg_raw"], lexicon, lang)

        # Split into sentences
        id_sents = split_sentences(id_cleaned)
        reg_sents = split_sentences(reg_cleaned)

        # Align sentences using DP
        pairs = align_story_sentences_dp(id_sents, reg_sents)

        story_records = []
        for p_idx, (id_seg, reg_seg) in enumerate(pairs, start=1):
            reg_seg_norm = normalize_sangihe_text(reg_seg)
            rec = {
                "story_id": s_id,
                "story_title_id": t_id,
                "story_title_reg": t_reg,
                "language": lang,
                "unit_id": f"tiga_kulano:{s_id}:{p_idx:03d}",
                "indonesian_text": id_seg,
                "regional_text": reg_seg,
                "regional_normalized": reg_seg_norm,
                "char_ratio": round(len(reg_seg) / max(len(id_seg), 1), 2),
            }
            story_records.append(rec)
            all_aligned_records.append(rec)

        stats_per_story.append({
            "story_id": s_id,
            "title": t_id,
            "language": lang,
            "id_sents": len(id_sents),
            "reg_sents": len(reg_sents),
            "aligned_pairs": len(pairs),
            "id_words": len(id_cleaned.split()),
            "reg_words": len(reg_cleaned.split()),
        })

        print(f"Story {s_id:2d}: {t_id[:35]:35s} [{lang:11s}] -> {len(pairs):2d} pairs (ID: {len(id_sents):2d}, REG: {len(reg_sents):2d})")

    # 5. Export JSONL and JSON
    Path(OUT_JSONL).parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSONL, "w", encoding="utf-8") as f:
        for r in all_aligned_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"\nExported {len(all_aligned_records)} aligned records to {OUT_JSONL}.")

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_aligned_records, f, ensure_ascii=False, indent=2)
    print(f"Exported formatted JSON to {OUT_JSON}.")

    # 6. Ingest into SQLite Database
    ingest_into_database(all_aligned_records)

    # 7. Print Summary Statistics
    print("\n" + "=" * 70)
    print("INGESTION & ALIGNMENT SUMMARY")
    print("=" * 70)
    total_pairs = len(all_aligned_records)
    total_id_words = sum(s["id_words"] for s in stats_per_story)
    total_reg_words = sum(s["reg_words"] for s in stats_per_story)
    print(f"Total Aligned Sentence Pairs: {total_pairs}")
    print(f"Total Indonesian Words     : {total_id_words:,}")
    print(f"Total Regional Words       : {total_reg_words:,}")
    
    # Dialect breakdown
    lang_counts = {}
    for r in all_aligned_records:
        l = r["language"]
        lang_counts[l] = lang_counts.get(l, 0) + 1
    print("\nDialect Distribution:")
    for l, cnt in lang_counts.items():
        print(f"  - {l:12s}: {cnt:3d} pairs ({cnt/total_pairs*100:.1f}%)")

    # Sample aligned output
    print("\nSample Aligned Pairs:")
    for sample_idx in [0, 45, 120, 250, total_pairs - 1]:
        if sample_idx < total_pairs:
            s_rec = all_aligned_records[sample_idx]
            print(f"\n--- [{s_rec['unit_id']}] ({s_rec['language']}) ---")
            print(f"  ID : {s_rec['indonesian_text']}")
            print(f"  REG: {s_rec['regional_text']}")
            print(f"  NRM: {s_rec['regional_normalized']}")


def ingest_into_database(records: List[Dict], db_path: str = CORPUS_DB):
    """Ingest aligned records into parallel_sentences and rebuild FTS5 index."""
    if not os.path.exists(db_path):
        print(f"Database {db_path} does not exist. Creating...")

    conn = sqlite3.connect(db_path)
    c = conn.cursor()

    # Check if 'tiga_kulano' already present, remove old entries if re-running
    c.execute("DELETE FROM parallel_sentences WHERE source_domain = 'tiga_kulano'")
    print(f"Cleared existing 'tiga_kulano' rows from {db_path}.")

    db_rows = []
    for r in records:
        source_domain = "tiga_kulano"
        ref_id = r["unit_id"]
        s_text = r["regional_text"]
        s_norm = r["regional_normalized"]
        id_text = r["indonesian_text"]
        bimk = f"[{r['language'].upper()}] {r['story_title_id']}"
        db_rows.append((source_domain, ref_id, s_text, s_norm, id_text, bimk))

    c.executemany("""
        INSERT INTO parallel_sentences 
        (source_domain, reference_id, sangihe_text, sangihe_normalized, indonesian_tb, indonesian_bimk)
        VALUES (?, ?, ?, ?, ?, ?);
    """, db_rows)

    print(f"Inserted {len(db_rows)} records into parallel_sentences.")

    # Rebuild FTS5 index
    c.execute("INSERT INTO parallel_fts(parallel_fts) VALUES('rebuild');")
    conn.commit()
    print("Rebuilt parallel_fts virtual table index successfully.")

    # Verify counts
    c.execute("SELECT source_domain, count(*) FROM parallel_sentences GROUP BY source_domain")
    print("\nUpdated database domain counts:")
    for domain, count in c.fetchall():
        print(f"  - {domain:15s}: {count:,} sentences")

    conn.close()


if __name__ == "__main__":
    process_and_align_all()
