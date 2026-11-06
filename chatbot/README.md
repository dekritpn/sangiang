# ✦ Sangiang Chatbot (Gemini-Inspired Web Interface)

> **Inisiator Proyek:** **Yayasan Cipta Manggala Dwipa**  
> **Rekayasa Sistem AI & Penerjemah:** **Divisi DigiLab CMD**  
> **Model Utama:** `sangiang:7b` (Ollama)  
> **Akses Web:** [http://localhost:2026](http://localhost:2026)

---

## 🏛️ Gambaran Umum

**Sangiang Chatbot** adalah aplikasi percakapan cerdas dwibahasa (**Bahasa Sangihe $\leftrightarrow$ Bahasa Indonesia**) yang dirancang dengan estetika antarmuka modern terinspirasi oleh **Google Gemini**.

Aplikasi ini mendemonstrasikan keunggulan model bahasa lokal **Sangiang (`sangiang:7b`)** sebagai asisten filologi, teman percakapan sehari-hari, serta penjaga kelestarian sastra dan budaya bahari Kepulauan Nusa Utara.

---

## ✨ Fitur-Fitur Utama Antarmuka (Gemini-Style)

1. **Desain Modern Obsidian & Aurora Sparkle**:
   - Tema gelap *Google Obsidian* (`#131314`) dan dukungan tema terang.
   - Tipografi modern Google Font *Outfit* serta *Gentium Plus* untuk ortografi diakritik fonemis Sangihe.
   - Aksen gradien aurora dinamis (*iridescent sparkle*).

2. **Dukungan Streaming Real-Time (SSE)**:
   - Respons kata demi kata mengalir secara langsung (*streaming Server-Sent Events*) dengan kursor berkedip mulus.
   - Tombol *Stop Generation* untuk menghentikan jawaban kapan saja.

3. **Papan Ketik Diakritik Interaktif (Sangihe Diacritic Dock)**:
   - Tombol cepat untuk memasukkan karakter fonemis khas Sangihe:  
     `ạ` `ẹ` `ị` `ọ` `ụ` `ě` `ẹ̌` `l᷊`
   - Karakter langsung tersisip tepat di posisi kursor (*caret*) textarea tanpa kehilangan fokus pengetikan.

4. **Sidebar Riwayat Percakapan (Recent Sessions)**:
   - Menu samping yang dapat diciutkan (*collapsible*).
   - Pengelompokan sesi obrolan tersimpan di penyimpanan lokal (*LocalStorage*).
   - Tombol *"Obrolan Baru"* dan *"Bersihkan Riwayat"*.

5. **Aksi Pesan Multi-Fitur**:
   - 📋 **Salin Pesan:** Menyalin seluruh teks ke papan klip dengan indikator animasi centang hijau.
   - 🔊 **Text-to-Speech (TTS):** Membacakan jawaban secara audio melalui peramban.
   - 🔄 **Regenerate Response:** Menghasilkan ulang respons alternatif dari AI.

6. **Format Markdown Kaya**:
   - Mendukung format cetak tebal, miring, daftar butir, blok kutipan, tabel kosakata, dan blok kode dengan pewarnaan sintaks (*syntax highlighting*).

---

## 🚀 Cara Menjalankan

### Cara 1: Menjalankan Skrip Otomatis
```bash
cd /home/dpng/Projects/sangihe_translation_engine/chatbot
./start_chatbot.sh
```

### Cara 2: Menjalankan Perintah Uvicorn Langsung
```bash
cd /home/dpng/Projects/sangihe_translation_engine/chatbot
uv run uvicorn app:app --host 0.0.0.0 --port 2026 --reload
```

Buka peramban web di:
👉 **[http://localhost:2026](http://localhost:2026)**

---

## 📡 Arsitektur API

| Metode | Endpoint | Deskripsi |
| :--- | :--- | :--- |
| `GET` | `/` | Antarmuka web Gemini Chatbot |
| `POST` | `/api/chat` | Endpoint percakapan (mendukung `stream: true` via SSE) |
| `GET` | `/api/models` | Daftar model LLM yang tersedia di Ollama |
| `GET` | `/api/health` | Pemeriksaan kesehatan layanan dan koneksi Ollama |

---

## 📄 Hak Cipta & Penghargaan

- **Inisiator Proyek:** Yayasan Cipta Manggala Dwipa
- **Rekayasa Sistem AI & Penerjemah:** Divisi DigiLab CMD
- **Pemilik Hak Cipta Korpus Kamus:** Yayasan Cipta Manggala Dwipa
- **Pemilik Hak Cipta Kamus Sumber (*Sangihe-Nederlandsch Woordenboek* 1959):** Brill / KITLV
- **Pemilik Hak Cipta Teks Kitab Suci:** Lembaga Alkitab Indonesia (LAI)
