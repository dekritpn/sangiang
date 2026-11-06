# Sub-Proyek: Dokumentasi Proyek LLM Bahasa Sangihe

Dokumentasi komprehensif proyek mesin penerjemah Bahasa Sangihe $\leftrightarrow$ Bahasa Indonesia yang disusun dalam format buku berstandar akademis dan populer menggunakan **LaTeX (XeLaTeX)**.

---

## 📖 Ringkasan Dokumen Buku

- **Judul Buku:** *Menghidupkan Bahasa di Era AI: Kisah, Sains, dan Rekayasa di Balik Mesin Penerjemah Bahasa Sangihe*
- **Format:** LaTeX (`book` document class), dikompilasi dengan `xelatex`
- **Tipografi:** Font *Gentium Plus* (SIL International) untuk merender karakter fonemis khas Sangihe (`ạ, ẹ, ị, ọ, ụ`, `ě`, `ẹ̌`, dan combining under-tilde `l᷊`) secara sempurna.
- **Gaya Penulisan:** Populer-Edukatif / Presentatif (konsep teknis seperti LLM, QLoRA, RAG, dan FTS5 diterangkan dengan analogi visual sehari-hari yang mudah dipahami oleh pembaca awam).
- **Jumlah Halaman Saat Ini:** 49 Halaman (5 Bagian, 15 Bab, 1 Lampiran Morfologi).

---

## 📁 Struktur Direktori

```
book_documentation/
├── compile.sh                      # Skrip kompilasi otomatis (XeLaTeX 2-pass)
├── main.tex                        # Master document utama
├── preamble.tex                    # Konfigurasi font, tcolorbox, listings, geometry
├── sync_project_status.py          # Skrip sinkronisasi data proyek ke LaTeX
├── stats_autogen.tex               # Definisi angka statistik proyek (otomatis diperbarui)
├── Buku_Dokumentasi_LLM_Bahasa_Sangihe.pdf  # Hasil kompilasi buku PDF (49 halaman)
└── chapters/                       # Modul bab naskah buku
    ├── ch01_pendahuluan.tex        # Bab 1: Latar Belakang & Urgensi Digitalisasi
    ├── ch02_fonologi_diakritik.tex # Bab 2: Seni Bunyi & Rahasia Diakritik
    ├── ch03_morfologi.tex          # Bab 3: Morfologi & Kasus Alih Bunyi Kata 'Waes'
    ├── ch04_korpus_leksikon.tex    # Bab 4: Kamus Steller-Aebersold & Teks Paralel
    ├── ch05_preprocessing.tex      # Bab 5: Normalisasi & Pembersihan Teks
    ├── ch06_benchmark.tex          # Bab 6: Tolok Ukur Uji & Pencegahan Kebocoran Data
    ├── ch07_hybrid_rag.tex         # Bab 7: Konsep & Filosofi Hybrid RAG
    ├── ch08_retrieval_engine.tex   # Bab 8: Mesin Pencari SQLite BM25 vs RAM Thrashing
    ├── ch09_prompt_engineering.tex # Bab 9: Rekayasa Prompt & Disambiguasi Polisemi
    ├── ch10_finetuning_strategi.tex# Bab 10: Strategi Fine-Tuning 4-bit QLoRA
    ├── ch11_pelatihan_evaluasi.tex # Bab 11: Analisis Kurva Loss Aktual di Cloud
    ├── ch12_gguf_deployment.tex    # Bab 12: Kuantisasi GGUF & Pendaftaran ke Ollama
    ├── ch13_rest_api.tex           # Bab 13: Arsitektur REST API FastAPI
    ├── ch14_web_ui.tex             # Bab 14: Antarmuka Web Translation Workbench
    ├── ch15_hasil_benchmark.tex    # Bab 15: Hasil Evaluasi & Peta Masa Depan
    └── appendix_morphology.tex     # Lampiran: Tabel Kaidah Morfologi Sangihe
```

---

## ⚡ Cara Menyelaraskan dan Mengompilasi Buku

Setiap kali ada pembaruan pada proyek utama (misal data korpus bertambah, model baru didaftarkan, atau hasil benchmark baru keluar):

1. Masuk ke direktori buku:
   ```bash
   cd book_documentation/
   ```

2. Jalankan skrip kompilasi:
   ```bash
   ./compile.sh
   ```

Skrip ini akan secara otomatis:
- Menarik angka real-time dari database korpus dan kamus melalui `sync_project_status.py`.
- Menyimpan variabel ke `stats_autogen.tex`.
- Mengompilasi naskah menjadi `Buku_Dokumentasi_LLM_Bahasa_Sangihe.pdf`.
