"""Defender subagents — each is a Claude Code SESSION the orchestrator opens and drives.

Two kinds of agent in this framework, never to be confused:
  * the TARGET agent  — the (possibly attacked) agent we defend; run by backend.run_turn.
  * DEFENDER subagents — Surveyor / Camoufleur.  Each is a persistent SESSION (a session-id
    that can be resumed): the orchestrator OPENS the session, sends it turns, reads its output,
    and can follow up in the SAME session (shared context — it already explored the env).  The
    orchestrator owns the lifecycle and the overall orchestration; the binding supplies the
    env-specific prompts.

A Session runs in an environment directory (an isolated copy, so it cannot pollute anything),
so the subagent can ls / read files / inspect schemas itself.  No fallback: if a session
fails to produce usable output after a retry, the caller raises — we fix the subagent, we do
not paper over it with a template.
"""
from __future__ import annotations

import json
import re

from . import backend


class SubagentError(RuntimeError):
    pass


class Session:
    """One defender subagent as a resumable Claude Code session, rooted at `cwd`."""

    def __init__(self, name: str, cwd, model: str | None = None, timeout: int = 240):
        self.name = name
        self.cwd = cwd
        self.model = model or backend.DEFAULT_MODEL
        self.timeout = timeout
        self.sid = backend.new_session()
        self._opened = False

    def ask(self, prompt: str) -> str:
        """Send one turn (opens the session on first call, resumes thereafter)."""
        _, out, _ = backend.run_turn(prompt, self.cwd, self.model, session_id=self.sid,
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
