#!/usr/bin/env python3
"""
Builds the unified `public/` static output directory for Cloudflare Pages.
- `public/index.html` & `public/static/*` -> Sangiang Translation Engine (translate.sangihe.org)
- `public/chat/index.html` & `public/chat/static/*` -> Sangiang Chatbot (chat.sangihe.org or /chat/)
"""

import shutil
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = ROOT_DIR / "public"
TRANSLATE_STATIC = ROOT_DIR / "static"
CHATBOT_STATIC = ROOT_DIR / "chatbot" / "static"


def build_public():
    if PUBLIC_DIR.exists():
        shutil.rmtree(PUBLIC_DIR)

    # 1. Copy Sangiang Translation Engine static files to public/ and public/static/
    (PUBLIC_DIR / "static").mkdir(parents=True, exist_ok=True)
    for item in TRANSLATE_STATIC.iterdir():
        if item.is_file():
            shutil.copy2(item, PUBLIC_DIR / "static" / item.name)
    shutil.copy2(TRANSLATE_STATIC / "index.html", PUBLIC_DIR / "index.html")

    # 2. Copy Sangiang Chatbot static files to public/chat/ and public/chat/static/
    (PUBLIC_DIR / "chat" / "static").mkdir(parents=True, exist_ok=True)
    for item in CHATBOT_STATIC.iterdir():
        if item.is_file():
            shutil.copy2(item, PUBLIC_DIR / "chat" / "static" / item.name)

    # Adjust asset paths in public/chat/index.html and public/chat/static/app.js so they work both on
    # chat.sangihe.org (via _middleware.js) and on /chat/ path directly
    chat_index = (CHATBOT_STATIC / "index.html").read_text(encoding="utf-8")
    chat_index_patched = chat_index.replace('"/static/', '"/chat/static/')
    (PUBLIC_DIR / "chat" / "index.html").write_text(chat_index_patched, encoding="utf-8")

    chat_app_js = (CHATBOT_STATIC / "app.js").read_text(encoding="utf-8")
    chat_app_js_patched = chat_app_js.replace('"/static/sangiang.jpeg"', '"/chat/static/sangiang.jpeg"')
    (PUBLIC_DIR / "chat" / "static" / "app.js").write_text(chat_app_js_patched, encoding="utf-8")

    print(f"[+] Built unified Cloudflare Pages output directory at: {PUBLIC_DIR}")


if __name__ == "__main__":
    build_public()

