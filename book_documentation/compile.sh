#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  Kompilasi Buku Dokumentasi LLM Bahasa Sangihe"
echo "=========================================================="

# 1. Sinkronisasi data terkini dari proyek utama
echo "🔄 Menyelaraskan statistik proyek terbaru..."
python3 sync_project_status.py

# 2. Kompilasi XeLaTeX (Pass 1)
echo "📄 Menjalankan XeLaTeX (Pass 1)..."
xelatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null

# 3. Kompilasi XeLaTeX (Pass 2 untuk Table of Contents & Referensi)
echo "📑 Menjalankan XeLaTeX (Pass 2 - Indeks & Daftar Isi)..."
xelatex -interaction=nonstopmode -halt-on-error main.tex > /dev/null

# 4. Beri nama berkas output yang rapi
if [ -f "main.pdf" ]; then
    cp main.pdf Buku_Dokumentasi_LLM_Bahasa_Sangihe.pdf
    echo "=========================================================="
    echo "✅ Berhasil! Buku telah dikompilasi menjadi:"
    echo "   $SCRIPT_DIR/Buku_Dokumentasi_LLM_Bahasa_Sangihe.pdf"
    echo "=========================================================="
else
    echo "❌ Gagal menghasilkan PDF."
    exit 1
fi
