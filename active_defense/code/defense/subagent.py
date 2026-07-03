"""Defender subagents — each is a Claude Code SESSION the Engine opens and drives.

Two kinds of agent in this framework, never to be confused:
  * the TARGET agent  — the (possibly attacked) agent we defend; run by agent_runtime.run_turn.
  * DEFENDER subagents — the Surveyor (env exploration).  A persistent SESSION (a resumable
    session-id): the Engine OPENS it, sends it turns, reads its output, and can follow up in the
    SAME session (shared context — it already explored the env).

A Session runs in an environment directory (an isolated copy, so it cannot pollute anything), so
the subagent can ls / read files / inspect schemas itself.  No fallback: if a session fails to
produce usable output after a retry, the caller raises — we fix the subagent, not paper over it.
"""
from __future__ import annotations

import json
import re

from . import agent_runtime


class SubagentError(RuntimeError):
    pass


class Session:
    """One defender subagent as a resumable Claude Code session, rooted at `cwd`."""

    def __init__(self, name: str, cwd, model: str | None = None, timeout: int = 240):
        self.name = name
        self.cwd = cwd
        self.model = model or agent_runtime.DEFAULT_MODEL
        self.timeout = timeout
        self.sid = agent_runtime.new_session()
        self._opened = False

    def ask(self, prompt: str) -> str:
        """Send one turn (opens the session on first call, resumes thereafter)."""
        _, out, _ = agent_runtime.run_turn(prompt, self.cwd, self.model, session_id=self.sid,
                                           resume=self._opened, timeout=self.timeout)
        self._opened = True
        return out

    def ask_json(self, prompt: str, *, retries: int = 1):
        """Send a turn and parse JSON; on malformed output, re-ask in the SAME session once.

        Raises SubagentError if no valid JSON after retries (no silent fallback)."""
        out = self.ask(prompt)
        for _ in range(retries + 1):
            parsed = _extract_json(out)
            if parsed is not None:
                return parsed
            out = self.ask("Your previous reply was not valid JSON. Reply with ONLY the JSON, "
                           "no prose, no code fences.")
        raise SubagentError(f"{self.name}: no valid JSON after {retries + 1} attempts")


class ApiSession:
    """Memory-backed, API-only stand-in for a defender Session: carries an EnvMemory slice as context
    and answers via one fast API call (no `claude` subprocess cold-start).  Used by the memory-backed
    roles (Camoufleur / Distinguisher) that need env KNOWLEDGE — designing a decoy / judging authenticity
    — not filesystem EXPLORATION.  Duck-compatible with helper design functions' `session` param
    (.ask / .ask_json)."""

    def __init__(self, client, model: str, context: str = ""):
        self.client, self.model, self.context = client, model, context

    def ask(self, prompt: str) -> str:
        from internal_client import chat
        return chat(self.client, self.model, (self.context + "\n\n" + prompt) if self.context else prompt)

    def ask_json(self, prompt: str) -> dict:
        txt = self.ask(prompt)
        m = re.search(r"```(?:json)?\s*(.*?)```", txt, re.S)
        if m:
            txt = m.group(1)
        try:
            return json.loads(txt)
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", txt, re.S)
            if m:
                return json.loads(m.group(0))
            raise SubagentError("ApiSession: no JSON in response")


def _extract_json(text: str):
    m = re.search(r"```(?:json)?\s*(.*?)```", text, re.S)
    chunk = m.group(1).strip() if m else None
    if chunk is None:
        m = re.search(r"(\[.*\]|\{.*\})", text, re.S)
        chunk = m.group(1) if m else None
    if not chunk:
        return None
    try:
        return json.loads(chunk)
    except json.JSONDecodeError:
        return None
