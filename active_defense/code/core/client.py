"""Internal OpenAI-compatible client for the active-defense MVP.

Reads OPENAI_API_KEY from the repo-root config.txt and routes through the
internal gateway. Supports three backends:
  - legacy gpt_openapi (OpenAI client, Api-Key header) for gpt-4o-mini etc.
  - modelhub azure (AzureOpenAI, azure_endpoint + api_version) for the gpt-5.4/5.5,
    nano/mini, and kimi-k2.6 family. Pick by model name via MODEL_REGISTRY.
  - deepseek (OpenAI client, DEEPSEEK_API_KEY), with stable logical model names.
All backends are API-only (no local GPU).
"""

from __future__ import annotations

from functools import lru_cache
import os
import threading
import time
from pathlib import Path

from openai import OpenAI, AzureOpenAI

# active_defense/code/core/client.py -> agent_safety root is parents[3]
REPO_ROOT = Path(__file__).resolve().parents[3]


def _cache_split(usage, prompt_tokens: int) -> tuple[int, int]:
    """Return (cache_hit_tokens, cache_miss_tokens) for a usage object.

    DeepSeek reports prefix-cache accounting directly via
    ``prompt_cache_hit_tokens`` / ``prompt_cache_miss_tokens``. OpenAI-style
    backends expose cached prompt tokens via ``prompt_tokens_details.cached_tokens``.
    We normalise both into (hit, miss) where hit+miss == prompt_tokens.
    Missing fields degrade gracefully to (0, prompt_tokens).
    """
    if not usage:
        return 0, int(prompt_tokens or 0)
    hit = getattr(usage, "prompt_cache_hit_tokens", None)
    miss = getattr(usage, "prompt_cache_miss_tokens", None)
    if hit is None:
        details = getattr(usage, "prompt_tokens_details", None)
        if details is not None:
            cached = getattr(details, "cached_tokens", None)
            if cached is None and isinstance(details, dict):
                cached = details.get("cached_tokens")
            if cached is not None:
                hit = cached
    hit = int(hit or 0)
    if miss is None:
        miss = int(prompt_tokens or 0) - hit
    miss = int(miss or 0)
    if miss < 0:
        miss = 0
    return hit, miss


# --- Process-wide token/usage accounting (efficiency stats) -----------------
# Every LLM call in this project ultimately goes through a client's
# `chat.completions.create` (sync via client_for_model, async via
# agent_sdk_model).  We install a lightweight wrapper on both so a single
# accumulator captures provider-reported token usage without estimation.
class _UsageTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.reset()

    def reset(self) -> None:
        with self._lock:
            self.calls = 0
            self.prompt_tokens = 0
            self.completion_tokens = 0
            self.total_tokens = 0
            # Provider-side prefix cache accounting. cache_hit is the portion of
            # prompt_tokens that was served from a cached prefix (billed at a
            # steep discount, ~10% on DeepSeek); cache_miss is the freshly
            # processed remainder. billable_prompt_tokens is a discounted proxy
            # (miss + 0.1*hit) so efficiency accounting reflects true cost.
            self.cache_hit_tokens = 0
            self.cache_miss_tokens = 0
            self.by_model = {}

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "calls": self.calls,
                "prompt_tokens": self.prompt_tokens,
                "completion_tokens": self.completion_tokens,
                "total_tokens": self.total_tokens,
                "cache_hit_tokens": self.cache_hit_tokens,
                "cache_miss_tokens": self.cache_miss_tokens,
                "by_model": {k: dict(v) for k, v in self.by_model.items()},
            }

    def record(self, response, model: str | None = None) -> None:
        usage = getattr(response, "usage", None)
        pt = int(getattr(usage, "prompt_tokens", 0) or 0) if usage else 0
        ct = int(getattr(usage, "completion_tokens", 0) or 0) if usage else 0
        tt = int(getattr(usage, "total_tokens", 0) or 0) if usage else 0
        if usage and not tt:
            tt = pt + ct
        hit, miss = _cache_split(usage, pt)
        key = str(model or getattr(response, "model", "") or "unknown")
        with self._lock:
            self.calls += 1
            self.prompt_tokens += pt
            self.completion_tokens += ct
            self.total_tokens += tt
            self.cache_hit_tokens += hit
            self.cache_miss_tokens += miss
            slot = self.by_model.setdefault(
                key, {"calls": 0, "prompt_tokens": 0,
                      "completion_tokens": 0, "total_tokens": 0,
                      "cache_hit_tokens": 0, "cache_miss_tokens": 0})
            slot["calls"] += 1
            slot["prompt_tokens"] += pt
            slot["completion_tokens"] += ct
            slot["total_tokens"] += tt
            slot["cache_hit_tokens"] = slot.get("cache_hit_tokens", 0) + hit
            slot["cache_miss_tokens"] = slot.get("cache_miss_tokens", 0) + miss

    def record_raw(self, model: str, prompt_tokens: int = 0,
                   completion_tokens: int = 0,
                   total_tokens: int = 0,
                   cache_hit_tokens: int = 0) -> None:
        """Record token counts obtained outside the OpenAI response object.

        Runtimes that call the model through a different client stack (e.g.
        MSB's langchain ChatDeepSeek/MCPAgent) surface usage via their own
        callback metadata rather than an OpenAI ``response.usage``. This lets
        those paths feed the same global accumulator so efficiency accounting
        stays uniform across benchmarks.
        """
        pt = int(prompt_tokens or 0)
        ct = int(completion_tokens or 0)
        tt = int(total_tokens or 0) or (pt + ct)
        hit = int(cache_hit_tokens or 0)
        if hit > pt:
            hit = pt
        miss = pt - hit
        key = str(model or "unknown")
        with self._lock:
            self.calls += 1
            self.prompt_tokens += pt
            self.completion_tokens += ct
            self.total_tokens += tt
            self.cache_hit_tokens += hit
            self.cache_miss_tokens += miss
            slot = self.by_model.setdefault(
                key, {"calls": 0, "prompt_tokens": 0,
                      "completion_tokens": 0, "total_tokens": 0,
                      "cache_hit_tokens": 0, "cache_miss_tokens": 0})
            slot["calls"] += 1
            slot["prompt_tokens"] += pt
            slot["completion_tokens"] += ct
            slot["total_tokens"] += tt
            slot["cache_hit_tokens"] = slot.get("cache_hit_tokens", 0) + hit
            slot["cache_miss_tokens"] = slot.get("cache_miss_tokens", 0) + miss


# Global token/usage accumulator shared across every client wrapper in this
# process. Referenced by _with_usage_accounting, the langchain callback, and
# the atexit dump; must be instantiated at module load.
USAGE = _UsageTracker()


def _maybe_install_usage_dump() -> None:
    """If USAGE_DUMP_PATH is set, write USAGE.snapshot() at process exit.

    This lets any benchmark runner emit clean per-model token accounting for
    efficiency measurement without editing each runner's CLI.
    """
    path = os.environ.get("USAGE_DUMP_PATH")
    if not path:
        return
    import atexit
    import json as _json

    def _dump():
        try:
            # Allow "{pid}" templating so concurrently-spawned subprocess
            # runners (SkillInject/SCR fan out one process per pair) each write
            # a distinct usage file instead of clobbering a shared path.
            resolved = path.replace("{pid}", str(os.getpid()))
            Path(resolved).parent.mkdir(parents=True, exist_ok=True)
            Path(resolved).write_text(
                _json.dumps(USAGE.snapshot(), ensure_ascii=False, indent=2),
                encoding="utf-8")
        except Exception:
            pass

    atexit.register(_dump)


_maybe_install_usage_dump()


def langchain_usage_callback(model: str | None = None):
    """Return a langchain callback handler that feeds USAGE from LLM results.

    MSB runs its target/defense agent through langchain ``ChatDeepSeek`` +
    ``MCPAgent``, which never touches the OpenAI client wrapped by
    ``_with_usage_accounting``. Attaching this handler to the chat model routes
    that runtime's provider-reported token usage into the same global
    accumulator so efficiency accounting is uniform across benchmarks.
    """
    try:
        from langchain_core.callbacks import BaseCallbackHandler
    except Exception:  # langchain not importable in this process
        return None

    class _UsageCallback(BaseCallbackHandler):
        def on_llm_end(self, response, **kwargs):  # noqa: D401
            try:
                out = getattr(response, "llm_output", None) or {}
                tu = out.get("token_usage") or {}
                name = out.get("model_name") or model or "unknown"
                pt = int(tu.get("prompt_tokens", 0) or 0)
                ct = int(tu.get("completion_tokens", 0) or 0)
                tt = int(tu.get("total_tokens", 0) or 0)
                # DeepSeek surfaces prefix-cache hits either as a top-level
                # prompt_cache_hit_tokens or nested under prompt_tokens_details.
                hit = int(tu.get("prompt_cache_hit_tokens", 0) or 0)
                if not hit:
                    ptd = tu.get("prompt_tokens_details") or {}
                    if isinstance(ptd, dict):
                        hit = int(ptd.get("cached_tokens", 0) or 0)
                if pt or ct or tt:
                    USAGE.record_raw(name, pt, ct, tt, cache_hit_tokens=hit)
                    return
                # Fallback: sum per-generation usage_metadata.
                for gens in getattr(response, "generations", []) or []:
                    for g in gens:
                        msg = getattr(g, "message", None)
                        um = getattr(msg, "usage_metadata", None) if msg else None
                        if um:
                            USAGE.record_raw(
                                name,
                                int(um.get("input_tokens", 0) or 0),
                                int(um.get("output_tokens", 0) or 0),
                                int(um.get("total_tokens", 0) or 0))
            except Exception:
                pass

    return _UsageCallback()


def _with_usage_accounting(client):
    """Wrap a sync or async client's create() to feed the global USAGE tracker."""
    try:
        original = client.chat.completions.create
    except AttributeError:
        return client
    if getattr(original, "_usage_wrapped", False):
        return client
    import inspect

    # The OpenAI SDK's create() is a decorated method, so
    # inspect.iscoroutinefunction() reports False even for AsyncOpenAI. Detect
    # the async case at runtime by checking whether the call returns an
    # awaitable, so token accounting works on both sync and async clients
    # (including every agent_sdk_model path).
    def create(*args, **kwargs):
        result = original(*args, **kwargs)
        if inspect.isawaitable(result):
            async def _await():
                response = await result
                try:
                    USAGE.record(response, kwargs.get("model"))
                except Exception:  # never let accounting break a call
                    pass
                return response
            return _await()
        try:
            USAGE.record(result, kwargs.get("model"))
        except Exception:
            pass
        return result

    create._usage_wrapped = True  # type: ignore[attr-defined]
    client.chat.completions.create = create  # type: ignore[assignment]
    return client

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
    "deepseek-chat",      # Stable experiment alias; transported as deepseek-v4-flash.
    "deepseek-coder",     # Stable experiment alias; transported as deepseek-v4-pro.
    "deepseek-reasoner",  # DeepSeek-R1
    "deepseek-v4-pro",
    "deepseek-v4-flash",
}
DEEPSEEK_TRANSPORT_MODELS = {
    "deepseek-chat": "deepseek-v4-flash",
    "deepseek-coder": "deepseek-v4-pro",
}

OPENAI_COMPATIBLE_GATEWAYS = {
    "claude-opus-4-7": ("YUNWU_API_URL", "YUNWU_API_KEY", "https://yunwu.ai/v1"),
    "gpt-5.6-sol": ("TOTOKENS_API_URL", "TOTOKENS_API_KEY", "https://totokens.cc"),
}


# Models whose endpoint rejects an explicit `temperature` param.
_NO_TEMP = {"kimi-k2.6", "gpt-5.6-sol", "gpt-5.5-2026-04-24", "gpt-5.4-2026-03-05"}


def _openai_gateway_headers(model: str, root: Path | None = None) -> dict | None:
    """Provider-specific headers for OpenAI-compatible non-modelhub gateways."""
    if model == "gpt-5.6-sol":
        actor = (os.environ.get("TOTOKENS_ACTOR_AUTH") or
                 read_config_key("TOTOKENS_ACTOR_AUTH", root=root) or
                 "local-image-extension")
        return {"x-openai-actor-authorization": actor}
    return None


def _normalize_model_params(client, model: str):
    """Remove request parameters that the selected endpoint does not support.

    Callers such as AgentDojo legitimately choose their own sampling defaults.
    ModelHub's GPT-5.x deployments, however, reject any explicit non-default
    temperature.  Normalize this transport-level incompatibility centrally so
    every caller sees the same OpenAI-compatible interface.
    """
    if model not in _NO_TEMP:
        return client
    original = client.chat.completions.create

    def create(*args, **kwargs):
        kwargs.pop("temperature", None)
        return original(*args, **kwargs)

    client.chat.completions.create = create
    return client



def _normalize_thinking_disabled(client, model: str):
    """Disable hidden reasoning for OpenAI-compatible models that otherwise
    spend completion budget in provider-specific reasoning_content.

    This is a transport compatibility shim, not a defense-policy change. It
    preserves caller arguments and only supplies a default when the request did
    not already choose a thinking mode.
    """
    if not str(model).lower().startswith("glm-"):
        return client
    original = client.chat.completions.create

    def create(*args, **kwargs):
        body = dict(kwargs.get("extra_body") or {})
        if "enable_thinking" not in body and "thinking" not in body:
            body["enable_thinking"] = False
        kwargs["extra_body"] = body
        return original(*args, **kwargs)

    client.chat.completions.create = create  # type: ignore[assignment]
    return client

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


def _normalize_deepseek_model(client: OpenAI, logical_model: str) -> OpenAI:
    """Translate stable experiment aliases to names accepted by the endpoint."""
    transport_model = DEEPSEEK_TRANSPORT_MODELS.get(logical_model, logical_model)
    if transport_model == logical_model:
        return client
    original = client.chat.completions.create

    def create(*args, **kwargs):
        if kwargs.get("model") == logical_model:
            kwargs["model"] = transport_model
        return original(*args, **kwargs)

    client.chat.completions.create = create  # type: ignore[assignment]
    return client


def _with_api_logging(client, model: str, provider: str):
    """Record exact provider usage without changing the OpenAI-compatible API."""
    try:
        from api.local_api_logger.logger import APILogger
    except ImportError:
        return _with_usage_accounting(client)
    logger = APILogger(str(Path(__file__).resolve().parents[2] / "api/api_logs"))
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
        try:
            USAGE.record(response, model)
        except Exception:
            pass
        return response

    client.chat.completions.create = create
    return client


def chat(
    client,
    model: str,
    prompt: str,
    *,
    thinking: bool | str | None = None,
    max_tokens: int | None = None,
    response_format: dict | None = None,
) -> str:
    """One-shot chat completion (temperature 0 where supported).

    The memory-backed defender roles (Camoufleur / Distinguisher) that need env KNOWLEDGE — not
    filesystem EXPLORATION — answer through this instead of a `claude` subprocess cold-start."""
    kw = {"model": model, "messages": [{"role": "user", "content": prompt}]}
    if model not in _NO_TEMP:
        kw["temperature"] = 0.0
    if thinking is False and model in DEEPSEEK_MODELS:
        # Compact structured defender roles do not benefit from tens of
        # thousands of hidden reasoning tokens.  Keep this opt-in so the
        # task and placement Agents retain their configured reasoning.
        kw["extra_body"] = {"thinking": {"type": "disabled"}}
    elif thinking == "brief" and model in DEEPSEEK_MODELS:
        # This provider-specific mode preserves a short reasoning pass before
        # the answer.  Unlike max_tokens, it does not spend the whole budget
        # on hidden reasoning and then truncate the JSON body.
        kw["extra_body"] = {"enable_thinking": False}
    if max_tokens is not None:
        kw["max_tokens"] = max_tokens
    if response_format is not None:
        kw["response_format"] = dict(response_format)
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
            _normalize_deepseek_model(
                _normalize_deepseek_roles(OpenAI(base_url=DEEPSEEK_BASE_URL, api_key=key, timeout=90.0)),
                model,
            ),
            model, "deepseek")
    if model in OPENAI_COMPATIBLE_GATEWAYS:
        url_env, key_env, default_url = OPENAI_COMPATIBLE_GATEWAYS[model]
        key = read_config_key(key_env, root=root)
        if not key:
            raise RuntimeError(f"Missing {key_env} (env or config.txt).")
        url = os.environ.get(url_env) or read_config_key(url_env, root=root) or default_url
        headers = _openai_gateway_headers(model, root=root)
        provider = "totokens" if model == "gpt-5.6-sol" else "yunwu"
        client = OpenAI(base_url=url, api_key=key, default_headers=headers)
        return _with_api_logging(_normalize_model_params(client, model), model, provider)
    if model in MODEL_REGISTRY:
        key = read_config_key(api_key_env, root=root)
        if not key:
            raise RuntimeError(f"Missing {api_key_env}.")
        client = AzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=key,
            api_version=MODEL_REGISTRY[model],
            default_headers={"Api-Key": key},
        )
        return _with_api_logging(_normalize_model_params(client, model), model, "modelhub")
    return _with_api_logging(
        _normalize_model_params(
            _normalize_thinking_disabled(
                internal_openai_client(api_key_env=api_key_env, root=root), model),
            model),
        model, "gpt_openapi")

@lru_cache(maxsize=16)
def agent_sdk_model(model: str, *, api_key_env: str = "OPENAI_API_KEY",
                    root: Path | None = None):
    """Build an OpenAI Agents SDK model for any registered project backend.

    Defender roles use this boundary instead of issuing chat-completion calls
    themselves.  Provider credentials and transport aliases remain centralized.
    """
    from agents import OpenAIChatCompletionsModel
    from openai import AsyncAzureOpenAI, AsyncOpenAI

    if model in DEEPSEEK_MODELS:
        key = read_config_key("DEEPSEEK_API_KEY", root=root)
        if not key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY (environment or config.txt).")
        client = _with_usage_accounting(
            AsyncOpenAI(base_url=DEEPSEEK_BASE_URL, api_key=key, timeout=90.0))
        return OpenAIChatCompletionsModel(
            DEEPSEEK_TRANSPORT_MODELS.get(model, model), client)
    if model in OPENAI_COMPATIBLE_GATEWAYS:
        url_env, key_env, default_url = OPENAI_COMPATIBLE_GATEWAYS[model]
        key = read_config_key(key_env, root=root)
        if not key:
            raise RuntimeError(f"Missing {key_env} (environment or config.txt).")
        url = os.environ.get(url_env) or read_config_key(
            url_env, root=root) or default_url
        headers = _openai_gateway_headers(model, root=root)
        client = AsyncOpenAI(base_url=url, api_key=key, default_headers=headers, timeout=90.0)
        return OpenAIChatCompletionsModel(
            model, _with_usage_accounting(_normalize_model_params(client, model)))
    if model in MODEL_REGISTRY:
        key = read_config_key(api_key_env, root=root)
        if not key:
            raise RuntimeError(f"Missing {api_key_env}.")
        client = AsyncAzureOpenAI(
            azure_endpoint=AZURE_ENDPOINT,
            api_key=key,
            api_version=MODEL_REGISTRY[model],
            default_headers={"Api-Key": key},
            timeout=90.0,
        )
        return OpenAIChatCompletionsModel(model, _with_usage_accounting(client))
    key = read_config_key(api_key_env, root=root)
    if not key:
        raise RuntimeError(
            f"Missing {api_key_env} (environment or repository config.txt).")
    client = _with_usage_accounting(_normalize_thinking_disabled(AsyncOpenAI(
        base_url=os.environ.get(
            "INTERNAL_OPENAI_BASE_URL", DEFAULT_INTERNAL_BASE_URL),
        api_key=key, default_headers={"Api-Key": key}, timeout=90.0), model))
    return OpenAIChatCompletionsModel(model, client)
