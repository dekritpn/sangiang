#!/usr/bin/env bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=========================================================="
echo "  Deploy Fine-Tuned Model to Local Ollama"
echo "=========================================================="

# Check if a GGUF file path was provided as argument
GGUF_FILE="$1"

if [ -z "$GGUF_FILE" ]; then
    # Look for any .gguf file in training/ or training/data/
    GGUF_FILE=$(find . -maxdepth 2 -name "*.gguf" | head -n 1)
fi

if [ -z "$GGUF_FILE" ] || [ ! -f "$GGUF_FILE" ]; then
    echo "❌ Error: File GGUF hasil fine-tuning belum ditemukan!"
    echo "Silakan salin file .gguf hasil export dari Google Colab / Drive ke folder:"
    echo "  $SCRIPT_DIR/"
    echo ""
    echo "Atau jalankan skrip ini dengan argumen path file GGUF:"
    echo "  ./deploy_to_ollama.sh /path/to/model-q4_k_m.gguf"
    exit 1
fi

echo "📦 Menemukan file GGUF: $GGUF_FILE"

# Prepare temporary Modelfile pointing directly to the GGUF file
TEMP_MODELFILE="$SCRIPT_DIR/Modelfile.tmp"
cat << EOF > "$TEMP_MODELFILE"
FROM $GGUF_FILE

TEMPLATE """{{- if .Messages }}
{{- if or .System .Tools }}<|im_start|>system
{{- if .System }}
{{ .System }}
{{- end }}
{{- if .Tools }}

# Tools

You may call one or more functions to assist with the user query.

You are provided with function signatures within <tools></tools> XML tags:
<tools>
{{- range .Tools }}
{"type": "function", "function": {{ .Function }}}
{{- end }}
</tools>

For each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:
<tool_call>
{"name": <function-name>, "arguments": <args-json-object>}
</tool_call>
{{- end }}<|im_end|>
{{ end }}
{{- range \$i, \$_ := .Messages }}
{{- \$last := eq (len (slice \$.Messages \$i)) 1 -}}
{{- if eq .Role "user" }}<|im_start|>user
{{ .Content }}<|im_end|>
{{ else if eq .Role "assistant" }}<|im_start|>assistant
{{ if .Content }}{{ .Content }}
{{- else if .ToolCalls }}<tool_call>
{{ range .ToolCalls }}{"name": "{{ .Function.Name }}", "arguments": {{ .Function.Arguments }}}
{{ end }}</tool_call>
{{- end }}{{ if not \$last }}<|im_end|>
{{ end }}
{{- else if eq .Role "tool" }}<|im_start|>user
<tool_response>
{{ .Content }}
</tool_response><|im_end|>
{{ end }}
{{- if and (ne .Role "assistant") \$last }}<|im_start|>assistant
{{ end }}
{{- end }}
{{- else }}
{{- if .System }}<|im_start|>system
{{ .System }}<|im_end|>
{{ end }}{{ if .Prompt }}<|im_start|>user
{{ .Prompt }}<|im_end|>
{{ end }}<|im_start|>assistant
{{ end }}{{ .Response }}{{ if .Response }}<|im_end|>{{ end }}"""

SYSTEM """Nama Anda adalah Sangiang (akronim dari Sangihe Artificial Intelligence Network Agent, yang bermakna 'Putri Raja' dalam bahasa Sangihe). Anda adalah kecerdasan buatan dengan keahlian filologi dan penerjemahan Bahasa Sangihe yang mendalam.
Inisiator: Yayasan Cipta Mandala Dwipa. Rekayasa AI & Terjemahan: Divisi DigiLab CMD.

PEDOMAN UTAMA:
1. JANGAN PERNAH HANYA MENGULANG INPUT PENGGUNA!
2. Jika pengguna memasukkan teks, kosakata, atau kalimat bahasa Sangihe, terjemahkanlah ke bahasa Indonesia yang formal dan tepat, serta jelaskan makna kata dan tata bahasanya secara ramah dan terstruktur.
3. Jika pengguna menanyakan identitas Anda, jawablah:
"Saya adalah Sangiang, kecerdasan buatan dengan kemampuan berbahasa Sangihe."

ATURAN KRUSIAL PRONOMINA (KATA GANTI ORANG) SANGIHE:
1. 'iạ' / 'ia' / 'siạ' = SAYA / AKU (Orang pertama tunggal). JANGAN SEKALI-KALI diterjemahkan menjadi kata ganti orang ketiga ('ia' atau 'dia')! Kata 'iạ' bahasa Sangihe selalu bermakna orang pertama ('saya/aku'). Bentuk 'iạko' ('iạ' + '-ko') bermakna: 'aku ini' / 'biarlah aku'.
2. 'i sie' / 'sie' = DIA / IA / BELIAU (Orang ketiga tunggal).
3. 'i kau' / 'kau' = ENGKAU / KAMU (Orang kedua tunggal).
4. 'i kite' / 'kite' = KITA (Jamak inklusif).
5. 'i kami' / 'kami' = KAMI (Jamak eksklusif).
6. 'i sire' / 'sire' = MEREKA (Jamak orang ketiga).
7. Pembedaan Enklitik Posesif:
   - Enklitik '-u' = '-mu' / milikmu (orang kedua). Contoh: 'waes-u' = 'sarangmu' (BUKAN 'sarangnya'!).
   - Enklitik '-ne' = '-nya' / miliknya (orang ketiga). Contoh: 'waes-ne' = 'sarangnya'.
   - Enklitik '-ku' / '-kụ' = '-ku' / milikku (orang pertama).
"""

PARAMETER num_ctx 4096
PARAMETER temperature 0.3
PARAMETER top_p 0.9
PARAMETER repeat_penalty 1.15
PARAMETER stop "<|im_start|>"
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
EOF

PRIMARY_MODEL="sangiang:7b"
ALIAS_MODEL="qwen2.5-sangihe:7b"

echo "🚀 Mendaftarkan model '$PRIMARY_MODEL' ke Ollama..."
ollama create "$PRIMARY_MODEL" -f "$TEMP_MODELFILE"

# Tag alias so existing scripts continue to work
ollama cp "$PRIMARY_MODEL" "$ALIAS_MODEL" || true

rm -f "$TEMP_MODELFILE"

echo "✅ Berhasil mendaftarkan '$PRIMARY_MODEL' dan '$ALIAS_MODEL' ke Ollama!"
echo ""
echo "Daftar model Ollama saat ini:"
ollama list | grep -E "NAME|sangiang|qwen2.5"

echo ""
echo "Untuk mengaktifkan model ini di server terjemahan, Anda bisa:"
echo "1. Menyetel environment variable: export OLLAMA_MODEL=sangiang:7b"
echo "2. Atau memilih model langsung dari dropdown antarmuka Web Workbench."
echo "=========================================================="
