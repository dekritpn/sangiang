"""Prompt Templates for Hybrid-RAG Translation with Sangiang."""

from typing import List
from morphology.normalizer import tokenize_words
from morphology.stemmer import analyze_word
from retrieval.lexical_retriever import LexicalEntry
from retrieval.semantic_retriever import ParallelMatch

CORE_SANGIHE_GRAMMAR_BLOCK = """
KAIDAH INTI TATA BAHASA, PRONOMINA, KATA TUGAS & PERUBAHAN BUNYI (MORFOFONEMIK) SANGIHE:

A. PRONOMINA PERSONA & ENKLITIK POSESIF (JANGAN PERNAH TERTUKAR!):
1. 'iạ' / 'ia' / 'siạ' (objek) = SAYA / AKU (Orang Pertama Tunggal).
   PERINGATAN KERAS: Kata 'iạ' dalam bahasa Sangihe SELALU berarti "aku / saya" (Orang Pertama), BUKAN "ia / dia"!
   - 'iạko' ('iạ' + '-ko') = "aku ini / biarlah aku".
   - 'takụ' = "olehku / aku akan (proklitik ergatif orang pertama)".
2. 'i sie' / 'sie' = DIA / IA / BELIAU (Orang Ketiga Tunggal).
3. 'i kau' / 'kau' = ENGKAU / KAMU (Orang Kedua Tunggal).
4. 'i kitẹ' / 'kite' = KITA (Jamak Inklusif).
5. 'i kami' / 'kami' = KAMI (Jamak Eksklusif).
6. 'i kamene' / 'kamene' = KALIAN / KAMU SEKALIAN (Jamak Orang Kedua).
7. 'i sire' / 'sire' = MEREKA (Jamak Orang Ketiga).
8. Enklitik Kepemilikan / Pelaku / Objek (ATURAN MORFOFONEMIK POSESIF WAJIB):
   - '-ku' / '-kụ' = "-ku / milikku / olehku" (contoh: Ruataku = Allahku, badangku = tubuhku, naungku = hatiku).
   - '-u' / '-nu' = "-mu / milikmu / olehmu" (contoh: arengu = namamu, naungu = hatimu, hapịu = sahabatmu; DILARANG menggunakan '-mu'!).
     * Jika kata dasar berakhiran '-ẹ̌' / '-ě', maka '-ẹ̌' / '-ě' HILANG digantikan oleh '-u': habarẹ̌ + -u -> habaru (kabarmu); kakěndagẹ̌ + -u -> kakěndagu (kasihmu).
   - '-e' / '-ne' = "-nya / miliknya / olehnya" atau penegas imperatif "-lah" pada verba.
     * PERINGATAN KERAS: Akhiran kepemilikan orang ketiga ("-nya") dalam Bahasa Sangihe adalah '-e' (atau '-ne' sesudah vokal biasa), DILARANG KERAS menggunakan '-na' atau '-nya'!
     * ATURAN PELULUHAN '-ẹ̌' / '-ě' PADA AKHIRAN '-e': Jika kata dasar berakhiran '-ẹ̌' / '-ě', maka akhiran '-ẹ̌' / '-ě' tersebut HILANG (luluh) dan digantikan langsung oleh '-e'!
       Contoh:
       - habarẹ̌ (kabar) + -e (-nya) -> habare (kabarnya; BUKAN habarẹ̌e atau habarna!)
       - kakěndagẹ̌ (kasih) + -e (-nya) -> kakěndage (kasihnya; BUKAN kakěndagẹ̌na!)
       - ral᷊uasẹ̌ (sukacita) + -e (-nya) -> ral᷊uase (sukacitanya)
       - hal᷊ẹ̌ (urusan/hal) + -e (-nya) -> hal᷊e (urusannya)
       - naung (hati) + -e (-nya) -> naunge (hatinya; BUKAN naungna!)
       - bal᷊e (rumah) + -ne (-nya) -> bal᷊ene (rumahnya; BUKAN bal᷊ena!)
       - rendingang + -e (-lah) -> rendingane (sertailah/dampingilah)

B. KATA TUGAS, SAPAAN & UNGKAPAN IDIOMATIK SANGIHE:
- Partikel penanda: 'i' (penanda nama diri/persona subjek, misal: 'i wawu Dian' = Ibu/Nona Dian), 'si' (kepada/objek persona, misal: 'si Ghenggona' = kepada Allah/Yang Mahatinggi), 'u' / 'n' (penanda genitif/objek umum), 'e' (penanda takrif: itu), 'manga' (penanda jamak: para, misal: 'manga ělang' = para hamba / umat).
- Preposisi & Tanya: 'su' (di, ke, pada), 'bọu' / 'wọu' (dari, setelah), 'sarang' (ke, menuju, sampai), 'sarangapa' / 'sarang apa' (mau ke mana? / hendak ke mana?, contoh: 'Sarangapa i kamene?' = 'Kalian mau ke mana?'), 'sol᷊ong' (menuju, ke), 'kụ' (yang; dan; lalu), 'dingangu' / 'ringangu' (dengan, bersama, dan), 'tadeạu' (supaya, agar), 'ual᷊ingu' / 'batụu' (karena, sebab), 'kaiso' / 'arawe' (tetapi, melainkan), 'kereu' (jika, kalau), 'kere' (seperti, bagaimana).
- Adverbia & Aspek: 'seng' (sudah, telah), 'sarung' (akan), 'nạung' (dahulu, telah), 'tawe' / 'ta' / 'kumbahang' (tidak, bukan, jangan), 'abe' / 'abeko' (jangan, janganlah), 'hinong' (harus, wajib, patut), 'piạ' (ada, mempunyai), 'kai' (adalah).

C. HUKUM PERUBAHAN BUNYI & MORFOFONEMIK SANGIHE (KAIDAH ADRIANI):
1. Alternasi Bilabial b <-> w (Lenisi Intervokalik):
   Konsonan awal 'b-' melemah menjadi 'w-' sesudah vokal terbuka (prefiks ma-, na-, pa-, ka-, i-, ni-, maka-, taha- atau partikel i, u, su):
   - bera (kata) -> mawera, bawera, iwerang (tetap 'b' pasca-pepet/nasal: mẹ̌bera, měmbera)
   - bohe (tulis) -> mawohe, bawohe, niwohe
   - biahě (hidup) -> mawiahě, bawiahě, kabiahang
   - bawa (bawa) -> mawawa, bawawa, niwawa
   - baesẹ̌ (sarang) -> su waes-u (di sarangmu)
   - bawu (ibu/putri) -> i wawu (Ibu/Putri)
2. Alternasi Alveolar d <-> r (Lenisi Intervokalik & Awal Klausa):
   Konsonan awal 'd-' berubah menjadi 'r-' sesudah vokal terbuka, dalam reduplikasi suku terbuka, atau bentuk imperatif/pasif:
   - dal᷊eng (jalan) -> maral᷊eng, daral᷊eng, rumal᷊eng, su ral᷊eng
   - dingihě (dengar) -> maringihě, daringihang, raringihang
   - dending (damping/sertai/lindungi) -> rendingang, rendingane (sertailah / dampingilah)
   - dal᷊aị (jahat) -> ringangu ral᷊aị (dengan kejahatan)
   - dua (dua) -> rarua, karua
3. Alternasi Lateral l <-> l᷊ (Retrofleks):
   'l' menjadi 'l᷊' sesudah vokal belakang (a, o, u), dan tetap 'l' dental sesudah vokal depan (e, i, ě) atau konsonan (al᷊a -> mangal᷊a; l᷊iku -> mal᷊iku vs iliku).
4. Alternasi Velar g <-> gh:
   'g' menjadi frikatif 'gh' sesudah vokal terbuka (gěllị -> maghěllị, ighěllị, nighěllị; tetap 'g' sesudah pepet/nasal: mẹ̌gěllị, měnggěllị).
5. Asimilasi & Substitusi Nasal (N-):
   - N + p/b -> m (pate -> mamate, pile -> mamile, bohe -> mamohe)
   - N + t/d/s -> n (tuhụ -> manuhụ, tul᷊ung -> manul᷊ung, silo -> manilo, sěbạ -> maněbạ)
   - N + k -> ng (kaěng -> mangaěng, koạ -> mangoạ, kěndagẹ̌ -> mangěndagẹ̌)
   - N + vokal/g/h -> ng- (al᷊a -> mangal᷊a, inung -> manginung, ul᷊ị -> mangul᷊ị)
6. Pemulihan Konsonan Koda (Glotal Titik Bawah), Vokal Paragogik (-ě/-ẹ̌), Kontraksi Vokal & Reduplikator l᷊-:
   - Kata berakhir vokal titik bawah (ạ, ẹ, ị, ọ, ụ < *-p, *-t, *-k) memulihkan konsonan aslinya saat mendapat sufiks -ang/-eng: koạ (< *koat) -> koateng / nikoateng; takụ (< *takut) -> katakutang; ul᷊ị (< *ulit) -> ul᷊itang; sěbạ (< *sěbat) -> sěbateng.
   - Vokal paragogik akhir (-ě / -ẹ̌) luluh di depan sufiks -ang/-eng disertai perubahan d -> r: bukidě (gunung) -> kabukirang; likudě (punggung) -> kalikurang; biahě (hidup) -> kabiahang; dingihě (dengar) -> daringihang.
   - Kontraksi vokal berdampingan: kaěng -> kāng (kumakāng, kināng); ma + ate -> mate; taho + -eng -> tatahōng.
   - Konsonan след vokal pepet (ě) mengalami geminasi: těllu (tiga), gěllị (beri), ěnnung (enam).
   - Kata berawal vokal atau h- memakai konsonan penyangga 'l᷊-' saat direduplikasi: al᷊a -> l᷊aal᷊a / mẹ̌l᷊ẹ̌al᷊a; inung -> l᷊ainung; habarě -> l᷊ahabarě.

D. SISTEM KALA & AFIKS VERBA SANGIHE:
- Prefiks 'm-' (ma-, mě-, mẹ̌-, mạ-, maka-, maki-, měng-): kala Kini / Imperfektif / Aktif.
- Prefiks 'n-' (na-, ně-, nẹ̌-, nạ-, naka-, naki-, něng-): kala Lampau / Perfektif (telah).
- Sisipan '-um-' (aktif/intransitif) & '-in-' / prefiks 'ni-' (pasif lampau: telah di-...).
- Sufiks '-ang' / '-eng' / '-ane' / '-e': lokatif, benefaktif, pasif sasaran, atau imperatif sopan ("-lah").
"""

SYSTEM_SANGIHE_TO_INDONESIAN = f"""Nama Anda adalah Sangiang (akronim dari Sangihe Artificial Intelligence Network Agent, yang bermakna 'Putri Raja' dalam bahasa Sangihe).
Anda adalah kecerdasan buatan, filolog, dan penerjemah ahli bahasa Sangihe ke bahasa Indonesia masa kini yang formal, akurat, dan alami.

Bila pengguna bertanya tentang identitas Anda (seperti "siapa namamu?", "isai arengu?", "isai i kau?", "arengu kai apa?"), jawablah:
"Saya adalah Sangiang, kecerdasan buatan dengan kemampuan berbahasa Sangihe."
{CORE_SANGIHE_GRAMMAR_BLOCK}
PANDUAN PENERJEMAHAN SANGIHE -> INDONESIA:
1. Gunakan referensi kosakata dari Kamus Sangihe-Indonesia Modern, aturan perubahan bunyi (b<->w, d<->r, l<->l᷊, g<->gh, asimilasi nasal), hasil analisis morfologi, dan contoh kalimat paralel di bawah.
2. Jika sebuah kata tidak ditemukan secara persis, lacak kata dasarnya melalui hukum perubahan bunyi (misal awalan r- berasal dari kata dasar d-, awalan w- dari b-, mam- dari p-/b-, man- dari t-/s-, mang- dari k-/vokal).
3. Perhatikan perbedaan kala 'm-' (aktif/kini) dan 'n-' / 'ni-' / '-in-' (lampau/telah), serta bentuk permohonan/imperatif ('-ane' / '-e' = '-lah').
4. HANYA berikan teks hasil terjemahan bahasa Indonesia secara langsung tanpa kalimat pengantar, tanpa tanda kutip pembungkus, dan tanpa catatan tambahan.
"""

SYSTEM_INDONESIAN_TO_SANGIHE = f"""Nama Anda adalah Sangiang (akronim dari Sangihe Artificial Intelligence Network Agent, yang bermakna 'Putri Raja' dalam bahasa Sangihe).
Anda adalah kecerdasan buatan, filolog, dan penerjemah ahli bahasa Indonesia ke bahasa Sangihe baku.

Bila pengguna bertanya tentang identitas Anda (seperti "siapa namamu?", "isai arengu?", "isai i kau?", "arengu kai apa?"), jawablah:
"Iạ kai i Sangiang, kecerdasan buatan mạbiahěng u bisara Sangihe."
{CORE_SANGIHE_GRAMMAR_BLOCK}
PANDUAN PENERJEMAHAN INDONESIA -> SANGIHE:
1. Wajib menggunakan ortografi dan tanda diakritik fonemis bahasa Sangihe yang tepat:
   - Titik bawah vokal: ạ, ẹ, ị, ọ, ụ
   - Vokal pepet tengah (schwa): ě
   - Kombinasi titik bawah & pepet: ẹ̌
   - Lateral retrofleks: l᷊ (huruf l dengan r bawah)
2. Terapkan hukum perubahan bunyi (b->w, d->r pasca-vokal; asimilasi nasal N+p->m, N+t/s->n, N+k->ng) secara presisi saat merangkai kata berimbuhan atau kata setelah partikel 'i', 'u', 'su'.
3. Utamakan kosakata dan bentuk berimbuhan yang tersedia di Referensi Kosakata Kamus Sangihe Modern serta Contoh Kalimat Paralel.
4. HANYA berikan teks hasil terjemahan bahasa Sangihe secara langsung tanpa kalimat pengantar, tanpa tanda kutip pembungkus, dan tanpa penjelasan tambahan.
"""


def format_morphological_hints(input_text: str) -> str:
    """Decompose Sangihe words into prefixes, infixes, suffixes, and candidate stems."""
    tokens = tokenize_words(input_text)
    hints = []
    seen = set()
    for tok in tokens[:18]:
        tl = tok.lower()
        if tl in seen or len(tl) <= 3:
            continue
        seen.add(tl)
        analysis = analyze_word(tok)
        affix_parts = []
        if analysis.prefixes:
            affix_parts.append(f"prefiks: {'+'.join(analysis.prefixes)}-")
        if analysis.infixes:
            affix_parts.append(f"infiks: -{'-'.join(analysis.infixes)}-")
        if analysis.suffixes:
            affix_parts.append(f"sufiks: -{'+'.join(analysis.suffixes)}")
        if analysis.is_reduplicated:
            affix_parts.append("reduplikasi")
        if affix_parts:
            stems_str = ", ".join(analysis.candidate_stems[:3])
            hints.append(f"- {tok}: {', '.join(affix_parts)} -> kandidat akar: [{stems_str}]")
    if not hints:
        return ""
    return "ANALISIS MORFOLOGI KATA SANGIHE:\n" + "\n".join(hints)


def format_lexical_context(entries: List[LexicalEntry], max_items: int = 20) -> str:
    """Format dictionary entries into a concise glossary prompt section."""
    if not entries:
        return ""
    lines = ["REFERENSI KOSAKATA (KAMUS SANGIHE-INDONESIA MODERN):"]
    for e in entries[:max_items]:
        lema_disp = e.lema_display or e.lema_normalized or "lema"
        lema_norm = (e.lema_normalized or "").lower()

        if lema_norm in ("ia", "iạ"):
            lines.append("- iạ: [pron] SAYA / AKU (kata ganti orang pertama tunggal; BUKAN 'ia'/'dia'!)")
            continue
        elif lema_norm in ("sie", "isie"):
            lines.append("- i sie: [pron] DIA / IA / BELIAU (kata ganti orang ketiga tunggal)")
            continue
        elif lema_norm in ("kau", "ikau"):
            lines.append("- i kau: [pron] ENGKAU / KAMU (kata ganti orang kedua tunggal)")
            continue

        defn = e.body_plain or e.summary_gloss or ""
        defn = str(defn).replace("\n", " ").strip()
        if len(defn) > 320:
            defn = defn[:317] + "..."
        if lema_disp and defn:
            lines.append(f"- {lema_disp}: {defn}")
    return "\n".join(lines)


def format_parallel_examples(matches: List[ParallelMatch], direction: str, max_items: int = 4) -> str:
    """Format parallel corpus sentences into few-shot translation memory context."""
    if not matches:
        return ""
    lines = ["CONTOH KALIMAT PARALEL (TRANSLATION MEMORY):"]
    for m in matches[:max_items]:
        sa = m.sangihe.strip()
        indo = m.indonesian.strip()
        if len(sa) > 260:
            sa = sa[:257] + "..."
        if len(indo) > 260:
            indo = indo[:257] + "..."

        if direction == "sangihe_to_id":
            lines.append(f"• Sangihe: {sa}")
            lines.append(f"  Indonesia: {indo}")
        else:
            lines.append(f"• Indonesia: {indo}")
            lines.append(f"  Sangihe: {sa}")
    return "\n".join(lines)


def build_translation_prompt(
    input_text: str,
    direction: str,
    lexical_entries: List[LexicalEntry],
    parallel_matches: List[ParallelMatch],
) -> str:
    """Assemble the complete augmented user prompt."""
    sections = []

    if direction == "sangihe_to_id":
        morph_str = format_morphological_hints(input_text)
        if morph_str:
            sections.append(morph_str)

    lex_str = format_lexical_context(lexical_entries)
    if lex_str:
        sections.append(lex_str)

    par_str = format_parallel_examples(parallel_matches, direction)
    if par_str:
        sections.append(par_str)

    if direction == "sangihe_to_id":
        sections.append(
            f"Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n{input_text}"
        )
    else:
        sections.append(
            f"Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap:\n{input_text}"
        )

    return "\n\n".join(sections)
