#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  ✦ Sangiang Chatbot (Gemini-Inspired Web Interface) ✦"
echo "  Inisiator: Yayasan Cipta Manggala Dwipa"
echo "  Rekayasa AI & Penerjemah: Divisi DigiLab CMD"
echo "  Model: sangiang:7b (Ollama)"
echo "  Akses: http://localhost:2026"
echo "=========================================================="

export PYTHONPATH="$SCRIPT_DIR/..:$PYTHONPATH"

# Run with uv or python3
if command -v uv &> /dev/null; then
    uv run uvicorn app:app --host 0.0.0.0 --port 2026 --reload
else
    python3 -m uvicorn app:app --host 0.0.0.0 --port 2026 --reload
fi
