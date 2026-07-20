"""In-process agent Session via the OpenAI Agents SDK, pointed at DeepSeek (OpenAI-compatible endpoint).

Provides the shared `.ask/.ask_json` role interface. The multi-step Runner loop gives the robustness a
one-shot API call lacks (e.g. reasoning
tool-by-tool to classify a fetch tool named 'get_webpage' correctly) — with NO subprocess cold-start
(unlike the coco CLI), so it is feasible even in hot loops (Distinguisher x certify_trials).

Model access: only DeepSeek is directly reachable here (strong models 401 on the gateway; openrouter only
via coco CLI).  DeepSeek speaks the OpenAI Chat Completions API -> set_default_openai_api('chat_completions').
"""
from __future__ import annotations

import json
import os
import re


class SubagentError(RuntimeError):
    """A defender role failed to produce a usable structured result."""


def _extract_json(text: str):
    match = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    chunk = match.group(1).strip() if match else None
    if chunk is None:
        match = re.search(r"(\[.*\]|\{.*\})", text, re.S)
        chunk = match.group(1) if match else None
    if not chunk:
        return None
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        return None


class ApiSession:
    """One-shot client-backed session used where an explicit project client is required."""

    def __init__(self, client, model: str, context: str = ""):
        self.client, self.model, self.context = client, model, context

    def ask(self, prompt: str) -> str:
        from code.internal_client import chat
        full = (self.context + "\n\n" + prompt) if self.context else prompt
        return chat(self.client, self.model, full)

    def ask_json(self, prompt: str) -> dict:
        parsed = _extract_json(self.ask(prompt))
        if parsed is None:
            raise SubagentError("ApiSession: no JSON in response")
        return parsed

_READY = False


def _ensure_configured() -> None:
    """Point the Agents SDK at DeepSeek's OpenAI-compatible endpoint (once per process)."""
    global _READY
    if _READY:
        return
    from openai import AsyncOpenAI
    from agents import set_default_openai_client, set_default_openai_api, set_tracing_disabled
    # Use the same credential resolution as the synchronous defender/benchmark clients.  Otherwise one
    # process can initialize its main client from config.txt while the Agents SDK fails merely because the
    # equivalent environment variable was not exported in this shell.
    from code.internal_client import read_config_key
    key = read_config_key("DEEPSEEK_API_KEY") or read_config_key("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("Missing DeepSeek credential (environment or repository config.txt).")
    client = AsyncOpenAI(base_url=os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com"), api_key=key)
    set_default_openai_client(client)
    set_default_openai_api("chat_completions")   # DeepSeek = chat-completions, not the Responses API
    set_tracing_disabled(True)                   # no OpenAI tracing backend available here
    _READY = True


class SdkSession:
    """One defender role as an in-process OpenAI-Agents-SDK agent on DeepSeek."""

    def __init__(self, name: str, cwd=None, model: str = "deepseek-chat", timeout: int = 200,
                 context: str = ""):
        # The Agents SDK client is process-global and configured for DeepSeek. Routing a GPT deployment
        # through it silently sends the model name to the wrong endpoint. Non-DeepSeek defender roles use
        # the project's model-aware client directly; AgentDojo supplies their environment slice inline.
        from code.internal_client import DEEPSEEK_MODELS, client_for_model
        self._direct_client = None if model in DEEPSEEK_MODELS else client_for_model(model)
        if self._direct_client is not None and cwd is not None:
            raise SubagentError(f"{name}: model-aware direct session cannot use filesystem tools")
        if self._direct_client is None:
            _ensure_configured()
        from pathlib import Path
        self.name = name
        self.model = model
        self.timeout = timeout
        self.context = context               # optional environment-plan context
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
        self._instructions = (f"You are the {name} role in a security-research pipeline. Reason carefully "
                              f"before answering. When asked for JSON, output ONLY the JSON.")
        self._agent = None
        if self._direct_client is None:
            from agents import Agent
            self._agent = Agent(
                name=name, instructions=self._instructions +
                ((" Use list_files / read_file to EXPLORE the working directory. Read only the files "
                  "you NEED, then STOP exploring and produce the answer.") if tools else ""),
                model=model, tools=tools)

    def ask(self, prompt: str) -> str:
        full = (self.context + "\n\n" + prompt) if self.context else prompt
        if self._direct_client is not None:
            from code.internal_client import chat
            return chat(self._direct_client, self.model, self._instructions + "\n\n" + full)
        from agents import Runner
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
