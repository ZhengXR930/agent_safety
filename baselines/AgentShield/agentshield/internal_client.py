"""Internal OpenAI-compatible client helpers for AgentShield.

AgentShield upstream uses a bare ``OpenAI()`` client that talks to api.openai.com.
In this environment we route through the internal OpenAI-compatible gateway,
reusing the same convention as ``adapter_defense/code/internal_openai_compat.py``:
the API key is read from the repo-root ``config.txt`` and passed via an
``Api-Key`` header against the internal base URL.
"""

from __future__ import annotations

import os
from pathlib import Path

from openai import OpenAI

# baselines/AgentShield/agentshield/internal_client.py -> repo root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_INTERNAL_BASE_URL = (
    "https://aidp.bytedance.net/api/modelhub/online/v2/crawl/openai/deployments/gpt_openapi"
)
DEFAULT_INTERNAL_MODEL = "gpt-4o-mini-2024-07-18"


def read_config_key(name: str, root: Path | None = None) -> str | None:
    """Read a key from the environment, else from repo-root config.txt."""
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
    *,
    api_key_env: str = "OPENAI_API_KEY",
    base_url: str | None = None,
    api_key_header: bool = True,
    root: Path | None = None,
) -> OpenAI:
    """Build an OpenAI client pointed at the internal gateway."""
    key = read_config_key(api_key_env, root=root)
    if not key:
        raise RuntimeError(
            f"Missing {api_key_env}. Set it in the environment or in {REPO_ROOT / 'config.txt'}."
        )
    headers = {"Api-Key": key} if api_key_header else None
    return OpenAI(
        base_url=base_url or os.environ.get("INTERNAL_OPENAI_BASE_URL", DEFAULT_INTERNAL_BASE_URL),
        api_key=key,
        default_headers=headers,
    )
