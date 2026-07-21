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
import time
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

OPENAI_COMPATIBLE_GATEWAYS = {
    "claude-opus-4-7": ("YUNWU_API_URL", "YUNWU_API_KEY", "https://yunwu.ai/v1"),
}


# Models whose endpoint rejects an explicit `temperature` param.
_NO_TEMP = {"kimi-k2.6", "gpt-5.5-2026-04-24", "gpt-5.4-2026-03-05"}


def _normalize_deepseek_roles(client: OpenAI) -> OpenAI:
    """Adapt the OpenAI `developer` role to DeepSeek's equivalent `system` role."""
    original = client.chat.completions.create

    def create(*args, **kwargs):
        messages = kwargs.get("messages")
        if messages:
            kwargs["messages"] = [
                ({**m, "role": "system"} if isinstance(m, dict) and m.get("role") == "developer" else m)
                for m in messages
            ]
        return original(*args, **kwargs)

    client.chat.completions.create = create  # type: ignore[assignment]
    return client


def _with_api_logging(client, model: str, provider: str):
    """Record exact provider usage without changing the OpenAI-compatible API."""
    try:
        from api.local_api_logger.logger import APILogger
    except ImportError:
        return client
    logger = APILogger(str(Path(__file__).resolve().parents[1] / "api/api_logs"))
    original = client.chat.completions.create

    def create(*args, **kwargs):
        started = time.time()
        try:
            response = original(*args, **kwargs)
        except Exception as exc:
            logger.log_call(
                model=model, request_data=dict(kwargs), response_data={},
                user="active_defense", duration_ms=(time.time() - started) * 1000,
                success=False, error=str(exc), metadata={"provider": provider})
            raise
        dump = getattr(response, "model_dump", None)
        data = dump(mode="json") if callable(dump) else {"result": str(response)}
        logger.log_call(
            model=model, request_data=dict(kwargs), response_data=data,
            user="active_defense", duration_ms=(time.time() - started) * 1000,
            success=True, metadata={"provider": provider})
        return response

    client.chat.completions.create = create
    return client


def chat(client, model: str, prompt: str) -> str:
    """One-shot chat completion (temperature 0 where supported).

    The memory-backed defender roles (Camoufleur / Distinguisher) that need env KNOWLEDGE — not
    filesystem EXPLORATION — answer through this instead of a `claude` subprocess cold-start."""
    kw = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if model not in _NO_TEMP:
        kw["temperature"] = 0.0
    try:
        r = client.chat.completions.create(**kw)
    except Exception:                                    # noqa: BLE001 — retry once without temperature
        kw.pop("temperature", None)
        r = client.chat.completions.create(**kw)
    return (r.choices[0].message.content or "").strip()


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
        return _with_api_logging(
            _normalize_deepseek_roles(OpenAI(base_url=DEEPSEEK_BASE_URL, api_key=key)),
            model, "deepseek")
    if model in OPENAI_COMPATIBLE_GATEWAYS:
        url_env, key_env, default_url = OPENAI_COMPATIBLE_GATEWAYS[model]
        key = read_config_key(key_env, root=root)
        if not key:
            raise RuntimeError(f"Missing {key_env} (env or config.txt).")
        url = os.environ.get(url_env) or read_config_key(url_env, root=root) or default_url
        return _with_api_logging(OpenAI(base_url=url, api_key=key), model, "yunwu")
    if model in MODEL_REGISTRY:
        key = read_config_key(api_key_env, root=root)
        if not key:
            raise RuntimeError(f"Missing {api_key_env}.")
        return _with_api_logging(AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=key,
            api_version=MODEL_REGISTRY[model],
            default_headers={"Api-Key": key},
        ), model, "modelhub")
    return _with_api_logging(
        internal_openai_client(api_key_env=api_key_env, root=root), model, "gpt_openapi")
