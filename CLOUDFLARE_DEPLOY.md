# Panduan Deploy Otomatis ke Cloudflare Pages & Cloudflare D1 via GitHub (`sangihe.org`)

Arsitektur repositori ini telah disiapkan untuk berjalan **100% Serverless di Cloudflare Pages + Cloudflare D1** dengan sinkronisasi otomatis dari **GitHub**, serta mendukung dua subdomain sekaligus dalam satu proyek:
- **`translate.sangihe.org`** $\rightarrow$ **Sangiang Translation Engine**
- **`chat.sangihe.org`** (atau `sangiang.sangihe.org`) $\rightarrow$ **Sangiang Chatbot**

---

## Struktur Proyek untuk Cloudflare Pages
- **`public/`**: Direktori hasil build statis untuk Cloudflare Pages (`public/index.html` untuk Sangiang Translate, dan `public/chat/index.html` untuk Sangiang Chatbot).
- **`functions/`**: Backend **Cloudflare Pages Functions** yang menjalankan seluruh logika Sangiang di jaringan Edge Cloudflare:
  - `functions/_middleware.js`: Mengatur CORS dan merutekan subdomain `chat.sangihe.org` secara otomatis ke halaman Sangiang Chatbot (`/chat/*`).
  - `functions/_lib/sangihe_engine.js`: Mesin normalisasi ortografi, stemmer morfologi & hukum perubahan bunyi Sangihe, kueri kamus **Cloudflare D1**, restorasi diakritik, serta integrasi Gemini API.
  - `functions/v1/*`: Endpoint API Mesin Penerjemah (`/v1/translate`, `/v1/feedback`, `/v1/dictionary/lookup`, `/v1/morphology/analyze`, `/v1/models`).
  - `functions/api/*`: Endpoint API Chatbot (`/api/chat` dengan *Server-Sent Events streaming*, `/api/health`, `/api/models`).
- **`cloudflare_d1/`**: Berisi file migrasi SQL dari `kamus_sangihe_modern.sqlite` (36.230 lema), `parallel_corpus.sqlite` (30.307 kalimat paralel), dan `user_feedback.sqlite` yang siap diunggah ke **Cloudflare D1**.

---

## Langkah 1: Buat & Isi Database Cloudflare D1 (`sangiang-db`)
Cukup dilakukan **satu kali** dari terminal komputer Anda:

1. Login ke akun Cloudflare melalui Wrangler:
   ```bash
   npx wrangler login
   ```
2. Buat database Cloudflare D1 bernama `sangiang-db`:
   ```bash
   npx wrangler d1 create sangiang-db
   ```
   Salin `database_id` yang muncul di terminal, lalu tempelkan ke dalam file [`wrangler.toml`](file:///home/dpng/Projects/sangihe_translation_engine/wrangler.toml) pada baris `database_id = "..."`.
3. Ekspor (jika ada pembaruan data lokal) dan impor seluruh kamus + korpus paralel ke Cloudflare D1:
   ```bash
   uv run python scripts/export_to_cloudflare_d1.py
   ./cloudflare_d1/import_to_d1.sh sangiang-db
   ```

---

## Langkah 2: Push Repositori ke GitHub
```bash
git init
git add .
git commit -m "Initial commit: Sangiang Translation Engine & Chatbot (Cloudflare Pages + D1)"
git branch -M main
git remote add origin https://github.com/<ORGANISASI_ATAU_USER>/<NAMA_REPO>.git
git push -u origin main
```

---

## Langkah 3: Hubungkan GitHub ke Cloudflare Pages
1. Buka **Cloudflare Dashboard** $\rightarrow$ **Workers & Pages** $\rightarrow$ **Create** $\rightarrow$ tab **Pages** $\rightarrow$ **Connect to Git**.
2. Pilih repositori GitHub proyek ini.
3. Pada bagian **Build settings**:
   - **Project name:** `sangiang`
   - **Production branch:** `main`
   - **Build command:** `python3 scripts/build_cloudflare_pages.py` *(atau kosongkan karena folder `public/` sudah ter-build di repo)*
   - **Build output directory:** `public`
4. Klik **Save and Deploy**.

---

## Langkah 4: Hubungkan Binding D1 & `GEMINI_API_KEY` di Cloudflare Pages
Di halaman proyek **Cloudflare Pages (`sangiang`)** $\rightarrow$ tab **Settings**:
1. **Variables and Secrets** $\rightarrow$ Tambahkan Secret:
   - Variable name: `GEMINI_API_KEY`
   - Value: *(API Key Google Gemini Anda)*
2. **Bindings** $\rightarrow$ **Add** $\rightarrow$ **D1 database**:
   - Variable name: `DB`
   - D1 database: Pilih `sangiang-db`
3. Lakukan **Retry deployment** (atau push commit baru ke GitHub) agar binding `DB` dan `GEMINI_API_KEY` aktif.

---

## Langkah 5: Pasang Subdomain `translate.sangihe.org` & `chat.sangihe.org`
Masih di proyek Cloudflare Pages (`sangiang`) $\rightarrow$ tab **Custom domains** $\rightarrow$ **Set up a custom domain**:
1. Tambahkan **`translate.sangihe.org`** $\rightarrow$ Otomatis akan menampilkan **Sangiang Translation Engine**.
2. Tambahkan **`chat.sangihe.org`** (atau **`sangiang.sangihe.org`**) pada proyek yang sama $\rightarrow$ Middleware [`functions/_middleware.js`](file:///home/dpng/Projects/sangihe_translation_engine/functions/_middleware.js) akan secara otomatis mengarahkan pengunjung `chat.sangihe.org` ke antarmuka **Sangiang Chatbot**!

Setiap kali tim kontributor melakukan `git push` atau *merge Pull Request* di GitHub, Cloudflare Pages akan otomatis memperbarui kedua subdomain tersebut.

