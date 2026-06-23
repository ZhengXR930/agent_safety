"""Internal OpenAI-compatible client for the active-defense MVP.

Reads OPENAI_API_KEY from the repo-root config.txt and routes through the
internal gateway. Supports three backends:
  - legacy gpt_openapi (OpenAI client, Api-Key header) for gpt-4o-mini etc.
  - modelhub azure (AzureOpenAI, azure_endpoint + api_version) for the gpt-5.4/5.5,
    nano/mini, and kimi-k2.6 family. Pick by model name via MODEL_REGISTRY.
  - deepseek (OpenAI client, DEEPSEEK_API_KEY) for deepseek-chat/coder/reasoner.
All backends are API-only (no local GPU).
"""

from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI, AzureOpenAI

# active_defense/code/internal_client.py -> repo root is parents[2]
REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_INTERNAL_BASE_URL = (
    "https://aidp.bytedance.net/api/modelhub/online/v2/crawl/openai/deployments/gpt_openapi"
)
DEFAULT_INTERNAL_MODEL = "gpt-4o-mini-2024-07-18"

AZURE_ENDPOINT = "https://aidp.bytedance.net/api/modelhub/online/v2/crawl"

# Models reachable via the AzureOpenAI client (azure_endpoint + api_version).
# value = api_version. Add more as needed.
MODEL_REGISTRY = {
    "gpt-5.5-2026-04-24": "2024-03-01-preview",
    "gpt-5.4-2026-03-05": "2024-03-01-preview",
    "gpt-5.4-mini-2026-03-17": "2024-02-01",
    "gpt-5.4-nano-2026-03-17": "2024-02-01",
    "kimi-k2.6": "2024-03-01-preview",
}

# DeepSeek models: use official DeepSeek API (OpenAI-compatible).
# key from DEEPSEEK_API_KEY in config.txt.
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODELS = {
    "deepseek-chat",      # DeepSeek-V4 (chat)
    "deepseek-coder",     # DeepSeek-V4 (code)
    "deepseek-reasoner",  # DeepSeek-R1
}


def read_config_key(name: str, root: Path | None = None) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    config_path = (root or REPO_ROOT) / "config.txt"
    if not config_path.exists():
        return None
    for line in config_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == name:
            return value.strip().strip('"').strip("'")
    return None


def internal_openai_client(
    *, api_key_env: str = "OPENAI_API_KEY", base_url: str | None = None, root: Path | None = None
) -> OpenAI:
    """Legacy gpt_openapi client (Api-Key header). For gpt-4o-mini etc."""
    key = read_config_key(api_key_env, root=root)
    if not key:
        raise RuntimeError(f"Missing {api_key_env} (env or {REPO_ROOT / 'config.txt'}).")
    return OpenAI(
        base_url=base_url or os.environ.get("INTERNAL_OPENAI_BASE_URL", DEFAULT_INTERNAL_BASE_URL),
        api_key=key,
        default_headers={"Api-Key": key},
    )


def client_for_model(model: str, *, api_key_env: str = "OPENAI_API_KEY", root: Path | None = None):
    """Return an API client appropriate for `model` (no local GPU).

    - If model is in DEEPSEEK_MODELS -> OpenAI(base_url=DEEPSEEK_BASE_URL, DEEPSEEK_API_KEY).
    - If model is in MODEL_REGISTRY -> AzureOpenAI(azure_endpoint, api_version).
    - Else -> legacy gpt_openapi OpenAI client.
    Use the returned client with `client.chat.completions.create(model=model, ...)`.
    """
    if model in DEEPSEEK_MODELS:
        key = read_config_key("DEEPSEEK_API_KEY", root=root)
        if not key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY (env or config.txt).")
        return OpenAI(base_url=DEEPSEEK_BASE_URL, api_key=key)
    if model in MODEL_REGISTRY:
        key = read_config_key(api_key_env, root=root)
        if not key:
            raise RuntimeError(f"Missing {api_key_env}.")
        return AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=key,
            api_version=MODEL_REGISTRY[model],
            default_headers={"Api-Key": key},
        )
    return internal_openai_client(api_key_env=api_key_env, root=root)

