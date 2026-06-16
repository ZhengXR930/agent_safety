"""Internal OpenAI-compatible client helpers used by benchmark adapters."""

from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INTERNAL_BASE_URL = (
    "https://aidp.bytedance.net/api/modelhub/online/v2/crawl/openai/deployments/gpt_openapi"
)
DEFAULT_INTERNAL_MODEL = "gpt-5.4-2026-03-05"


def read_config_key(name: str, root: Path | None = None) -> str | None:
    if os.environ.get(name):
        return os.environ[name]
    config_path = (root or ROOT) / "config.txt"
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
    *,
    api_key_env: str = "OPENAI_API_KEY",
    base_url: str | None = None,
    api_key_header: bool = True,
    root: Path | None = None,
) -> OpenAI:
    key = read_config_key(api_key_env, root=root)
    if not key:
        raise RuntimeError(f"Missing {api_key_env}")
    headers = {"Api-Key": key} if api_key_header else None
    return OpenAI(
        base_url=base_url or os.environ.get("INTERNAL_OPENAI_BASE_URL", DEFAULT_INTERNAL_BASE_URL),
        api_key=key,
        default_headers=headers,
    )

