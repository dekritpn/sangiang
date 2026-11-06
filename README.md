# Sangiang Translation Engine
### *Sangihe Artificial Intelligence Network Agent*
> **Inisiator Proyek:** **Yayasan Cipta Manggala Dwipa**  
> **Rekayasa Sistem AI dan Penerjemah:** **Divisi DigiLab CMD**

Mesin penerjemah dua arah (**Bahasa Sangihe $\leftrightarrow$ Bahasa Indonesia**) berbasis **Hybrid Retrieval-Augmented Generation (RAG)** dan model bahasa lokal hasil fine-tuning **Sangiang (`sangiang:7b` / `qwen2.5:7b`)**.

Nama **"Sangiang"** merujuk pada sosok putri raja / putri kahyangan dalam sastra klasik Nusa Utara, yang diabadikan sebagai semi-akronim dari *Sangihe Artificial Intelligence Network Agent*.

### 🌐 Antarmuka Web yang Tersedia:
- 📖 **Translation Workbench (Port 8000):** [http://localhost:8000](http://localhost:8000) — Mesin penerjemah dua arah berfasilitas inspektur leksikon RAG & analisis morfologi.
- ✦ **Sangiang Chatbot (Port 2026):** [http://localhost:2026](http://localhost:2026) — Antarmuka percakapan cerdas bergaya **Google Gemini** dengan respons streaming langsung dan papan ketik diakritik Sangihe.

---

## 🏛️ Arsitektur Sistem

```text
[Input Teks (Bebas / Berdiakritik)] ───► [1. Normalizer & Stemmer Sangihe]
                                                    │
                 ┌──────────────────────────────────┴──────────────────────────────────┐
                 ▼                                                                     ▼
     [Lexical RAG (SQLite)]                                              [Sentence-level TM (BM25)]
     Steller-Aebersold Kamus                                             Korpus Paralel (29.835 Kalimat:
     (sarindi.sqlite: 11.391 lema)                                       Alkitab, Dongeng, & Himbawo)
                 │                                                                     │
                 └──────────────────────────────────┬──────────────────────────────────┘
                                                    ▼
                                       [Augmented Prompt Builder]
                                 (Aturan Diakritik + Kamus + Polisemi)
                                                    │
                                                    ▼
                                      [Model AI: Sangiang (7B)]
                                   (Local Ollama via CPU/GPU)
                                                    │
                                                    ▼
                                     [Diacritic Restorer Post-Processor]
                                                    │
                                                    ▼
                                        [Output Terjemahan Formal]
```

### Komponen Utama:
1. **`morphology/`**:
   - `normalizer.py`: Menghapus tanda diakritik (`ạ, ẹ, ị, ọ, ụ, ě, ẹ̌, l᷊`) untuk pencarian leksikal fleksibel, serta standardisasi glotal/apostrof.
   - `stemmer.py`: *Rule-based morphological analyzer* untuk pola imbuhan Sangihe (prefiks *ma-*, *maki-*, *maka-*, *mě̌-*, sisipan *-um-*, *-in-*, sufiks *-ang*, *-eng*, alternasi morfonemik $b \leftrightarrow w$, $d \leftrightarrow r$, peluruhan vokal gema, dan reduplikasi).
   - `diacritic_restorer.py`: Menyelaraskan teks terjemahan bahasa Sangihe dengan kamus referensi untuk merekonstruksi tanda diakritik secara presisi.
2. **`retrieval/`**:
   - `lexical_retriever.py`: Menghubungkan langsung ke SQLite Steller-Aebersold (`sarindi.sqlite`) untuk lema dan indeks balik bahasa Indonesia (`id_index`).
   - `indexer.py`: Membangun database `data/parallel_corpus.sqlite` berisi 29.835 kalimat paralel Alkitab, cerita rakyat *Dongeng*, dan wiracarita *Biong i Himbawo*.
   - `semantic_retriever.py`: Fast candidate retrieval berbasis SQLite FTS5 BM25 ($< 3$ ms) yang menjaga model bahasa tetap reside di RAM tanpa *memory eviction*.
3. **`engine/`**:
   - `translator.py`: Orkestrator pipeline terjemahan end-to-end, dilengkapi penanganan identitas Sangiang.
   - `prompt_templates.py`: Format prompt terstruktur dengan persona Sangiang, panduan disambiguasi nomor arti lema, dan kaidah fonemis.
   - `llm_client.py`: Klien API Ollama lokal dengan dukungan dynamic model selector.
4. **`api/`**:
   - `app.py`: Layanan REST API berbasis FastAPI.
   - `schemas.py`: Kontrak skema Pydantic untuk request dan response.
5. **`static/`**:
   - Antarmuka **Web Translation Workbench** modern bergaya Glassmorphism dengan bilah sisip diakritik virtual, dropdown pemilih model, dan inspektur konteks RAG.
6. **`benchmark/`**:
   - `generate_testset.py`: Pembuat subset evaluasi representatif (150 kalimat terisolasi).
   - `evaluate.py`: Evaluator metrik kualitas (**BLEU**, **chrF++**, dan **Diacritic Density Ratio**).
   - `compare_models.py`: Perkakas evaluasi komparatif *head-to-head* antara Base Model vs Fine-Tuned Model.
7. **`training/`**:
   - `prepare_dataset.py`: Generator dataset pelatihan LoRA / QLoRA bebas bocor (*anti-leakage*).
   - `sangihe_qwen2_5_finetuning_colab.ipynb`: Notebook Unsloth turnkey untuk pelatihan di GPU T4 Google Colab.
   - `Modelfile`: Konfigurasi ChatML template dan persona Sangiang untuk Ollama.
   - `deploy_to_ollama.sh`: Skrip otomatisasi pendaftaran model GGUF ke Ollama lokal.
8. **`book_documentation/`**:
   - Sub-proyek buku dokumentasi lengkap dalam format **LaTeX (XeLaTeX)** berjudul *"Menghidupkan Bahasa di Era AI"*.

---

## 🛠️ Panduan Operasional & Pemeliharaan Sistem (Maintenance)

Bagian ini ditujukan khusus bagi **pengelola sistem (*system administrator*)** untuk menjalankan, memelihara, dan memperbarui layanan.

### 1. Menjalankan Layanan Translation Engine

```bash
# A. Pastikan layanan Ollama lokal aktif
systemctl --user status ollama-local.service
# Jika belum aktif, jalankan:
systemctl --user start ollama-local.service

# B. Jalankan server FastAPI Uvicorn
uv run uvicorn api.app:app --host 0.0.0.0 --port 8000 --reload
```

- **Aplikasi Web Workbench:** Kunjungi `http://localhost:8000` di peramban web (atau melalui IP Tailscale untuk akses jarak jauh dari ponsel/perangkat lain).
- **Dokumentasi Interaktif API (Swagger UI):** Akses di `http://localhost:8000/docs`.

---

### 2. Mendaftarkan Model Fine-Tuned "Sangiang" ke Ollama

Setelah proses pelatihan di Google Colab selesai dan berkas `.gguf` diunduh dari Google Drive:

```bash
# 1. Salin berkas GGUF ke folder training/
cp /path/ke/qwen2.5-sangihe-7b-q4_k_m.gguf training/

# 2. Jalankan skrip pendaftaran otomatis
./training/deploy_to_ollama.sh
```

Skrip ini akan secara otomatis:
- Membaca konfigurasi persona Sangiang dari `training/Modelfile`.
- Mendaftarkan model ke Ollama dengan nama resmi **`sangiang:7b`** (dan alias `qwen2.5-sangihe:7b`).
- Memverifikasi ketersediaan model via `ollama list`.

Untuk menjadikannya model *default* di server terjemahan:
```bash
export OLLAMA_MODEL=sangiang:7b
```
*(Atau pilih langsung model `sangiang:7b (Putri Sangiang ✦)` dari dropdown di antarmuka Web Workbench).*

---

### 3. Menguji Identitas & Terjemahan Sangiang

Uji respons identitas langsung melalui terminal:

```bash
# Uji Identitas Bahasa Indonesia
curl -s -X POST http://127.0.0.1:8000/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Siapa namamu?", "direction": "sangihe_to_id"}' | jq .translated_text
# Output: "Saya adalah Sangiang, kecerdasan buatan dengan kemampuan berbahasa Sangihe."

# Uji Identitas Bahasa Sangihe (Isai arengu? / Isai i kau? / Arengu kai apa?)
curl -s -X POST http://127.0.0.1:8000/v1/translate \
  -H "Content-Type: application/json" \
  -d '{"text": "Isai arengu?", "direction": "sangihe_to_id"}' | jq .translated_text
# Output: "Iạ kai i Sangiang, kecerdasan buatan mạbiahěng u bisara Sangihe."
```

---

### 4. Menjalankan Uji Tolok Ukur Kualitas (Benchmark)

Untuk mengukur performa model terhadap 150 kalimat acuan (*held-out testset*):

```bash
# Evaluasi model aktif tunggal (BLEU, chrF++, dan Diacritic Ratio)
uv run python -m benchmark.evaluate --direction sangihe_to_id --limit 15

# Evaluasi Komparatif Head-to-Head: Base Model vs Sangiang Fine-Tuned
uv run python -m benchmark.compare_models \
  --base qwen2.5:7b \
  --finetuned sangiang:7b \
  --direction sangihe_to_id \
  --limit 15
```

---

### 5. Memutakhirkan & Mengompilasi Buku Dokumentasi LaTeX

Sub-proyek buku dokumentasi dirancang agar selalu sinkron secara otomatis terhadap perubahan data di proyek:

```bash
# Masuk ke direktori dokumentasi
cd book_documentation/

# Jalankan skrip kompilasi otomatis
./compile.sh
```

Skrip ini akan mengeksekusi:
1. `sync_project_status.py`: Mengekstrak jumlah korpus, lema kamus, dan pasangan latih terkini ke `stats_autogen.tex`.
2. Kompilasi 2-pass menggunakan `xelatex` (memanfaatkan font *Gentium Plus* untuk diakritik Sangihe `ạ, ẹ, ị, ọ, ụ, ě, ẹ̌, l᷊`).
3. Menghasilkan naskah buku PDF mutakhir: `book_documentation/Buku_Dokumentasi_LLM_Bahasa_Sangihe.pdf`.

---

## 📡 Endpoint REST API Utama

| Metode | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `POST` | `/v1/translate` | Menerjemahkan teks (menerima input tanpa/dengan diakritik, opsi override model) |
| `GET` | `/v1/models` | Menampilkan daftar model yang tersedia di Ollama beserta status aktif |
| `POST` | `/v1/morphology/analyze` | Membedah kata Sangihe menjadi prefiks, infiks, sufiks, dan akar kata dasar |
| `POST` | `/v1/dictionary/lookup` | Pencarian langsung ke 11.391 lema kamus Steller-Aebersold |
| `GET` | `/health` | Memeriksa ketersediaan koneksi database dan Ollama |

---

## 📄 Lisensi, Hak Cipta & Penghargaan

Proyek dan sistem ini diinisiasi dan diprakarsai oleh **Yayasan Cipta Manggala Dwipa**, dengan rekayasa sistem kecerdasan buatan (AI) serta penerjemahan oleh **Divisi DigiLab CMD**, sebagai wujud dedikasi untuk pelestarian bahasa daerah Nusantara dan kemajuan literasi digital kebudayaan bahari Kepulauan Sangihe.

### Kepemilikan Hak Cipta & Tim Terkait:
- **Inisiator Proyek**: **Yayasan Cipta Manggala Dwipa**
- **Rekayasa Sistem AI dan Penerjemah**: **Divisi DigiLab CMD**
- **Yayasan Cipta Manggala Dwipa**: Pemilik hak cipta korpus terjemahan *Kamus Sangihe-Indonesia*.
- **Brill / KITLV**: Pemilik hak cipta buku kamus terkait (*Sangihe-Nederlandsch Woordenboek* karya K.G.F. Steller & W.E. Aebersold, 1959).
- **Lembaga Alkitab Indonesia (LAI)**: Pemilik hak cipta naskah dan buku-buku Alkitab terkait (Alkitab Terjemahan Bahasa Sangihe, Terjemahan Baru / TB, dan Bahasa Indonesia Masa Kini / BIMK).

Korpus dan leksikon juga memadukan naskah sastra lisan tradisional *Sasahara* dan puisi epik *Biong i Himbawo* sebagai bagian dari warisan kekayaan budaya Nusantara.
