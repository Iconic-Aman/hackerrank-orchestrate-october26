"""
Minimal synchronous OpenRouter client.

Reads OPENROUTER_API_KEY, OPENROUTER_MODEL, OPENROUTER_API_URL from env.
Falls back to a .env file in the backend directory if env vars are not set.
No third-party dotenv library required.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

import httpx


# ---------------------------------------------------------------------------
# Manual .env loader (no python-dotenv dependency)
# ---------------------------------------------------------------------------
def _load_env_file() -> None:
    """Parse backend/.env and set missing env vars (does NOT overwrite existing ones)."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    if not env_path.exists():
        return
    with open(env_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


_load_env_file()


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------
TIMEOUT = 30  # seconds


def chat_completion(
    prompt: str,
    system: str = "",
    temperature: float = 0.0,
    max_tokens: int = 256,
) -> Optional[str]:
    """
    Send a single-turn chat completion to OpenRouter.

    Returns the assistant message text, or None if the call fails
    (network error, missing key, bad response).
    """
    api_key = os.getenv("OPENROUTER_API_KEY", "")
    model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
    base_url = os.getenv("OPENROUTER_API_URL", "https://openrouter.ai/api/v1")

    if not api_key:
        return None  # graceful: caller falls back to regex

    url = base_url.rstrip("/") + "/chat/completions"
    messages: list[dict] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/hackerrank-orchestrate",
        "X-Title": "Ghost Data Still Exists — Deletion Audit",
    }

    try:
        resp = httpx.post(url, json=payload, headers=headers, timeout=TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except Exception:
        return None  # graceful fallback
