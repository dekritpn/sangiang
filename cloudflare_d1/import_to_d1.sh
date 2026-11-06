#!/usr/bin/env bash
set -e
DB_NAME="${1:-sangiang-db}"
echo "=========================================================="
echo "  Mengimpor Database Sangiang ke Cloudflare D1: $DB_NAME"
echo "=========================================================="
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for sql_file in "$DIR"/*.sql; do
  echo "[*] Menjalankan $(basename "$sql_file") ..."
  npx wrangler d1 execute "$DB_NAME" --remote --file="$sql_file"
done
echo "[+] Selesai! Seluruh data kamus, korpus paralel, dan feedback telah masuk ke Cloudflare D1 ($DB_NAME)."
