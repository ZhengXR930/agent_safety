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

# DeepSeek models are served by api.deepseek.com directly (DEEPSEEK_API_KEY),
# NOT by the gpt_openapi gateway (which 401s with "no model permission").
DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEEPSEEK_MODELS = {"deepseek-chat", "deepseek-coder", "deepseek-reasoner"}


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


def _patch_developer_role(client: OpenAI) -> OpenAI:
    """Rewrite role='developer' -> 'system' on outgoing chat.completions.

    AgentDojo's OpenAILLM emits the system prompt with role='developer' (new
    OpenAI convention), but the DeepSeek API only accepts system/user/assistant/
    tool and 400s on 'developer'. We wrap create() to normalize it, so the
    official AgentShield pipeline runs unmodified against deepseek-chat.
    """
    orig_create = client.chat.completions.create

    def patched(*args, **kwargs):
        msgs = kwargs.get("messages")
        if msgs:
            for m in msgs:
                if isinstance(m, dict) and m.get("role") == "developer":
                    m["role"] = "system"
        return orig_create(*args, **kwargs)

    client.chat.completions.create = patched  # type: ignore[assignment]
    return client


def client_for_model(model: str | None = None, *, root: Path | None = None) -> OpenAI:
    """Route to the correct backend by model name.

    DeepSeek models go direct to api.deepseek.com (DEEPSEEK_API_KEY); everything
    else goes through the gpt_openapi internal gateway (OPENAI_API_KEY).  Mirrors
    active_defense/code/internal_client.client_for_model so AgentShield and our
    method run the SAME deepseek-chat backend for a fair comparison.
    """
    if model and model in DEEPSEEK_MODELS:
        key = read_config_key("DEEPSEEK_API_KEY", root=root)
        if not key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY (env or config.txt).")
        return _patch_developer_role(OpenAI(base_url=DEEPSEEK_BASE_URL, api_key=key))
    return internal_openai_client(root=root)
