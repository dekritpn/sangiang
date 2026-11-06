import hashlib
import os
import sqlite3
import time
from pathlib import Path
from typing import Dict, List, Optional
import httpx

ROOT_DIR = Path(__file__).resolve().parent.parent


def load_dotenv_if_present() -> None:
    """Load key-value pairs from .env in project root if not already in environment."""
    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("\"'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


load_dotenv_if_present()

GEMINI_MODELS = [
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash-lite",
    "gemini-3.5-flash",
]

# Google API retired direct gemini-2.5-flash-lite endpoint in late 2026 in favor of gemini-3.5-flash-lite
GEMINI_API_MODEL_MAP = {
    "gemini-2.5-flash-lite": "gemini-3.5-flash-lite",
    "gemini-2.5-flash": "gemini-3.5-flash",
}


class LocalLLMCache:
    """SQLite-backed local response cache to avoid redundant API calls for identical prompts."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_file = ROOT_DIR / "data" / "llm_cache.sqlite"
        else:
            db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = str(db_file)
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS llm_cache (
                    cache_key TEXT PRIMARY KEY,
                    model TEXT NOT NULL,
                    response TEXT NOT NULL,
                    created_at REAL NOT NULL
                );
                """
            )

    @staticmethod
    def make_key(model: str, system_prompt: str, user_prompt: str, temperature: float) -> str:
        raw = f"{model}|temp={temperature:.2f}|sys={system_prompt}|usr={user_prompt}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def get(self, key: str) -> Optional[str]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.cursor()
                cur.execute("SELECT response FROM llm_cache WHERE cache_key = ?;", (key,))
                row = cur.fetchone()
                return row[0] if row else None
        except Exception:
            return None

    def set(self, key: str, model: str, response: str) -> None:
        if not response:
            return
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO llm_cache (cache_key, model, response, created_at)
                    VALUES (?, ?, ?, ?);
                    """,
                    (key, model, response, time.time()),
                )
        except Exception:
            pass


class OllamaClient:
    """Unified LLM Client supporting Google Gemini API (gemini-2.5-flash-lite) and local Ollama."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: Optional[str] = None,
        timeout: float = 180.0,
        use_cache: bool = True,
    ):
        load_dotenv_if_present()
        self.base_url = base_url.rstrip("/")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY") or ""
        default_env_model = (
            os.getenv("LLM_MODEL")
            or os.getenv("OLLAMA_MODEL")
            or ("gemini-2.5-flash-lite" if self.gemini_api_key else "sangiang:7b")
        )
        self.model = model or default_env_model
        self.timeout = timeout
        self.use_cache = use_cache
        self.cache = LocalLLMCache() if use_cache else None

    @staticmethod
    def is_gemini_model(model_name: str) -> bool:
        return model_name.lower().startswith("gemini-")

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 512,
        num_ctx: int = 4096,
    ) -> str:
        """Generate response using either Gemini API or local Ollama, with local SQLite caching."""
        target_model = model if (model and model.lower() != "sangiang") else self.model
        sys_str = system_prompt or ""

        # 1. Check local SQLite cache first
        cache_key = ""
        if self.cache:
            cache_key = self.cache.make_key(target_model, sys_str, prompt, temperature)
            cached_resp = self.cache.get(cache_key)
            if cached_resp is not None:
                return cached_resp

        # 2. Route to Gemini API if target_model is a Gemini model
        if self.is_gemini_model(target_model):
            result = self._generate_gemini(
                prompt=prompt,
                system_prompt=system_prompt,
                model=target_model,
                temperature=temperature,
                max_tokens=max_tokens,
            )
        else:
            result = self._generate_ollama(
                prompt=prompt,
                system_prompt=system_prompt,
                model=target_model,
                temperature=temperature,
                max_tokens=max_tokens,
                num_ctx=num_ctx,
            )

        # 3. Store in local SQLite cache
        if self.cache and cache_key and result:
            self.cache.set(cache_key, target_model, result)

        return result

    def _generate_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call Google Gemini generateContent REST API."""
        api_key = self.gemini_api_key or os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GEMINI_API_KEY belum diatur di file .env atau environment variable."
            )

        api_model = GEMINI_API_MODEL_MAP.get(model.lower(), model)
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{api_model}:generateContent"
        payload: Dict = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens,
                "topP": 0.9,
            },
        }
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        # Retry with exponential backoff on transient 429/503 errors
        last_err = None
        for attempt in range(3):
            try:
                with httpx.Client(timeout=60.0) as client:
                    resp = client.post(
                        url,
                        params={"key": api_key},
                        json=payload,
                    )
                    if resp.status_code in (429, 503) and attempt < 2:
                        time.sleep(1.5 * (attempt + 1))
                        continue
                    resp.raise_for_status()
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise RuntimeError(f"Gemini tidak mengembalikan kandidat jawaban: {data}")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(p.get("text", "") for p in parts).strip()
                    return text
            except httpx.HTTPError as e:
                last_err = e
                if attempt < 2:
                    time.sleep(1.0)
                    continue
        raise RuntimeError(f"Gemini API gagal ({model}): {last_err}")

    def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: str,
        temperature: float,
        max_tokens: int,
        num_ctx: int,
    ) -> str:
        """Generate response using local Ollama /api/generate."""
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "60m",
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
                "num_ctx": num_ctx,
                "top_p": 0.9,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            with httpx.Client(timeout=self.timeout) as client:
                resp = client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "").strip()
        except httpx.ReadTimeout:
            raise RuntimeError(
                f"Ollama generation timed out after {self.timeout}s ({model})."
            )
        except httpx.HTTPError as e:
            raise RuntimeError(f"Ollama generation failed: {e}")

    def list_models(self) -> List[str]:
        """Fetch list of available models (Gemini models + local Ollama models)."""
        models: List[str] = []
        if self.gemini_api_key:
            models.extend(GEMINI_MODELS)
        try:
            with httpx.Client(timeout=2.5) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    for m in data.get("models", []):
                        name = m.get("name", "")
                        if name and name not in models:
                            models.append(name)
        except Exception:
            pass
        if not models:
            models.append(self.model)
        return models

    def is_alive(self) -> bool:
        """Check if either Gemini API key is configured or local Ollama service is reachable."""
        if self.gemini_api_key:
            return True
        try:
            with httpx.Client(timeout=3.0) as client:
                resp = client.get(f"{self.base_url}/api/tags")
                return resp.status_code == 200
        except Exception:
            return False
