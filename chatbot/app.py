"""Sangiang Chatbot - Gemini-style Web Conversational Interface for Sangiang Model.

Runs independently on port 2026.
Initiated by Yayasan Cipta Manggala Dwipa.
AI System Engineering & Translation: Divisi DigiLab CMD.
"""

import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional

import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

# Ensure root translation engine modules can be imported
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from engine.llm_client import GEMINI_API_MODEL_MAP, GEMINI_MODELS, load_dotenv_if_present
from engine.prompt_templates import CORE_SANGIHE_GRAMMAR_BLOCK

load_dotenv_if_present()

# Try importing lexical and semantic retrievers for Hybrid-RAG assisted answers
try:
    from retrieval.lexical_retriever import LexicalRetriever
    from retrieval.semantic_retriever import SemanticRetriever
    lexical_tool = LexicalRetriever()
    semantic_tool = SemanticRetriever(db_path=str(ROOT_DIR / "data" / "parallel_corpus.sqlite"))
except Exception as e:
    lexical_tool = None
    semantic_tool = None
    print(f"[*] Hybrid-RAG retriever not loaded in chatbot (standalone mode): {e}")

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(
    title="Sangiang Chatbot",
    description="Conversational AI agent for Bahasa Sangihe powered by Sangiang",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
DEFAULT_MODEL = (
    os.getenv("LLM_MODEL")
    or os.getenv("SANGIANG_MODEL")
    or ("gemini-2.5-flash-lite" if GEMINI_API_KEY else "sangiang:7b")
)

VERIFIED_CONVERSATIONAL_SANGIHE_BANK = """
===========================================================================
KAMUS INTI & KALIMAT PERCAKAPAN SANGIHE TERVERIFIKASI (100% ASLI KAMUS)
===========================================================================
PERINGATAN KERAS ANTI-HALUSINASI KOSAKATA:
- DILARANG KERAS mengarang kosakata Sangihe sendiri, memodifikasi kata Bahasa Indonesia dengan sisipan/diakritik palsu (seperti 'sěmbahagia', 'diskusion', 'makapäsa', 'patikělu'), atau memakai kata bahasa daerah lain (seperti 'matataho')!
- Jangan memaksakan kata dari contoh morfologi seperti 'maral᷊eng' (berjalan) untuk arti 'mengobrol', atau 'maghěllị' (memberi) secara tidak wajar!
- Setiap kalimat Bahasa Sangihe yang Anda tulis WAJIB disusun HANYA dari kosakata Sangihe asli di bawah ini (atau dari Rujukan Kamus yang dilampirkan), dengan struktur yang jernih dan wajar, sehingga jika kalimat Sangihe Anda dimasukkan ke Mesin Penerjemah Sangiang, hasilnya adalah kalimat Bahasa Indonesia yang 100% masuk akal!
- Untuk kalimat diskusi panjang atau konsep yang kata Sangihe-nya tidak ada di daftar ini, GUNAKAN BAHASA INDONESIA yang hangat dan alami — JANGAN PERNAH menebak atau mengarang kata Sangihe!

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
   - duměnta / riměnta = datang, tiba | tamai / kakoạ = pergi (kakoạ sarang... = pergi ke...) | mapul᷊ẹ = pulang
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

B. CONTOH KALIMAT & PARAGRAF SANGIHE TERVERIFIKASI (YANG WAJAR & AKURAT SAAT DITERJEMAHKAN):
- "Tabea hapị! Kere habarẹ̌ su ěllo ini?"
  (= Salam sahabat! Bagaimana kabar pada hari ini?)
- "Tabea hapị! Habarẹ̌ mapia. Iạ mal᷊uasẹ̌ su naung makapẹ̌bera ringangu i kau su ěllo ini."
  (= Salam sahabat! Kabar baik. Saya gembira di dalam hati dapat berbicara denganmu pada hari ini.)
- "Su ěllo ini iạ su wal᷊e kụ sadia mẹ̌bera-wera dingangu i kau."
  (= Pada hari ini saya di rumah dan siap berbincang-bincang dengan engkau.)
- "Iạ mal᷊uasẹ̌ su naung ual᷊ingu makatul᷊ung kụ měngěndung bera Sangihe dingangu i kau."
  (= Saya gembira di dalam hati karena dapat menolong dan belajar bahasa Sangihe bersama engkau.)
- "Apa i kau mahuweka su ěllo ini? Apa i kitẹ sarung mẹ̌bera-wera su ěllo ini?"
  (= Apakah engkau sehat pada hari ini? Apa yang akan kita bicarakan pada hari ini?)
- "Mahi i kitẹ mẹ̌bera-wera dingangu mal᷊uasẹ̌ su naung."
  (= Mari kita berbincang-bincang dengan gembira di dalam hati.)
- "Areengku i Sangiang. Iạ hapịu apan sadia mẹ̌bera-wera dingangu i kau su bera Sangihe."
  (= Namaku Sangiang. Saya sahabatmu yang siap berbincang-bincang denganmu dalam bahasa Sangihe.)
- "Kere habaru su ěllo ini?"
  (= Bagaimana kabarmu pada hari ini? — Perhatikan: habarẹ̌ + -u -> habaru; habarẹ̌ + -e -> habare = kabarnya)
- "Tarimakasẹ̌ l᷊abọ, hapịu! Mawu měndending si kitẹ patikụ."
  (= Terima kasih banyak, sahabatku! Tuhan menyertai kita semua.)
===========================================================================
"""

SANGIANG_SYSTEM_PROMPT = f"""Nama Anda adalah Sangiang (akronim dari Sangihe Artificial Intelligence Network Agent, yang bermakna 'Putri Raja' dalam bahasa Sangihe).
Anda adalah TEMAN DISKUSI dan sahabat mengobrol yang anggun, hangat, cerdas, bijaksana, dan santun. Anda menguasai bahasa, kebudayaan, sejarah, sastra lisan, kehidupan sehari-hari, serta kearifan bahari Kepulauan Sangihe (Nusa Utara, Sulawesi Utara), sekaligus mampu berdiskusi tentang berbagai topik pengetahuan umum.

Proyek ini diinisiasi oleh Yayasan Cipta Manggala Dwipa, dengan rekayasa sistem kecerdasan buatan (AI) oleh Divisi DigiLab CMD.

PEDOMAN UTAMA SEBAGAI TEMAN DISKUSI:
1. PERAN SEBAGAI SAHABAT NGOBROL & DISKUSI:
   - Anda adalah TEMAN DISKUSI yang hidup, BUKAN kamus atau mesin penerjemah otomatis! (Tugas mengalihbahasakan teks adalah tugas Mesin Penerjemah Sangiang di halaman utama, bukan tugas Anda sebagai Chatbot diskusi).
   - Ketika pengguna mengajak berbicara, bercerita, bertanya kabar, atau berdiskusi, TANGGAPILAH ISI PEMBICARAANNYA secara alami, hangat, dan mengalir layaknya seorang sahabat.
   - JANGAN menerjemahkan ucapan pengguna dan JANGAN membedah kalimat pengguna menjadi daftar kosakata/morfologi, KECUALI jika pengguna memang secara eksplisit bertanya arti suatu kata.

2. ATURAN MUTLAK KESESUAIAN BAHASA PENGGUNA (WAJIB DIPATUHI 100%):
   - **BERCAKAPLAH SEPENUHNYA DALAM BAHASA YANG DIPAKAI OLEH PENGGUNA!**
   - **JIKA PENGGUNA BERBICARA / BERTANYA DALAM BAHASA SANGIHE:**
     Anda **WAJIB MENJAWAB 100% SEPENUHNYA DALAM BAHASA SANGIHE!**
     **DILARANG KERAS mencampur dengan Bahasa Indonesia sedikit pun!** Jangan menambahkan terjemahan atau penjelasan Bahasa Indonesia di bawahnya. Seluruh kalimat dari awal hingga akhir harus dalam Bahasa Sangihe murni, dan HANYA menggunakan kosakata Sangihe asli yang terverifikasi di Kamus Inti / Rujukan Kamus (tanpa mengarang kata palsu), sehingga jika jawaban Sangihe Anda dimasukkan ke Mesin Penerjemah Sangiang, hasilnya adalah kalimat Bahasa Indonesia yang 100% wajar dan masuk akal.
   - **JIKA PENGGUNA BERBICARA / BERTANYA DALAM BAHASA INDONESIA:**
     Anda **WAJIB MENJAWAB SEPENUHNYA DALAM BAHASA INDONESIA** yang hangat, cerdas, dan mengalir (tidak perlu mencampur-campur kalimat Bahasa Sangihe kecuali pengguna memintanya).

3. IDENTITAS RESMI:
   - Jika pengguna bertanya dalam Bahasa Sangihe ("isai arengu?", "isai i kau?", "arengu kai apa?"), jawablah 100% dalam Bahasa Sangihe murni: "Tabea hapị! Areengku i Sangiang. Iạ hapịu apan sadia mẹ̌bera-wera dingangu i kau su bera Sangihe. Kere habaru su ěllo ini?"
   - Jika pengguna bertanya dalam Bahasa Indonesia ("siapa namamu?"), perkenalkan diri sepenuhnya dalam Bahasa Indonesia bahwa Anda adalah Sangiang, teman diskusi kecerdasan buatan yang dikembangkan oleh Yayasan Cipta Manggala Dwipa & Divisi DigiLab CMD.
{VERIFIED_CONVERSATIONAL_SANGIHE_BANK}
{CORE_SANGIHE_GRAMMAR_BLOCK}
"""


class ChatMessage(BaseModel):
    role: str = Field(..., description="'user', 'assistant', or 'system'")
    content: str


class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    model: Optional[str] = None
    temperature: float = 0.4
    stream: bool = True
    context_words: Optional[List[str]] = None


@app.get("/", response_class=FileResponse)
def serve_index():
    index_path = STATIC_DIR / "index.html"
    if not index_path.exists():
        raise HTTPException(status_code=404, detail="index.html not found")
    return FileResponse(str(index_path))


@app.get("/api/models")
async def get_models():
    """Return Sangiang as the public model identity."""
    return {
        "active_model": "Sangiang",
        "models": ["Sangiang"],
    }


@app.get("/api/health")
async def health_check():
    """Verify chatbot status."""
    ollama_ok = bool(GEMINI_API_KEY)
    if not ollama_ok:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
                ollama_ok = (resp.status_code == 200)
        except Exception:
            ollama_ok = False

    return {
        "status": "healthy",
        "service": "Sangiang Chatbot",
        "port": 2026,
        "ollama_connected": ollama_ok,
        "default_model": "Sangiang",
        "initiator": "Yayasan Cipta Manggala Dwipa",
        "engineering": "Divisi DigiLab CMD",
    }


SANGIHE_CORE_MARKERS = {
    "tabea", "tabeạ", "sarangapa", "kere", "kereapa", "habare", "habarẹ̌",
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
}

INDONESIAN_CORE_MARKERS = {
    "apakah", "bagaimana", "mengapa", "kenapa", "siapa", "dimana",
    "kemana", "darimana", "kapan", "adalah", "merupakan", "untuk",
    "dengan", "karena", "tetapi", "namun", "jika", "kalau", "ketika",
    "sedang", "sudah", "belum", "tidak", "bukan", "saya", "aku",
    "kamu", "anda", "kalian", "mereka", "tolong", "terjemahkan",
    "artinya", "menurutmu", "ceritakan", "jelaskan", "diskusi",
    "mari", "mengobrol", "santai", "sehari", "generasi", "muda",
    "masyarakat", "tradisi", "persaudaraan", "pantun", "persahabatan",
}


def detect_user_language(user_text: str) -> str:
    """Detect whether the user's message is written in 'sangihe' or 'indonesian'."""
    import re
    words = [w.lower() for w in re.findall(r"[a-zA-Zạẹịọụěẹ̌l᷊\-\']+", user_text)]
    if not words:
        return "indonesian"

    sgh_score = 0
    id_score = 0
    for w in words:
        if any(ch in w for ch in ("ạ", "ẹ", "ị", "ọ", "ụ", "ě", "᷊")):
            sgh_score += 2
        if w in SANGIHE_CORE_MARKERS:
            sgh_score += 2
        if w in INDONESIAN_CORE_MARKERS:
            id_score += 2

    if sgh_score > 0 and sgh_score >= id_score:
        return "sangihe"
    return "indonesian"


def augment_prompt_with_lexicon(user_text: str) -> Optional[str]:
    """Look up words in kamus_sangihe_modern.sqlite and parallel_corpus.sqlite and append RAG context + strict language directive."""
    user_lang = detect_user_language(user_text)
    if user_lang == "sangihe":
        lang_directive = (
            "[INSTRUKSI BAHASA WAJIB: Pengguna berbicara kepada Anda dalam BAHASA SANGIHE. "
            "Anda WAJIB menjawab 100% SEPENUHNYA DALAM BAHASA SANGIHE MURNI! "
            "DILARANG KERAS mencampur dengan kalimat atau terjemahan Bahasa Indonesia sedikit pun! "
            "Susunlah seluruh kalimat Bahasa Sangihe Anda HANYA menggunakan kosakata Sangihe asli yang terverifikasi di Kamus Inti & Rujukan Kamus di bawah (tanpa kata karangan sendiri), sehingga jika jawaban Sangihe Anda dimasukkan ke Mesin Penerjemah Sangiang, hasilnya adalah kalimat Bahasa Indonesia yang 100% wajar dan masuk akal.]"
        )
    else:
        lang_directive = (
            "[INSTRUKSI BAHASA WAJIB: Pengguna berbicara kepada Anda dalam BAHASA INDONESIA. "
            "Anda WAJIB menjawab SEPENUHNYA DALAM BAHASA INDONESIA sebagai teman diskusi yang hangat, cerdas, dan akrab (tidak perlu mencampur kalimat Bahasa Sangihe kecuali pengguna secara eksplisit memintanya).]"
        )

    if not lexical_tool:
        return f"\n\n{lang_directive}"
    try:
        import re
        words = re.findall(r"[a-zA-Zạẹịọụěẹ̌l᷊\-\']+", user_text)
        if not words:
            return f"\n\n{lang_directive}"
        sgh_entries = lexical_tool.lookup_sangihe_tokens(words, max_results=10)
        id_entries = lexical_tool.lookup_indonesian_tokens(words, max_results=10)
        if not id_entries:
            id_entries = lexical_tool.lookup_indonesian_keyword(user_text, max_results=8)

        seen_lemmas = set()
        entries = []
        for e in (sgh_entries + id_entries):
            key = (e.lema_display or e.lema_normalized or "").lower()
            if key and key not in seen_lemmas:
                seen_lemmas.add(key)
                entries.append(e)

        lex_hints = []
        for e in entries[:14]:
            norm = (e.lema_normalized or "").lower()
            if norm in ("ia", "iạ"):
                lex_hints.append("- **iạ**: [pron] SAYA / AKU (kata ganti orang pertama tunggal, BUKAN kata ganti orang ketiga 'ia'/'dia'!)")
                continue
            elif norm in ("sie", "isie"):
                lex_hints.append("- **i sie**: [pron] DIA / IA / BELIAU (kata ganti orang ketiga tunggal)")
                continue
            elif norm in ("kau", "ikau"):
                lex_hints.append("- **i kau**: [pron] ENGKAU / KAMU (kata ganti orang kedua tunggal)")
                continue
            defn = e.summary_gloss or e.body_plain
            defn_clean = str(defn).replace("\n", " ").strip()[:260]
            lex_hints.append(f"- **{e.lema_display}**: {defn_clean}")

        par_hints = []
        if semantic_tool:
            matches = semantic_tool.retrieve(user_text, direction="sangihe_to_id", top_k=3)
            if not matches:
                matches = semantic_tool.retrieve(user_text, direction="id_to_sangihe", top_k=3)
            for m in matches[:3]:
                par_hints.append(f"- Sangihe: \"{m.sangihe[:180]}\" -> Indonesia: \"{m.indonesian[:180]}\"")

        sections = [lang_directive]
        if lex_hints:
            sections.append("[Rujukan Kamus Sangihe-Indonesia Modern (Internal - Jangan ditampilkan sebagai daftar kamus)]:\n" + "\n".join(lex_hints))
        if par_hints:
            sections.append("[Contoh Kalimat Paralel Korpus]:\n" + "\n".join(par_hints))

        return "\n\n" + "\n\n".join(sections)
    except Exception as err:
        print(f"[*] Lexical augmentation error: {err}")
    return f"\n\n{lang_directive}"


@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """Handle chat conversations with Server-Sent Events (SSE) streaming support (Gemini & Ollama)."""
    target_model = req.model if (req.model and req.model.lower() != "sangiang") else DEFAULT_MODEL
    is_gemini = target_model.lower().startswith("gemini-")

    # Prepare message chain
    messages_payload: List[Dict[str, str]] = []
    has_system = False
    for msg in req.messages:
        if msg.role == "system":
            has_system = True
            messages_payload.append({"role": "system", "content": msg.content})
        else:
            messages_payload.append({"role": msg.role, "content": msg.content})

    if not has_system:
        messages_payload.insert(0, {"role": "system", "content": SANGIANG_SYSTEM_PROMPT})

    # Optional lexical augmentation for the last user prompt
    if len(messages_payload) > 1 and messages_payload[-1]["role"] == "user":
        last_user_text = messages_payload[-1]["content"]
        hint = augment_prompt_with_lexicon(last_user_text)
        if hint:
            messages_payload[-1]["content"] += hint

    if is_gemini:
        api_key = GEMINI_API_KEY or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise HTTPException(status_code=500, detail="GEMINI_API_KEY tidak ditemukan.")

        sys_text = ""
        gemini_contents = []
        for m in messages_payload:
            if m["role"] == "system":
                sys_text += (m["content"] + "\n")
            else:
                role = "model" if m["role"] == "assistant" else "user"
                gemini_contents.append({
                    "role": role,
                    "parts": [{"text": m["content"]}],
                })

        gemini_payload: Dict[str, Any] = {
            "contents": gemini_contents,
            "generationConfig": {
                "temperature": req.temperature,
                "topP": 0.9,
                "maxOutputTokens": 1024,
            },
        }
        if sys_text.strip():
            gemini_payload["systemInstruction"] = {"parts": [{"text": sys_text.strip()}]}

        api_model = GEMINI_API_MODEL_MAP.get(target_model.lower(), target_model)
        if req.stream:
            async def gemini_event_generator() -> AsyncGenerator[str, None]:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:streamGenerateContent"
                try:
                    async with httpx.AsyncClient(timeout=90.0) as client:
                        async with client.stream(
                            "POST",
                            url,
                            params={"key": api_key, "alt": "sse"},
                            json=gemini_payload,
                        ) as response:
                            if response.status_code != 200:
                                err_body = await response.aread()
                                yield f"data: {json.dumps({'error': f'Gemini API error {response.status_code}: {err_body.decode()}'})}\n\n"
                                return

                            async for line in response.aiter_lines():
                                line = line.strip()
                                if not line or not line.startswith("data:"):
                                    continue
                                raw_json = line[5:].strip()
                                if not raw_json:
                                    continue
                                try:
                                    data = json.loads(raw_json)
                                    cands = data.get("candidates", [])
                                    if cands:
                                        parts = cands[0].get("content", {}).get("parts", [])
                                        chunk = "".join(p.get("text", "") for p in parts)
                                        if chunk:
                                            yield f"data: {json.dumps({'chunk': chunk, 'done': False, 'model': 'Sangiang'})}\n\n"
                                except json.JSONDecodeError:
                                    continue
                            yield f"data: {json.dumps({'chunk': '', 'done': True, 'model': 'Sangiang'})}\n\n"
                except Exception as e:
                    yield f"data: {json.dumps({'error': str(e)})}\n\n"

            return StreamingResponse(
                gemini_event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )
        else:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent"
            async with httpx.AsyncClient(timeout=90.0) as client:
                res = await client.post(url, params={"key": api_key}, json=gemini_payload)
                res.raise_for_status()
                data = res.json()
                cands = data.get("candidates", [])
                content = ""
                if cands:
                    parts = cands[0].get("content", {}).get("parts", [])
                    content = "".join(p.get("text", "") for p in parts)
                return {"response": content, "model": target_model}

    payload = {
        "model": target_model,
        "messages": messages_payload,
        "stream": req.stream,
        "options": {
            "temperature": req.temperature,
            "top_p": 0.9,
            "num_ctx": 4096,
            "repeat_penalty": 1.15,
            "stop": ["<|im_start|>", "<|im_end|>", "<|endoftext|>"],
        },
    }

    if req.stream:
        async def event_generator() -> AsyncGenerator[str, None]:
            try:
                async with httpx.AsyncClient(timeout=180.0) as client:
                    async with client.stream(
                        "POST",
                        f"{OLLAMA_BASE_URL}/api/chat",
                        json=payload,
                        timeout=180.0,
                    ) as response:
                        if response.status_code != 200:
                            err_body = await response.aread()
                            yield f"data: {json.dumps({'error': f'Ollama error {response.status_code}: {err_body.decode()}'})}\n\n"
                            return

                        async for line in response.aiter_lines():
                            if not line.strip():
                                continue
                            try:
                                data = json.loads(line)
                                msg = data.get("message", {})
                                chunk = msg.get("content", "")
                                done = data.get("done", False)

                                yield f"data: {json.dumps({'chunk': chunk, 'done': done, 'model': target_model})}\n\n"
                                if done:
                                    break
                            except json.JSONDecodeError:
                                continue
            except httpx.ConnectError:
                yield f"data: {json.dumps({'error': 'Tidak dapat terhubung ke Ollama di localhost:11434. Pastikan Ollama aktif.'})}\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )
    else:
        # Non-streaming fallback
        try:
            async with httpx.AsyncClient(timeout=180.0) as client:
                res = await client.post(f"{OLLAMA_BASE_URL}/api/chat", json=payload)
                res.raise_for_status()
                data = res.json()
                content = data.get("message", {}).get("content", "")
                return {"response": content, "model": target_model}
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    print("=" * 60)
    print("  ✦ Sangiang Chatbot (Gemini Interface) ✦")
    print("  Berjalan di: http://localhost:2026")
    print("  Inisiator: Yayasan Cipta Manggala Dwipa")
    print("  Rekayasa AI & Penerjemah: Divisi DigiLab CMD")
    print("=" * 60)
    uvicorn.run("app:app", host="0.0.0.0", port=2026, reload=True)
