# Panduan Pelatihan & Fine-Tuning Model Sangiang v3 (Morphological Induction & Disambiguation)

Dokumen ini menjelaskan alur kerja (*workflow*) lengkap pelaksanaan fine-tuning model **Sangiang v3** menggunakan Google Colab (GPU T4/L4 gratis), ekspor ke format GGUF (Q4_K_M), dan penyebaran (*deployment*) kembali ke Ollama lokal di komputer Anda.

**Inisiator Proyek:** Yayasan Cipta Mandala Dwipa  
**Rekayasa Sistem AI & Terjemahan:** Divisi DigiLab CMD  

---

## 🌟 Pembaruan Utama Sangiang v3

1. **Disambiguasi Pronomina & Klitik Posesif Otentik**:
   - Memperbaiki kekeliruan homograf: **`iạ`** (Sangihe: orang pertama tunggal = aku/saya) tidak lagi tertukar dengan kata **`ia`** (Indonesia: orang ketiga tunggal = dia).
   - Memperbaiki klitik posesif: **`-u`** (orang kedua: -mu / milikmu) seperti `waes-u` (sarangmu, bukan sarangnya), **`-ne`** (-nya), dan **`-ku`** (-ku).
   - Menyertakan 560+ pasang data kontras pronomina yang di-oversample khusus.

2. **Morphological Induction Chain-of-Thought (10.000 Pasang Data)**:
   - Merealisasikan ide dekonstruksi morfologi: analisis kata bentukan berimbuhan/sisipan bersama kata dasar, pergeseran makna leksikon Steller-Aebersold (1959), dan penalaran berantai (*Chain-of-Thought*).
   - Mengajarkan secara eksplisit afiksasi produktif: prefiks `mě-`, `ma-`, `maka-`, `manga-`, sisipan `-um-`, `-in-`, sufiks `-ang`/`-eng`, sirkumfiks `ka-...-ang`, `pe-...-ang`, serta hukum alternasi fonem $w \leftrightarrow b$ dan $d \leftrightarrow r$.

3. **Response-Only Loss Masking (`train_on_responses_only`)**:
   - Loss gradient 100% terkonsentrasi pada jawaban terjemahan dan penalaran asisten, bukan menghafal kalimat sistem prompt yang berulang.

---

## 📁 Berkas & Sumber Daya yang Disiapkan

1. **Dataset Master Sangiang v3:**
   - [`training/sangiang_v3_colab_data.zip`](file:///home/dpng/Projects/sangihe_translation_engine/training/sangiang_v3_colab_data.zip) (4.01 MB):
     * **26.315 pasang instruksi latih** (`train.jsonl`) dan **1.386 pasang validasi** (`val.jsonl`).
     * 10.000 pasang penalaran morfologi (*Morphological Reasoning CoT*).
     * 560+ pasang kontras pronomina & klitik posesif.
     * 17.141 pasang terjemahan paralel terkurasi (Alkitab & Non-Alkitab).
     * Format ChatML standar dengan master system prompt.

2. **Jupyter Notebook yang Dioptimalkan (Anti-Bottleneck):**
   - [`training/sangihe_qwen2_5_finetuning_colab.ipynb`](file:///home/dpng/Projects/sangihe_translation_engine/training/sangihe_qwen2_5_finetuning_colab.ipynb):
     * Menggunakan **Unsloth (Fast QLoRA)** pada base model `unsloth/Qwen2.5-7B-Instruct-bnb-4bit`.
     * `max_seq_length = 512` dengan `train_on_responses_only`.
     * Evaluasi validasi cepat (100 sampel) mencegah bottleneck I/O.
     * **Durasi Pelatihan:** Hanya **20–25 menit** di GPU T4 gratis.

3. **Alat Otomatisasi Ollama Lokal:**
   - [`training/Modelfile`](file:///home/dpng/Projects/sangihe_translation_engine/training/Modelfile): Konfigurasi ChatML template dan aturan pronomina untuk Ollama.
   - [`training/deploy_to_ollama.sh`](file:///home/dpng/Projects/sangihe_translation_engine/training/deploy_to_ollama.sh): Skrip satu langkah untuk mendaftarkan file GGUF ke Ollama lokal sebagai model `sangiang:7b`.

---

## 🚀 Langkah Eksekusi di Google Colab

1. **Buka Google Colab**: Kunjungi [Google Colab](https://colab.research.google.com/) dan unggah notebook:
   `training/sangihe_qwen2_5_finetuning_colab.ipynb`
2. **Pilih GPU Runtime**: Menu **Runtime** → **Change runtime type** → Pilih **T4 GPU** (Gratis).
3. **Jalankan Sel Berurutan**:
   - **Sel 1**: Instal dependensi Unsloth & TRL.
   - **Sel 2**: Muat model Qwen2.5:7B 4-bit dan LoRA adapter.
   - **Sel 3**: Unggah file `training/sangiang_v3_colab_data.zip` (4.01 MB).
   - **Sel 4 & 5**: Jalankan pelatihan SFT (~20-25 menit).
   - **Sel 6**: Uji inferensi otomatis untuk pronomina `iạ`, klitik `-u`, dan penalaran morfologi.
   - **Sel 7 & 8**: Ekspor ke format GGUF (Q4_K_M) dan simpan ke Google Drive / unduh langsung.
   - Tersedia juga opsi unduh langsung via browser menggunakan `files.download(...)` bila Google Drive mengalami kendala kuota atau sinkronisasi.

---

## 📥 Langkah 4: Deploy ke Ollama Lokal

1. Salin berkas `*.gguf` hasil unduhan ke folder:
   `/home/dpng/Projects/sangihe_translation_engine/training/`
2. Jalankan skrip deployment:
   ```bash
   ./training/deploy_to_ollama.sh
   ```
   Skrip ini otomatis mendaftarkan model ke Ollama lokal dengan nama:
   `sangiang:7b` (dan alias `qwen2.5-sangihe:7b`).

3. Periksa ketersediaan model:
   ```bash
   ollama list
   ```

---

## 🎯 Langkah 5: Uji Coba Dunia Nyata

1. **Sangiang Chatbot (Port 2026):**
   - Buka `http://localhost:2026`.
   - Sapa Sangiang: *"Kere habarẹ̌?"* atau *"Tabea! Siapa namamu?"*.
   - Sangiang akan merespons dengan luwes, santun, dan menggunakan ortografi diakritik yang presisi.

2. **Translation Workbench (Port 8000):**
   - Buka `http://localhost:8000`.
   - Pilih model `sangiang:7b` dari dropdown model untuk terjemahan berakurasi tinggi yang dipadukan dengan Hybrid RAG.
