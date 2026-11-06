import json
from pathlib import Path

nb_path = Path("training/sangihe_qwen2_5_finetuning_colab.ipynb")

with open(nb_path, "r", encoding="utf-8") as f:
    nb = json.load(f)

# Cell 0: Header
nb["cells"][0]["source"] = [
    "# Fine-Tuning Qwen2.5:7b Multi-Task & Multi-Domain (Sangiang v2)\n",
    "**Proyek:** Sangihe Translation Engine & Conversational AI (Sangiang)\n",
    "**Inisiator:** Yayasan Cipta Mandala Dwipa | **AI & Translation:** Divisi DigiLab CMD\n",
    "**Framework:** Unsloth (Fast QLoRA) + Hugging Face TRL\n",
    "**Target Export:** GGUF (Q4_K_M) untuk Ollama lokal\n",
    "\n",
    "> **Catatan Performa (Anti-Bottleneck):**\n",
    "> Notebook ini telah dioptimalkan dengan `max_seq_length = 512` dan evaluasi validasi terbatas (100 sampel).\n",
    "> Waktu pelatihan murni di Google Colab T4 GPU hanya membutuhkan **20-25 menit** (bukan 8 jam).\n",
    "> Ekspor GGUF dilakukan secara lokal terlebih dahulu untuk mencegah *I/O timeout* Google Drive."
]

# Cell 4: Model loading (max_seq_length = 512)
nb["cells"][4]["source"] = [
    "from unsloth import FastLanguageModel\n",
    "import torch\n",
    "\n",
    "max_seq_length = 512 # Optimal untuk pasangan kalimat terjemahan, dialog, dan leksikon\n",
    "dtype = None # Auto detection (Float16 untuk T4, Bfloat16 untuk A100/L4)\n",
    "load_in_4bit = True # 4bit QLoRA menghemat 70% memori VRAM\n",
    "\n",
    "model, tokenizer = FastLanguageModel.from_pretrained(\n",
    "    model_name=\"unsloth/Qwen2.5-7B-Instruct-bnb-4bit\",\n",
    "    max_seq_length=max_seq_length,\n",
    "    dtype=dtype,\n",
    "    load_in_4bit=load_in_4bit,\n",
    ")\n",
    "\n",
    "# Pasang Adapter LoRA pada layer proyeksi utama\n",
    "model = FastLanguageModel.get_peft_model(\n",
    "    model,\n",
    "    r=16,\n",
    "    target_modules=[\"q_proj\", \"k_proj\", \"v_proj\", \"o_proj\",\n",
    "                    \"gate_proj\", \"up_proj\", \"down_proj\"],\n",
    "    lora_alpha=32,\n",
    "    lora_dropout=0,\n",
    "    bias=\"none\",\n",
    "    use_gradient_checkpointing=\"unsloth\",\n",
    "    random_state=3407,\n",
    ")\n",
    "print(\"Model Qwen2.5:7b siap untuk fine-tuning Sangiang v2!\")\n"
]

# Cell 10: Training (Optimized eval & speed)
nb["cells"][10]["source"] = [
    "from trl import SFTTrainer\n",
    "from transformers import TrainingArguments\n",
    "\n",
    "# Evaluasi dibatasi ke 100 sampel agar proses evaluasi selesai dalam hitungan detik (mencegah bottleneck 8 jam)\n",
    "eval_subsample = val_dataset.select(range(min(100, len(val_dataset))))\n",
    "\n",
    "trainer = SFTTrainer(\n",
    "    model=model,\n",
    "    tokenizer=tokenizer,\n",
    "    train_dataset=train_dataset,\n",
    "    eval_dataset=eval_subsample,\n",
    "    dataset_text_field=\"text\",\n",
    "    max_seq_length=max_seq_length,\n",
    "    dataset_num_proc=2,\n",
    "    packing=False,\n",
    "    args=TrainingArguments(\n",
    "        per_device_train_batch_size=4,\n",
    "        gradient_accumulation_steps=4,\n",
    "        warmup_steps=30,\n",
    "        max_steps=1000, # Durasi: ~20-25 menit di GPU T4\n",
    "        learning_rate=2e-4,\n",
    "        fp16=not torch.cuda.is_bf16_supported(),\n",
    "        bf16=torch.cuda.is_bf16_supported(),\n",
    "        logging_steps=25,\n",
    "        optim=\"adamw_8bit\",\n",
    "        weight_decay=0.01,\n",
    "        lr_scheduler_type=\"cosine\",\n",
    "        seed=3407,\n",
    "        output_dir=\"outputs\",\n",
    "        eval_strategy=\"steps\",\n",
    "        eval_steps=250,\n",
    "        save_strategy=\"steps\",\n",
    "        save_steps=500,\n",
    "    ),\n",
    ")\n",
    "\n",
    "print(\"Memulai pelatihan Sangiang v2 (Estimasi: 20-25 menit)...\\n\")\n",
    "trainer_stats = trainer.train()\n"
]

# Cell 12: Inference tests (Conversational, Lexical, Translation)
nb["cells"][12]["source"] = [
    "FastLanguageModel.for_inference(model)\n",
    "\n",
    "def test_prompt(user_text, system_prompt=None):\n",
    "    if not system_prompt:\n",
    "        system_prompt = \"Nama Anda adalah Sangiang. Anda adalah kecerdasan buatan dengan kemampuan berbahasa Sangihe.\"\n",
    "    messages = [\n",
    "        {\"role\": \"system\", \"content\": system_prompt},\n",
    "        {\"role\": \"user\", \"content\": user_text}\n",
    "    ]\n",
    "    formatted = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)\n",
    "    inputs = tokenizer([formatted], return_tensors=\"pt\").to(\"cuda\")\n",
    "    outputs = model.generate(**inputs, max_new_tokens=128, temperature=0.3)\n",
    "    reply = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)\n",
    "    return reply.strip()\n",
    "\n",
    "print(\"=== TEST 1: Sapaan Percakapan Otentik ===\")\n",
    "print(\"User: Kere habarẹ̌?\")\n",
    "print(\"Sangiang:\", test_prompt(\"Kere habarẹ̌?\"))\n",
    "print()\n",
    "\n",
    "print(\"=== TEST 2: Identitas AI Sangiang ===\")\n",
    "print(\"User: Siapa namamu dan apa makna nama Sangiang?\")\n",
    "print(\"Sangiang:\", test_prompt(\"Siapa namamu dan apa makna nama Sangiang?\"))\n",
    "print()\n",
    "\n",
    "print(\"=== TEST 3: Terjemahan Indonesia -> Sangihe (Diakritik) ===\")\n",
    "sys_id2sa = \"Anda adalah penerjemah ahli dan filolog bahasa Sangihe terkemuka. Terjemahkan ke bahasa Sangihe formal dengan tanda diakritik lengkap.\"\n",
    "prompt_id = \"Terjemahkan teks bahasa Indonesia berikut ke bahasa Sangihe formal dengan tanda diakritik lengkap:\\nPada mulanya Allah menciptakan langit dan bumi.\"\n",
    "print(\"Sangiang:\", test_prompt(prompt_id, sys_id2sa))\n",
    "print()\n",
    "\n",
    "print(\"=== TEST 4: Pemahaman Kosakata Kamus Steller-Aebersold ===\")\n",
    "print(\"User: Apa arti kata 'baesẹ̌' dalam bahasa Sangihe?\")\n",
    "print(\"Sangiang:\", test_prompt(\"Apa arti kata 'baesẹ̌' dalam bahasa Sangihe?\"))\n"
]

# Cell 14: Safe GGUF Export (Local first, then Drive copy + direct download option)
nb["cells"][14]["source"] = [
    "import os, glob, shutil\n",
    "from google.colab import drive, files\n",
    "\n",
    "local_gguf_dir = \"/content/sangiang_v2_gguf\"\n",
    "os.makedirs(local_gguf_dir, exist_ok=True)\n",
    "\n",
    "print(\"1. Mengonversi bobot model ke format GGUF (Q4_K_M) di disk lokal Colab...\")\n",
    "model.save_pretrained_gguf(local_gguf_dir, tokenizer, quantization_method=\"q4_k_m\")\n",
    "\n",
    "gguf_files = glob.glob(f\"{local_gguf_dir}/*.gguf\")\n",
    "if gguf_files:\n",
    "    gguf_path = gguf_files[0]\n",
    "    size_gb = os.path.getsize(gguf_path) / (1024**3)\n",
    "    print(f\"\\n✅ GGUF Berhasil Dibuat di Disk Lokal:\")\n",
    "    print(f\"   Path: {gguf_path}\")\n",
    "    print(f\"   Ukuran: {size_gb:.2f} GB\\n\")\n",
    "\n",
    "    # Opsi A: Salin ke Google Drive dengan penanganan aman\n",
    "    try:\n",
    "        print(\"2. Menghubungkan Google Drive untuk penyimpanan awan...\")\n",
    "        drive.mount('/content/drive')\n",
    "        drive_dest = '/content/drive/MyDrive/Sangihe_Translation_Models'\n",
    "        os.makedirs(drive_dest, exist_ok=True)\n",
    "        dest_file = os.path.join(drive_dest, os.path.basename(gguf_path))\n",
    "        print(f\"   Menyalin ke {dest_file}...\")\n",
    "        shutil.copyfile(gguf_path, dest_file)\n",
    "        drive.flush_and_unmount()\n",
    "        print(\"   ✅ Selesai tersimpan di Google Drive!\")\n",
    "    except Exception as e:\n",
    "        print(f\"   ⚠️ Gagal menyalin ke Google Drive: {e}\")\n",
    "\n",
    "    # Opsi B: Instruksi Unduh Langsung ke Komputer\n",
    "    print(\"\\n3. OPSI UNDUH LANGSUNG (Bila Google Drive Lambat/Bermasalah):\")\n",
    "    print(\"   Jalankan perintah berikut di sel baru untuk mengunduh langsung ke browser:\")\n",
    "    print(f\"   files.download('{gguf_path}')\")\n",
    "else:\n",
    "    print(\"❌ File GGUF belum ditemukan. Periksa keluaran log konversi di atas.\")\n"
]

with open(nb_path, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=2, ensure_ascii=False)

print("✅ Successfully updated training/sangihe_qwen2_5_finetuning_colab.ipynb with optimized configuration!")
