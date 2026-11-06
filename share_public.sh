#!/usr/bin/env bash
# Skrip untuk membagikan Sangiang Translation Workbench (Port 8000) & Chatbot (Port 2026) ke publik
# menggunakan Cloudflare Tunnel (Gratis, HTTPS otomatis)

set -e

CLOUDFLARED="${HOME}/.local/bin/cloudflared"

if [ ! -x "$CLOUDFLARED" ]; then
    echo "Mengunduh cloudflared ke ~/.local/bin/cloudflared..."
    mkdir -p "${HOME}/.local/bin"
    curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o "$CLOUDFLARED"
    chmod +x "$CLOUDFLARED"
fi

echo "========================================================"
echo "  SANGIANG PUBLIC TUNNEL LAUNCHER (Cloudflare Gratis)   "
echo "========================================================"
echo "Pilih layanan yang ingin dibagikan ke publik:"
echo "  1) Translation Workbench (Port 8000)"
echo "  2) Sangiang Chatbot      (Port 2026)"
echo "  3) Keduanya sekaligus    (Port 8000 & 2026)"
echo "--------------------------------------------------------"
read -rp "Pilihan Anda [1/2/3, default=3]: " choice
choice=${choice:-3}

case "$choice" in
    1)
        echo "Membuka tunnel publik untuk Port 8000 (Workbench)..."
        exec "$CLOUDFLARED" tunnel --url http://localhost:8000 --no-autoupdate
        ;;
    2)
        echo "Membuka tunnel publik untuk Port 2026 (Chatbot)..."
        exec "$CLOUDFLARED" tunnel --url http://localhost:2026 --no-autoupdate
        ;;
    3)
        echo "Membuka tunnel untuk Port 8000 dan Port 2026 (Tekan Ctrl+C untuk berhenti)..."
        trap 'kill 0' SIGINT SIGTERM
        "$CLOUDFLARED" tunnel --url http://localhost:8000 --no-autoupdate 2>&1 | sed 's/^/[WORKBENCH-8000] /' &
        "$CLOUDFLARED" tunnel --url http://localhost:2026 --no-autoupdate 2>&1 | sed 's/^/[CHATBOT-2026]   /' &
        wait
        ;;
    *)
        echo "Pilihan tidak valid."
        exit 1
        ;;
esac

