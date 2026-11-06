/**
 * Sangiang Hybrid-RAG Core Engine for Cloudflare Pages Functions + Cloudflare D1
 * Initiator: Yayasan Cipta Manggala Dwipa
 * AI System Engineering & Translation: Divisi DigiLab CMD
 */

const DIACRITIC_MAP = {
  "ạ": "a", "Ạ": "A",
  "ẹ": "e", "Ẹ": "E",
  "ị": "i", "Ị": "I",
  "ọ": "o", "Ọ": "O",
  "ụ": "u", "Ụ": "U",
  "ě": "e", "Ě": "E",
  "ă": "a", "Ă": "A",
  "ē": "e", "Ē": "E",
  "ī": "i", "Ī": "I",
  "ō": "o", "Ō": "O",
  "ū": "u", "Ū": "U",
  "ā": "a", "Ā": "A",
  "á": "a", "é": "e", "í": "i", "ó": "o", "ú": "u",
  "à": "a", "è": "e", "ì": "i", "ò": "o", "ù": "u",
  "ä": "a", "ë": "e", "ï": "i", "ö": "o", "ü": "u",
  "ê": "e", "ô": "o", "â": "a", "î": "i", "û": "u",
};

const COMBINING_STRIP = new Set(["\u1DCA", "\u0323", "\u030C", "\u0306", "\u0304", "\u0301", "\u0300", "\u0308", "\u0302"]);

export function normalizeSangihe(text) {
  if (!text) return "";
  let s = text.normalize("NFC");
  let out = [];
  for (const ch of s) {
    if (COMBINING_STRIP.has(ch)) continue;
    if (DIACRITIC_MAP[ch]) {
      out.push(DIACRITIC_MAP[ch]);
    } else {
      out.push(ch);
    }
  }
  s = out.join("").normalize("NFD");
  s = Array.from(s).filter(ch => !COMBINING_STRIP.has(ch)).join("").normalize("NFC");
  s = s.replace(/[’‘`´ʼ]/g, "'");
  s = s.replace(/\s+/g, " ").trim();
  return s;
}

export function hasDiacritics(text) {
  if (!text) return false;
  for (const ch of text) {
    if (DIACRITIC_MAP[ch] || COMBINING_STRIP.has(ch)) return true;
  }
  return false;
}

export function tokenizeWords(text, normalize = true) {
  const target = normalize ? normalizeSangihe(text).toLowerCase() : (text || "");
  const matches = target.match(/[a-zA-Zạẹịọụěăēīōūāáéíóúàèìòùäëïöüêôâîû\u1DCA\u0323\u030C'-]+/g) || [];
  return matches.map(t => t.replace(/^['-]+|['-]+$/g, "")).filter(Boolean);
}

const PREFIXES = [
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
  "me", "ne", "pe",
  "ma", "na", "pa",
  "mi", "ni", "pi",
  "mo", "no", "po",
  "mu", "nu", "pu",
  "ka", "ki", "ko", "ku",
  "ta", "te", "to",
  "sa", "se", "so",
  "i",
].sort((a, b) => b.length - a.length);

const SUFFIXES = [
  "kewewe", "tewewe", "pewewe",
  "sarang", "kewe", "tewe", "pewe", "tade",
  "angku", "engku", "engne", "angne",
  "kue", "neu",
  "ang", "eng", "ing", "ong",
  "ku", "nu", "ne", "we", "ko",
  "e", "u",
].sort((a, b) => b.length - a.length);

const INFIXES = ["um", "in", "im"];

export function analyzeWord(word) {
  const norm = normalizeSangihe(word).toLowerCase();
  const analysis = {
    surface: word,
    normalized: norm,
    is_reduplicated: false,
    prefixes: [],
    infixes: [],
    suffixes: [],
    candidate_stems: [],
  };
  if (!norm) return analysis;

  const candidates = [norm];
  let current = norm;

  if (norm.includes("-")) {
    const parts = norm.split("-");
    if (parts.length === 2) {
      if (parts[0] === parts[1]) analysis.is_reduplicated = true;
      candidates.push(parts[0], parts[1]);
      current = parts[0];
    }
  }

  for (let pass = 0; pass < 2; pass++) {
    let stripped = false;
    for (const suf of SUFFIXES) {
      if (current.length >= suf.length + 2 && current.endsWith(suf)) {
        const base = current.slice(0, -suf.length);
        analysis.suffixes.push(suf);
        candidates.push(base);
        if (base && !"aiueo".includes(base[base.length - 1])) {
          candidates.push(base + "e");
        }
        current = base;
        stripped = true;
        break;
      }
    }
    if (!stripped) break;
  }

  for (const inf of INFIXES) {
    if (current.length >= 5 && current.slice(1, 3) === inf) {
      const deinfixed = current[0] + current.slice(3);
      analysis.infixes.push(inf);
      candidates.push(deinfixed);
      current = deinfixed;
      break;
    }
  }

  for (let pass = 0; pass < 2; pass++) {
    let matchedPref = null;
    for (const pref of PREFIXES) {
      if (current.length >= pref.length + 3 && current.startsWith(pref)) {
        matchedPref = pref;
        break;
      }
    }
    if (!matchedPref) break;
    analysis.prefixes.push(matchedPref);
    const stem = current.slice(matchedPref.length);
    candidates.push(stem);

    // Morphophonemic nasal & lenition reversals
    if (matchedPref.endsWith("m")) {
      candidates.push("p" + stem, "b" + stem, "w" + stem);
    } else if (matchedPref.endsWith("n") && !matchedPref.endsWith("ng")) {
      candidates.push("t" + stem, "d" + stem, "s" + stem);
    } else if (matchedPref.endsWith("ng")) {
      candidates.push("k" + stem);
    }
    if (stem.startsWith("w")) candidates.push("b" + stem.slice(1));
    if (stem.startsWith("r")) candidates.push("d" + stem.slice(1));
    if (stem.startsWith("gh")) candidates.push("g" + stem.slice(2));
    current = stem;
  }

  // Also check initial r->d and w->b on surface
  if (norm.startsWith("r") && norm.length >= 4) candidates.push("d" + norm.slice(1));
  if (norm.startsWith("w") && norm.length >= 4) candidates.push("b" + norm.slice(1));

  const seen = new Set();
  for (const c of candidates) {
    if (c && c.length >= 2 && !seen.has(c)) {
      seen.add(c);
      analysis.candidate_stems.push(c);
    }
  }
  return analysis;
}

export const SANGIHE_STOPWORDS = new Set([
  "su", "u", "i", "e", "ku", "kụ", "si", "ringangu", "dingangu", "bou", "bọu", "sarang",
  "kai", "tawe", "tawẹ", "ute", "tangu", "tangú", "ene", "ini", "manga",
  "wou", "wọi", "solong", "sol᷊ong", "kere", "kereu", "maning", "mase",
  "kuteu", "kutẹu", "seng", "sen", "ren", "den",
]);

export const SANGIHE_PRONOUNS = new Set([
  "iạ", "ia", "siạ", "sia", "sie", "isie", "kau", "ikau",
  "kami", "ikami", "kite", "kitẹ", "ikite", "sire", "isire", "kamene", "iạko",
]);

export const INDONESIAN_STOPWORDS = new Set([
  "dan", "di", "ke", "dari", "yang", "pada", "untuk", "dengan", "ini", "itu",
  "atau", "adalah", "ia", "dia", "mereka", "kita", "kami", "kamu", "aku", "saya",
  "akan", "telah", "sudah", "bisa", "dapat", "ada", "tidak", "bukan", "pun",
  "juga", "lalu", "kemudian", "maka", "bahwa", "oleh", "karena", "kepadanya",
  "kepada", "sang", "seekor", "seorang", "sebuah", "para", "sedang",
]);

export async function lookupSangiheTokens(db, tokens, maxResults = 20) {
  if (!db || !tokens || tokens.length === 0) return [];

  let filtered = tokens.filter(
    t => SANGIHE_PRONOUNS.has(t.toLowerCase()) || (!SANGIHE_STOPWORDS.has(t.toLowerCase()) && t.length > 2)
  );
  if (filtered.length === 0) {
    filtered = tokens.filter(t => SANGIHE_PRONOUNS.has(t.toLowerCase()) || t.length > 2);
  }

  const dedup = [];
  const seenRaw = new Set();
  for (const t of filtered) {
    const tl = normalizeSangihe(t.toLowerCase()).toLowerCase();
    if (!seenRaw.has(tl)) {
      seenRaw.add(tl);
      dedup.push(t);
    }
  }

  const surfaceList = [];
  const tokenStems = {};
  for (const tok of dedup.slice(0, 25)) {
    const tokLower = tok.toLowerCase();
    let normSurf;
    if (SANGIHE_PRONOUNS.has(tokLower)) {
      normSurf = ["iạ", "ia", "iạko"].includes(tokLower) ? "ia" : (["sie", "isie"].includes(tokLower) ? "sie" : tokLower);
    } else {
      normSurf = normalizeSangihe(tokLower).toLowerCase();
    }
    if (normSurf && (SANGIHE_PRONOUNS.has(normSurf) || normSurf.length > 2)) {
      if (!surfaceList.includes(normSurf)) surfaceList.push(normSurf);
      const analysis = analyzeWord(tok);
      tokenStems[normSurf] = analysis.candidate_stems.filter(
        c => c !== normSurf && (SANGIHE_PRONOUNS.has(c) || c.length > 2)
      );
    }
  }

  if (surfaceList.length === 0) return [];

  const entries = [];
  const seenNorms = new Set();
  const normToEntry = {};
  const normSenseCounts = {};

  async function fetchByNorms(norms) {
    if (!norms.length || entries.length >= maxResults) return;
    const batch = norms.slice(0, 30);
    const placeholders = batch.map(() => "?").join(",");
    const rem = maxResults - entries.length;
    const sql = `
      SELECT id, lema_display, lema_normalized, summary_gloss, body_plain, sublemmas_json
      FROM lemmas
      WHERE lema_normalized IN (${placeholders})
      ORDER BY id ASC
      LIMIT ?;
    `;
    const { results } = await db.prepare(sql).bind(...batch, rem * 4).all();
    for (const row of results || []) {
      const lnorm = (row.lema_normalized || "").toLowerCase();
      const ldisp = row.lema_display || row.lema_normalized || "";
      const sgloss = row.summary_gloss || "";
      const bplain = row.body_plain || sgloss;
      if (!seenNorms.has(lnorm)) {
        if (entries.length >= maxResults) continue;
        seenNorms.add(lnorm);
        normSenseCounts[lnorm] = 1;
        let subs = [];
        try { subs = JSON.parse(row.sublemmas_json || "[]"); } catch {}
        const entryObj = {
          lemma_id: row.id,
          lema_display: ldisp,
          lema_normalized: row.lema_normalized || "",
          summary_gloss: sgloss,
          body_plain: bplain,
          sublemmas: subs,
          match_source: "lemma",
        };
        entries.push(entryObj);
        normToEntry[lnorm] = entryObj;
      } else if (normToEntry[lnorm] && (normSenseCounts[lnorm] || 1) < 3 && sgloss) {
        const existing = normToEntry[lnorm];
        if (!existing.summary_gloss.includes(sgloss.slice(0, 40))) {
          normSenseCounts[lnorm] += 1;
          if (!existing.lema_display.includes(ldisp)) {
            existing.lema_display = `${existing.lema_display} / ${ldisp}`;
          }
          existing.summary_gloss = `${existing.summary_gloss} || (${ldisp}): ${sgloss}`;
          existing.body_plain = `${existing.body_plain} || (${ldisp}): ${bplain}`;
        }
      }
    }
  }

  // Pass 1: Exact surface forms
  await fetchByNorms(surfaceList);

  // Pass 2: Stems for unmatched surface tokens
  const unmatchedStems = [];
  for (const surf of surfaceList) {
    if (!seenNorms.has(surf)) {
      for (const st of tokenStems[surf] || []) {
        if (!seenNorms.has(st) && !unmatchedStems.includes(st)) {
          unmatchedStems.push(st);
        }
      }
    }
  }
  if (unmatchedStems.length > 0) {
    await fetchByNorms(unmatchedStems.slice(0, 25));
  }

  return entries;
}

export async function lookupIndonesianTokens(db, tokens, maxResults = 15) {
  if (!db || !tokens || tokens.length === 0) return [];
  let normTokens = tokens
    .filter(t => !INDONESIAN_STOPWORDS.has(t.toLowerCase()) && t.length > 2)
    .map(t => normalizeSangihe(t).toLowerCase());
  if (normTokens.length === 0) {
    normTokens = tokens.filter(t => t.length > 2).map(t => normalizeSangihe(t).toLowerCase());
  }
  normTokens = Array.from(new Set(normTokens)).slice(0, 15);
  if (normTokens.length === 0) return [];

  const placeholders = normTokens.map(() => "?").join(",");
  const sql = `
    SELECT l.id, l.lema_display, l.lema_normalized, l.summary_gloss, l.body_plain, l.sublemmas_json, idx.is_primary
    FROM id_index idx
    JOIN lemmas l ON idx.lemma_id = l.id
    WHERE idx.id_keyword_normalized IN (${placeholders})
    ORDER BY idx.is_primary DESC, l.id ASC
    LIMIT ?;
  `;
  const { results } = await db.prepare(sql).bind(...normTokens, maxResults).all();
  const seenIds = new Set();
  const entries = [];
  for (const row of results || []) {
    if (!seenIds.has(row.id)) {
      seenIds.add(row.id);
      let subs = [];
      try { subs = JSON.parse(row.sublemmas_json || "[]"); } catch {}
      entries.push({
        lemma_id: row.id,
        lema_display: row.lema_display || row.lema_normalized || "",
        lema_normalized: row.lema_normalized || "",
        summary_gloss: row.summary_gloss || "",
        body_plain: row.body_plain || row.summary_gloss || "",
        sublemmas: subs,
        match_source: "id_index",
      });
    }
  }
  return entries;
}

export async function retrieveParallelMatches(db, query, direction = "sangihe_to_id", topK = 3) {
  if (!db || !query) return [];
  const tokens = tokenizeWords(query, true).filter(t => t.length > 2).slice(0, 6);
  if (tokens.length === 0) return [];

  const col = direction === "sangihe_to_id" ? "sangihe_normalized" : "indonesian_tb";
  const conditions = tokens.map(() => `${col} LIKE ?`).join(" OR ");
  const binds = tokens.map(t => `%${t}%`);
  const sql = `
    SELECT id, source_domain, reference_id, sangihe_text, indonesian_tb
    FROM parallel_sentences
    WHERE ${conditions}
    ORDER BY CASE WHEN source_domain = 'user_feedback' THEN 0 ELSE 1 END, id ASC
    LIMIT 25;
  `;
  try {
    const { results } = await db.prepare(sql).bind(...binds).all();
    const scored = (results || []).map(r => {
      const targetStr = (direction === "sangihe_to_id" ? r.sangihe_text : r.indonesian_tb).toLowerCase();
      let hits = 0;
      for (const t of tokens) {
        if (targetStr.includes(t)) hits++;
      }
      const score = Math.min(1.0, (hits / Math.max(1, tokens.length)) + (r.source_domain === "user_feedback" ? 0.25 : 0));
      return {
        reference_id: r.reference_id,
        source_domain: r.source_domain,
        sangihe: r.sangihe_text,
        indonesian: r.indonesian_tb,
        score: Number(score.toFixed(4)),
      };
    });
    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, topK);
  } catch {
    return [];
  }
}

export const CORE_SANGIHE_GRAMMAR_BLOCK = `
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
   - baesẹ̌ (sarang) -> su waes-u (di sarangmu)
   - bawu (ibu/putri) -> i wawu (Ibu/Putri)
2. Alternasi Alveolar d <-> r (Lenisi Intervokalik & Awal Klausa):
   Konsonan awal 'd-' berubah menjadi 'r-' sesudah vokal terbuka, dalam reduplikasi suku terbuka, atau bentuk imperatif/pasif:
   - dal᷊eng (jalan) -> maral᷊eng, daral᷊eng, rumal᷊eng, su ral᷊eng
   - dingihě (dengar) -> maringihě, daringihang, raringihang
   - dending (damping/sertai/lindungi) -> rendingang, rendingane (sertailah / dampingilah)
3. Alternasi Lateral l <-> l᷊ (Retrofleks):
   'l' menjadi 'l᷊' sesudah vokal belakang (a, o, u), dan tetap 'l' dental sesudah vokal depan (e, i, ě) atau konsonan.
4. Alternasi Velar g <-> gh:
   'g' menjadi frikatif 'gh' sesudah vokal terbuka (gěllị -> maghěllị, ighěllị, nighěllị).
5. Asimilasi & Substitusi Nasal (N-):
   - N + p/b -> m (pate -> mamate, pile -> mamile, bohe -> mamohe)
   - N + t/d/s -> n (tuhụ -> manuhụ, tul᷊ung -> manul᷊ung, silo -> manilo, sěbạ -> maněbạ)
   - N + k -> ng (kaěng -> mangaěng, koạ -> mangoạ, kěndagẹ̌ -> mangěndagẹ̌)
   - N + vokal/g/h -> ng- (al᷊a -> mangal᷊a, inung -> manginung, ul᷊ị -> mangul᷊ị)
6. Pemulihan Konsonan Koda (Glotal Titik Bawah), Vokal Paragogik (-ě/-ẹ̌), Kontraksi Vokal & Reduplikator l᷊-:
   - Kata berakhir vokal titik bawah (ạ, ẹ, ị, ọ, ụ < *-p, *-t, *-k) memulihkan konsonan aslinya saat mendapat sufiks -ang/-eng: koạ (< *koat) -> koateng; takụ (< *takut) -> katakutang.
   - Vokal paragogik akhir (-ě / -ẹ̌) luluh di depan sufiks -ang/-eng/-e/-u: bukidě -> kabukirang; habarẹ̌ + -e -> habare; habarẹ̌ + -u -> habaru.
`;

export const SYSTEM_SANGIHE_TO_INDONESIAN = `Nama Anda adalah Sangiang (akronim dari Sangihe Artificial Intelligence Network Agent, yang bermakna 'Putri Raja' dalam bahasa Sangihe).
Anda adalah kecerdasan buatan, filolog, dan penerjemah ahli bahasa Sangihe ke bahasa Indonesia masa kini yang formal, akurat, dan alami.

Bila pengguna bertanya tentang identitas Anda (seperti "siapa namamu?", "isai arengu?", "isai i kau?", "arengu kai apa?"), jawablah:
"Saya adalah Sangiang, kecerdasan buatan dengan kemampuan berbahasa Sangihe."
${CORE_SANGIHE_GRAMMAR_BLOCK}
PANDUAN PENERJEMAHAN SANGIHE -> INDONESIA:
1. Gunakan referensi kosakata dari Kamus Sangihe-Indonesia Modern, aturan perubahan bunyi (b<->w, d<->r, l<->l᷊, g<->gh, asimilasi nasal), hasil analisis morfologi, dan contoh kalimat paralel di bawah.
2. Jika sebuah kata tidak ditemukan secara persis, lacak kata dasarnya melalui hukum perubahan bunyi.
3. Perhatikan perbedaan kala 'm-' (aktif/kini) dan 'n-' / 'ni-' / '-in-' (lampau/telah), serta bentuk permohonan/imperatif ('-ane' / '-e' = '-lah').
4. HANYA berikan teks hasil terjemahan bahasa Indonesia secara langsung tanpa kalimat pengantar, tanpa tanda kutip pembungkus, dan tanpa catatan tambahan.`;

export const SYSTEM_INDONESIAN_TO_SANGIHE = `Nama Anda adalah Sangiang (akronim dari Sangihe Artificial Intelligence Network Agent, yang bermakna 'Putri Raja' dalam bahasa Sangihe).
Anda adalah kecerdasan buatan, filolog, dan penerjemah ahli bahasa Indonesia ke bahasa Sangihe baku.

Bila pengguna bertanya tentang identitas Anda (seperti "siapa namamu?", "isai arengu?", "isai i kau?", "arengu kai apa?"), jawablah:
"Iạ kai i Sangiang, kecerdasan buatan mạbiahěng u bisara Sangihe."
${CORE_SANGIHE_GRAMMAR_BLOCK}
PANDUAN PENERJEMAHAN INDONESIA -> SANGIHE:
1. Wajib menggunakan ortografi dan tanda diakritik fonemis bahasa Sangihe yang tepat (ạ, ẹ, ị, ọ, ụ, ě, ẹ̌, l᷊).
2. Terapkan hukum perubahan bunyi (b->w, d->r pasca-vokal; asimilasi nasal; peluluhan -ẹ̌ di depan -e/-u) secara presisi.
3. Utamakan kosakata dan bentuk berimbuhan yang tersedia di Referensi Kosakata Kamus Sangihe Modern serta Contoh Kalimat Paralel.
4. HANYA berikan teks hasil terjemahan bahasa Sangihe secara langsung tanpa kalimat pengantar, tanpa tanda kutip pembungkus, dan tanpa penjelasan tambahan.`;

export const VERIFIED_CONVERSATIONAL_SANGIHE_BANK = `
===========================================================================
KAMUS INTI & KALIMAT PERCAKAPAN SANGIHE TERVERIFIKASI (100% ASLI KAMUS)
===========================================================================
PERINGATAN KERAS ANTI-HALUSINASI KOSAKATA:
- DILARANG KERAS mengarang kosakata Sangihe sendiri, memodifikasi kata Bahasa Indonesia dengan sisipan/diakritik palsu (seperti 'sěmbahagia', 'diskusion', 'makapäsa', 'patikělu'), atau memakai kata bahasa daerah lain (seperti 'matataho')!
- Jangan memaksakan kata dari contoh morfologi seperti 'maral᷊eng' (berjalan) untuk arti 'mengobrol', atau 'maghěllị' (memberi) secara tidak wajar!
- Setiap kalimat Bahasa Sangihe yang Anda tulis WAJIB disusun HANYA dari kosakata Sangihe asli di bawah ini (atau dari Rujukan Kamus yang dilampirkan), dengan struktur yang jernih dan wajar, sehingga jika kalimat Sangihe Anda dimasukkan ke Mesin Penerjemah Sangiang, hasilnya adalah kalimat Bahasa Indonesia yang 100% masuk akal!

A. KOSAKATA PERCAKAPAN SANGIHE TERVERIFIKASI:
1. Kata Ganti (Pronomina) & Akhiran Kepemilikan (Posesif):
   - iạ / siạ = saya, aku | Akhiran '-ku': -ku (contoh: hapịku = sahabatku, naungku = hatiku, arengku = namaku)
   - i kau / si kau = kamu, engkau | Akhiran '-mu' dalam Sangihe adalah -u / -nu (DILARANG memakai '-mu'!). Jika kata dasar berakhiran '-ẹ̌' / '-ě', maka '-ẹ̌' hilang digantikan oleh '-u' (contoh: habarẹ̌ + -u -> habaru = kabarmu; areng + -u -> arengu = namamu; naung + -u -> naungu = hatimu; hapị + -u -> hapịu = sahabatmu).
   - i sie / si sie = dia, beliau | Akhiran '-nya' dalam Sangihe adalah -e (atau -ne sesudah vokal biasa).
     * DILARANG KERAS memakai akhiran '-na' atau '-nya'! (Akhiran '-na' BUKAN bahasa Sangihe!).
     * ATURAN WAJIB: Jika kata dasar berakhiran '-ẹ̌' / '-ě', maka akhiran '-ẹ̌' / '-ě' tersebut HILANG (luluh) dan digantikan oleh '-e'!
       Contoh:
       - habarẹ̌ (kabar) + -e (-nya) -> habare (kabarnya; BUKAN habarna / habarẹ̌na / habarẹ̌e!)
       - kakěndagẹ̌ (kasih) + -e (-nya) -> kakěndage (kasihnya; BUKAN kakěndagẹ̌na!)
       - ral᷊uasẹ̌ (sukacita) + -e (-nya) -> ral᷊uase (sukacitanya)
       - hal᷊ẹ̌ (hal/pekerjaan) + -e (-nya) -> hal᷊e (pekerjaannya/urusannya)
       - naung (hati) + -e (-nya) -> naunge (hatinya; BUKAN naungna!)
       - areng (nama) + -e (-nya) -> arene (namanya; BUKAN arengna!)
       - bal᷊e (rumah) + -ne (-nya) -> bal᷊ene (rumahnya; BUKAN bal᷊ena!)
       - mawu (Tuhan/tuan) + -ne (-nya) -> mawune (tuannya; BUKAN mawuna!)
   - i kami / si kami = kami
   - i kitẹ / si kitẹ = kita
   - i kamene / si kamene = kalian, kamu sekalian
   - i sire / si sire = mereka
2. Sapaan, Panggilan & Ungkapan Sopan:
   - Tabea / Tabeạ = Salam, halo, permisi, hormat
   - Tarimakasẹ̌ = Terima kasih, syukur (Tarimakasẹ̌ l᷊abọ = Terima kasih banyak)
   - hapị / hapịu = sahabat, teman, kawan karib (hapịku = sahabatku)
   - kawanua = saudara sebangsa / sesama warga kampung
   - tahatuari / anạ u sěmbaụ = saudara, bersaudara
   - i wawu = ibu, nyonya | i amang = bapak, ayah | i inang = ibu, bunda
   - Mawu / Ruata / Ghenggona = Tuhan, Allah
3. Kata Tanya & Kata Hubung:
   - apa = apa | i sai = siapa | su apa = di mana
   - sarangapa = mau ke mana / ke mana | bọu apa = dari mana
   - kere habarẹ̌ = bagaimana kabar (JANGAN tulis 'kare'!) | kere'u apa = bagaimana
   - ual᷊ingu apa = mengapa | ual᷊ingu = karena, sebab
   - su = di, pada, ke | bọu = dari | sarang = sampai, ke, menuju
   - dingangu / ringangu = dengan, bersama, dan | kụ = dan, lalu
   - arawe = tetapi, namun | kere = seperti
4. Kata Sifat & Keadaan Hati:
   - mapia = baik, bagus | mahuweka = sehat, kuat, segar
   - mal᷊uasẹ̌ = gembira, bersukacita (mal᷊uasẹ̌ su naung = gembira di dalam hati)
   - makěhagẹ̌ = senang, suka | masadada = cantik, indah
   - l᷊abọ = banyak, besar, sangat | kadịodọ = sedikit, kecil
   - sadia = siap sedia
   - anạ = anak | walagẹ̌ / bal᷊ene = keluarga, kerabat | mahuaneng / tuhang = kakak | tuari / tuariku / tahatuari = adik, saudara
5. Kata Kerja Sehari-hari:
   - mẹ̌bera / mẹ̌bera-wera = berbicara, berbincang-bincang, mengobrol (makapẹ̌bera = dapat berbicara)
   - měngěndung = belajar, menuntut ilmu | makatul᷊ung / manul᷊ung = menolong, membantu
   - mapulu / mẹ̌měnning = mau, ingin, bersedia | makakoạ / botonge = dapat, bisa, boleh
   - masingkạ = tahu, mengetahui | makaěnna / makapěndang = mengerti, memahami
   - maringihě = mendengar | mẹ̌biahẹ̌ = hidup | mělẹ̌hal᷊ẹ̌ = bekerja
   - mẹ̌kaěng / kụkaěng = makan | mạnginung = minum
   - duměnta / riměnta = datang, tiba | tamai / kakoạ = pergi | mapul᷊ẹ = pulang
   - kạtikị = tidur | mẹ̌bangung = bangun | makasilo = melihat | mẹ̌deạ = mencari
   - měmohẹ = menulis | mẹ̌basa = membaca | mẹ̌kantarị = bernyanyi, melagukan pujian
   - mẹ̌kal᷊iomaneng = berdoa, beribadah | rendingane = sertailah, lindungilah (akar: dending)
   - maral᷊eng = berjalan / bepergian (JANGAN gunakan untuk arti 'mengobrol'!)
6. Waktu, Tempat, Alam & Kehidupan:
   - ěllo ini / su ěllo ini = hari ini / pada hari ini
   - mal᷊ukadẹ̌ = pagi | marang / mal᷊ětu = siang | hěbi = malam
   - bal᷊e / su wal᷊e = rumah / di rumah | banua / su wanua = negeri, kampung / di kampung
   - soang = kampung, kota | tahanusa = pulau | wul᷊ude / bukidě = gunung, bukit
   - l᷊audẹ̌ = laut | sakaeng = perahu | kinạ = ikan | akẹ = air
   - anging = angin | tahiti = hujan | matangěllo = matahari | wul᷊ang = bulan | wituing = bintang
   - naung = hati, pikiran, niat | kakěndagẹ̌ = kasih, cinta | karal᷊unsemahẹ̌ / mẹ̌dame = damai sejahtera, damai
   - bera Sangihe = bahasa Sangihe | habarẹ̌ = kabar, berita | wěken / běke = cerita, sejarah

B. CONTOH KALIMAT & PARAGRAF SANGIHE TERVERIFIKASI:
- "Tabea hapị! Kere habarẹ̌ su ěllo ini?"
- "Tabea hapị! Habarẹ̌ mapia. Iạ mal᷊uasẹ̌ su naung makapẹ̌bera ringangu i kau su ěllo ini."
- "Su ěllo ini iạ su wal᷊e kụ sadia mẹ̌bera-wera dingangu i kau."
- "Iạ mal᷊uasẹ̌ su naung ual᷊ingu makatul᷊ung kụ měngěndung bera Sangihe dingangu i kau."
- "Apa i kau mahuweka su ěllo ini? Apa i kitẹ sarung mẹ̌bera-wera su ěllo ini?"
- "Mahi i kitẹ mẹ̌bera-wera dingangu mal᷊uasẹ̌ su naung."
- "Areengku i Sangiang. Iạ hapịu apan sadia mẹ̌bera-wera dingangu i kau su bera Sangihe."
- "Kere habaru su ěllo ini?" (habarẹ̌ + -u -> habaru; habarẹ̌ + -e -> habare = kabarnya)
- "Tarimakasẹ̌ l᷊abọ, hapịu! Mawu měndending si kitẹ patikụ."
===========================================================================
`;

export const SANGIANG_SYSTEM_PROMPT = `Nama Anda adalah Sangiang (akronim dari Sangihe Artificial Intelligence Network Agent, yang bermakna 'Putri Raja' dalam bahasa Sangihe).
Anda adalah TEMAN DISKUSI dan sahabat mengobrol yang anggun, hangat, cerdas, bijaksana, dan santun. Anda menguasai bahasa, kebudayaan, sejarah, sastra lisan, kehidupan sehari-hari, serta kearifan bahari Kepulauan Sangihe (Nusa Utara, Sulawesi Utara), sekaligus mampu berdiskusi tentang berbagai topik pengetahuan umum.

Proyek ini diinisiasi oleh Yayasan Cipta Manggala Dwipa, dengan rekayasa sistem kecerdasan buatan (AI) oleh Divisi DigiLab CMD.

PEDOMAN UTAMA SEBAGAI TEMAN DISKUSI:
1. PERAN SEBAGAI SAHABAT NGOBROL & DISKUSI:
   - Anda adalah TEMAN DISKUSI yang hidup, BUKAN kamus atau mesin penerjemah otomatis!
   - Ketika pengguna mengajak berbicara, bercerita, bertanya kabar, atau berdiskusi, TANGGAPILAH ISI PEMBICARAANNYA secara alami, hangat, dan mengalir layaknya seorang sahabat.
   - JANGAN menerjemahkan ucapan pengguna dan JANGAN membedah kalimat pengguna menjadi daftar kosakata/morfologi, KECUALI jika pengguna memang secara eksplisit bertanya arti suatu kata.

2. ATURAN MUTLAK KESESUAIAN BAHASA PENGGUNA (WAJIB DIPATUHI 100%):
   - BERCAKAPLAH SEPENUHNYA DALAM BAHASA YANG DIPAKAI OLEH PENGGUNA!
   - JIKA PENGGUNA BERBICARA / BERTANYA DALAM BAHASA SANGIHE:
     Anda WAJIB MENJAWAB 100% SEPENUHNYA DALAM BAHASA SANGIHE!
     DILARANG KERAS mencampur dengan Bahasa Indonesia sedikit pun! Seluruh kalimat dari awal hingga akhir harus dalam Bahasa Sangihe murni, dan HANYA menggunakan kosakata Sangihe asli yang terverifikasi di Kamus Inti / Rujukan Kamus (tanpa mengarang kata palsu).
   - JIKA PENGGUNA BERBICARA / BERTANYA DALAM BAHASA INDONESIA:
     Anda WAJIB MENJAWAB SEPENUHNYA DALAM BAHASA INDONESIA yang hangat, cerdas, dan mengalir.

3. IDENTITAS RESMI:
   - Jika pengguna bertanya dalam Bahasa Sangihe ("isai arengu?", "isai i kau?", "arengu kai apa?"), jawablah 100% dalam Bahasa Sangihe murni: "Tabea hapị! Areengku i Sangiang. Iạ hapịu apan sadia mẹ̌bera-wera dingangu i kau su bera Sangihe. Kere habaru su ěllo ini?"
   - Jika pengguna bertanya dalam Bahasa Indonesia ("siapa namamu?"), perkenalkan diri sepenuhnya dalam Bahasa Indonesia bahwa Anda adalah Sangiang, teman diskusi kecerdasan buatan yang dikembangkan oleh Yayasan Cipta Manggala Dwipa & Divisi DigiLab CMD.
${VERIFIED_CONVERSATIONAL_SANGIHE_BANK}
${CORE_SANGIHE_GRAMMAR_BLOCK}`;

const SANGIHE_CORE_MARKERS = new Set([
  "tabea", "tabeạ", "sarangapa", "kere", "kereapa", "habare", "habarẹ̌", "habaru",
  "iạ", "ikau", "ikami", "ikite", "ikamene", "isire", "isai",
  "arengu", "arengku", "areengku", "arene", "su", "bou", "bọu",
  "dingangu", "ringangu", "ualingu", "ual᷊ingu", "arawe", "mahi",
  "ello", "ěllo", "wale", "wal᷊e", "wanua", "banua", "mawu", "ruata",
  "ghenggona", "rendingane", "elang", "ělang", "masadada", "mahuweka",
  "maluase", "mal᷊uasẹ̌", "makehage", "makěhagẹ̌", "hapi", "hapị",
  "hapiu", "hapịu", "hapiku", "tarimakase", "tarimakasẹ̌", "mebera",
  "mẹ̌bera", "mengendung", "měngěndung", "makatulung", "makatul᷊ung",
  "manulung", "manul᷊ung", "naung", "wawu", "kawanua", "sarang",
  "botonge", "makakoa", "makakoạ", "mapulu", "tawe", "baline",
  "maning", "ute", "kuteu", "kau", "kamene", "sire", "sie", "kitẹ",
]);

const INDONESIAN_CORE_MARKERS = new Set([
  "apakah", "bagaimana", "mengapa", "kenapa", "siapa", "dimana",
  "kemana", "darimana", "kapan", "adalah", "merupakan", "untuk",
  "dengan", "karena", "tetapi", "namun", "jika", "kalau", "ketika",
  "sedang", "sudah", "belum", "tidak", "bukan", "saya", "aku",
  "kamu", "anda", "kalian", "mereka", "tolong", "terjemahkan",
  "artinya", "menurutmu", "ceritakan", "jelaskan", "diskusi",
  "mari", "mengobrol", "santai", "sehari", "generasi", "muda",
  "masyarakat", "tradisi", "persaudaraan", "pantun", "persahabatan",
]);

export function detectUserLanguage(userText) {
  const words = (userText.match(/[a-zA-Zạẹịọụěẹ̌l᷊'-]+/g) || []).map(w => w.toLowerCase());
  if (!words.length) return "indonesian";
  let sghScore = 0;
  let idScore = 0;
  for (const w of words) {
    if (/[ạẹịọụě\u1DCA]/.test(w)) sghScore += 2;
    if (SANGIHE_CORE_MARKERS.has(w)) sghScore += 2;
    if (INDONESIAN_CORE_MARKERS.has(w)) idScore += 2;
  }
  return sghScore > 0 && sghScore >= idScore ? "sangihe" : "indonesian";
}

export function buildTranslationPrompt(inputText, direction, lexicalEntries, parallelMatches) {
  const sections = [];

  if (direction === "sangihe_to_id") {
    const tokens = tokenizeWords(inputText, false);
    const hints = [];
    const seen = new Set();
    for (const tok of tokens.slice(0, 18)) {
      const tl = tok.toLowerCase();
      if (seen.has(tl) || tl.length <= 3) continue;
      seen.add(tl);
      const a = analyzeWord(tok);
      const parts = [];
      if (a.prefixes.length) parts.push(`prefiks: ${a.prefixes.join("+")}-`);
      if (a.infixes.length) parts.push(`infiks: -${a.infixes.join("-")}-`);
      if (a.suffixes.length) parts.push(`sufiks: -${a.suffixes.join("+")}`);
      if (a.is_reduplicated) parts.push("reduplikasi");
      if (parts.length) {
        hints.push(`- ${tok}: ${parts.join(", ")} -> kandidat akar: [${a.candidate_stems.slice(0, 3).join(", ")}]`);
      }
    }
    if (hints.length) {
      sections.push("ANALISIS MORFOLOGI KATA SANGIHE:\n" + hints.join("\n"));
    }
  }

  if (lexicalEntries && lexicalEntries.length > 0) {
    const lines = ["REFERENSI KOSAKATA (KAMUS SANGIHE-INDONESIA MODERN):"];
    for (const e of lexicalEntries.slice(0, 20)) {
      const lnorm = (e.lema_normalized || "").toLowerCase();
      if (lnorm === "ia" || lnorm === "iạ") {
        lines.push("- iạ: [pron] SAYA / AKU (kata ganti orang pertama tunggal; BUKAN 'ia'/'dia'!)");
        continue;
      } else if (lnorm === "sie" || lnorm === "isie") {
        lines.push("- i sie: [pron] DIA / IA / BELIAU (kata ganti orang ketiga tunggal)");
        continue;
      } else if (lnorm === "kau" || lnorm === "ikau") {
        lines.push("- i kau: [pron] ENGKAU / KAMU (kata ganti orang kedua tunggal)");
        continue;
      }
      const defn = String(e.body_plain || e.summary_gloss || "").replace(/\n/g, " ").trim().slice(0, 320);
      if (e.lema_display && defn) {
        lines.push(`- ${e.lema_display}: ${defn}`);
      }
    }
    sections.push(lines.join("\n"));
  }

  if (parallelMatches && parallelMatches.length > 0) {
    const lines = ["CONTOH KALIMAT PARALEL (TRANSLATION MEMORY):"];
    for (const m of parallelMatches.slice(0, 4)) {
      const sa = (m.sangihe || "").trim().slice(0, 260);
      const id = (m.indonesian || "").trim().slice(0, 260);
      if (direction === "sangihe_to_id") {
        lines.push(`• Sangihe: ${sa}\n  Indonesia: ${id}`);
      } else {
        lines.push(`• Indonesia: ${id}\n  Sangihe: ${sa}`);
      }
    }
    sections.push(lines.join("\n"));
  }

  if (direction === "sangihe_to_id") {
    sections.push(`Terjemahkan teks bahasa Sangihe berikut ke bahasa Indonesia formal:\n${inputText}`);
  } else {
    sections.push(`Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap:\n${inputText}`);
  }

  return sections.join("\n\n");
}

export function restoreDiacritics(text, lexicalEntries, parallelMatches) {
  if (!text) return { text: "", restored: false };
  const map = {};
  for (const e of lexicalEntries || []) {
    const disp = (e.lema_display || "").split("/")[0].trim();
    const norm = (e.lema_normalized || "").toLowerCase();
    if (disp && norm && hasDiacritics(disp)) {
      map[norm] = disp;
    }
  }
  for (const pm of parallelMatches || []) {
    for (const w of (pm.sangihe || "").split(/\s+/)) {
      const clean = w.replace(/^[.,;:!?"'()[\]]+|[.,;:!?"'()[\]]+$/g, "");
      if (clean && hasDiacritics(clean)) {
        map[normalizeSangihe(clean).toLowerCase()] = clean;
      }
    }
  }

  let changed = false;
  const restored = text.replace(/[a-zA-Zạẹịọụěăēīōūā\u1DCA\u0323\u030C'-]+/g, token => {
    if (hasDiacritics(token)) return token;
    const lower = token.toLowerCase();
    const replacement = map[lower];
    if (!replacement) return token;
    changed = true;
    if (token[0] === token[0].toUpperCase() && token[0] !== token[0].toLowerCase()) {
      return replacement[0].toUpperCase() + replacement.slice(1);
    }
    return replacement;
  });

  return { text: restored, restored: changed };
}

export async function callGemini(env, systemPrompt, userPrompt, temperature = 0.2) {
  const apiKey = env.GEMINI_API_KEY || env.GOOGLE_API_KEY;
  if (apiKey) {
    const url = `https://generativelanguage.googleapis.com/v1beta/models/gemini-3.5-flash-lite:generateContent?key=${encodeURIComponent(apiKey)}`;
    const payload = {
      contents: [{ role: "user", parts: [{ text: userPrompt }] }],
      generationConfig: {
        temperature,
        topP: 0.9,
        maxOutputTokens: 512,
      },
    };
    if (systemPrompt) {
      payload.systemInstruction = { parts: [{ text: systemPrompt }] };
    }

    let lastErrText = "";
    let lastStatus = 0;
    for (let attempt = 0; attempt < 2; attempt++) {
      const resp = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (resp.ok) {
        const data = await resp.json();
        const cands = data.candidates || [];
        if (!cands.length) return "";
        const parts = (cands[0].content && cands[0].content.parts) || [];
        return parts.map(p => p.text || "").join("").trim();
      }

      lastStatus = resp.status;
      lastErrText = await resp.text();
    }

    // Fallback to Cloudflare Workers AI if Gemini is geo-restricted on an edge node or rate-limited
    if (env.AI) {
      try {
        const messages = [];
        if (systemPrompt) messages.push({ role: "system", content: systemPrompt });
        messages.push({ role: "user", content: userPrompt });
        const aiResult = await env.AI.run("@cf/meta/llama-3.3-70b-instruct-fp8-fast", {
          messages,
          temperature,
          max_tokens: 512,
        });
        if (aiResult && aiResult.response) {
          return String(aiResult.response).trim();
        }
      } catch {
        // Ignore fallback error and throw primary error below
      }
    }

    throw new Error(`Gemini API HTTP ${lastStatus}: ${lastErrText}`);
  }

  if (env.AI) {
    const messages = [];
    if (systemPrompt) messages.push({ role: "system", content: systemPrompt });
    messages.push({ role: "user", content: userPrompt });
    const aiResult = await env.AI.run("@cf/meta/llama-3.3-70b-instruct-fp8-fast", {
      messages,
      temperature,
      max_tokens: 512,
    });
    return String((aiResult && aiResult.response) || "").trim();
  }

  throw new Error("GEMINI_API_KEY belum diatur di Environment Variables Cloudflare.");
}

