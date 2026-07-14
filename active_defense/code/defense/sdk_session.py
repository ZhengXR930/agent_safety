"""In-process agent Session via the OpenAI Agents SDK, pointed at DeepSeek (OpenAI-compatible endpoint).

Duck-compatible with subagent.Session / ApiSession (.ask / .ask_json), so any defender role swaps in with
no other change.  The multi-step Runner loop gives the ROBUSTNESS a one-shot API call lacks (e.g. reasoning
tool-by-tool to classify a fetch tool named 'get_webpage' correctly) — with NO subprocess cold-start
(unlike the coco CLI), so it is feasible even in hot loops (Distinguisher x certify_trials).

Model access: only DeepSeek is directly reachable here (strong models 401 on the gateway; openrouter only
via coco CLI).  DeepSeek speaks the OpenAI Chat Completions API -> set_default_openai_api('chat_completions').
"""
from __future__ import annotations

import os

from .subagent import SubagentError, _extract_json

_READY = False


def _ensure_configured() -> None:
    """Point the Agents SDK at DeepSeek's OpenAI-compatible endpoint (once per process)."""
    global _READY
    if _READY:
        return
    from openai import AsyncOpenAI
    from agents import set_default_openai_client, set_default_openai_api, set_tracing_disabled
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    client = AsyncOpenAI(base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"), api_key=key)
    set_default_openai_client(client)
    set_default_openai_api("chat_completions")   # DeepSeek = chat-completions, not the Responses API
    set_tracing_disabled(True)                   # no OpenAI tracing backend available here
    _READY = True


class SdkSession:
    """One defender role as an in-process OpenAI-Agents-SDK agent on DeepSeek."""

    def __init__(self, name: str, cwd=None, model: str = "deepseek-chat", timeout: int = 200,
                 context: str = ""):
        _ensure_configured()
        from pathlib import Path
        from agents import Agent
        self.name = name
        self.model = model
        self.timeout = timeout
        self.context = context               # EnvMemory slice prepended to each ask (ApiSession-compatible)
        tools = []
        if cwd is not None:                          # exploration roles (Surveyor): real file tools
            from agents import function_tool
            base = Path(cwd)

            @function_tool
            def list_files(subdir: str = "") -> str:
                """List the files under the working directory (optionally within a subdirectory)."""
                d = base / subdir
                if not d.exists():
                    return f"(no such dir: {subdir})"
                return "\n".join(sorted(str(p.relative_to(base)) for p in d.rglob("*")
                                        if p.is_file()))[:4000] or "(empty)"

            @function_tool
            def read_file(path: str) -> str:
                """Read a UTF-8 text file (path relative to the working directory)."""
                p = base / path
                if not p.is_file():
                    return f"(no such file: {path})"
                try:
                    return p.read_text(encoding="utf-8", errors="ignore")[:12000]
                except OSError as e:
                    return f"(read error: {e})"

            tools = [list_files, read_file]
        # exploration roles (with file tools) need many turns: list + read N files + reason -> generous cap;
        # reasoning-only roles finish in a couple of turns.
        self._max_turns = 40 if tools else 8
        self._agent = Agent(
            name=name,
            instructions=(f"You are the {name} role in a security-research pipeline. Reason carefully, "
                          f"step by step, before answering. " +
                          ("Use list_files / read_file to EXPLORE the working directory. Read only the files "
                           "you NEED, then STOP exploring and produce the answer — do not exhaust your turns. "
                           if tools else "") +
                          "When asked for JSON, output ONLY the JSON."),
            model=model, tools=tools)

    def ask(self, prompt: str) -> str:
        from agents import Runner
        full = (self.context + "\n\n" + prompt) if self.context else prompt
        try:
            r = Runner.run_sync(self._agent, full, max_turns=self._max_turns)
            return (r.final_output or "") if r is not None else ""
        except Exception as e:  # noqa: BLE001 — MaxTurnsExceeded / transient: never crash the pipeline
            # salvage any partial final text carried on the exception, else empty (caller retries / safe-defaults)
            for attr in ("final_output", "last_output", "output"):
                val = getattr(e, attr, None)
                if val:
                    return str(val)
            return ""

    def ask_json(self, prompt: str, *, retries: int = 1):
        out = self.ask(prompt)
        for _ in range(retries + 1):
            parsed = _extract_json(out)
            if parsed is not None:
                return parsed
            out = self.ask("Your previous reply was not valid JSON. Reply with ONLY the JSON object, "
                           "no prose, no code fences.")
        raise SubagentError(f"{self.name}: no valid JSON after {retries + 1} attempts")
