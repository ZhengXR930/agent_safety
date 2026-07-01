"""Agent-CLI backend: native Claude Code driving a DeepSeek base model.

SCR's high attack-success is bound to the native Claude Code agent framework; the
signal comes from the DeepSeek base model.  We get both by pointing Claude Code at
DeepSeek's Anthropic-compatible endpoint via env vars injected ONLY into the spawned
subprocess (never into ~/.claude/settings, which would hijack this session).

Each episode runs in an ISOLATED system-temp dir (no sibling case/split dirs visible,
no experiment-revealing cwd path) so the agent cannot meta-game the harness.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from internal_client import read_config_key  # noqa: E402

DEEPSEEK_ANTHROPIC_BASE = "https://api.deepseek.com/anthropic"
SKILLS_DIRNAME = ".claude"
DEFAULT_MODEL = "deepseek-chat"


def skills_root(work: Path) -> Path:
    return work / SKILLS_DIRNAME / "skills"


def _env(model: str) -> dict:
    key = read_config_key("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY (env or config.txt).")
    env = dict(os.environ)
    env.update({
        "ANTHROPIC_BASE_URL": DEEPSEEK_ANTHROPIC_BASE,
        "ANTHROPIC_AUTH_TOKEN": key,
        "ANTHROPIC_API_KEY": key,
        "ANTHROPIC_MODEL": model,
        "ANTHROPIC_DEFAULT_OPUS_MODEL": model,
        "ANTHROPIC_DEFAULT_SONNET_MODEL": model,
        "ANTHROPIC_DEFAULT_HAIKU_MODEL": model,
        "CLAUDE_CODE_SUBAGENT_MODEL": model,
        "CLAUDE_CODE_MAX_OUTPUT_TOKENS": "32000",
        "CLAUDE_CODE_USE_BEDROCK": "",
    })
    return env


def _cmd(model: str, session_id: str | None, resume: bool, mcp_config: str | None = None) -> list[str]:
    cmd = ["claude", "--print", "--dangerously-skip-permissions",
           "--output-format", "text", "--model", model]
    if mcp_config:                                   # attach a local MCP server (e.g. the WRAP mediator)
        cmd += ["--mcp-config", mcp_config, "--strict-mcp-config"]
    if resume and session_id:
        cmd += ["--resume", session_id]
    elif session_id:
        cmd += ["--session-id", session_id]
    return cmd


def run_turn(prompt: str, cwd: Path, model: str, *, session_id: str | None = None,
             resume: bool = False, timeout: int = 240, mcp_config: str | None = None) -> tuple[int, str, float]:
    """Run one agent turn; returns (returncode, combined_output, seconds)."""
    t0 = time.time()
    try:
        r = subprocess.run(
            _cmd(model, session_id, resume, mcp_config) + [prompt], cwd=str(cwd),
            capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=timeout, env=_env(model))
        return r.returncode, (r.stdout or "") + "\n" + (r.stderr or ""), time.time() - t0
    except subprocess.TimeoutExpired:
        return -1, "TIMEOUT", time.time() - t0
    except Exception as e:  # noqa: BLE001
        return -1, str(e), time.time() - t0


@contextmanager
def isolated_env(case_dir: Path):
    """Copy a case into an isolated temp dir, rename cli_skills -> .claude, yield the
    work root.  Auto-cleaned.  The opaque temp path hides the experiment from the agent."""
    iso = Path(tempfile.mkdtemp(prefix="env_"))
    work = iso / "env"
    try:
        shutil.copytree(case_dir, work)
        src = work / "cli_skills"
        if src.exists():
            src.rename(work / SKILLS_DIRNAME)
        (work / "sandbox").mkdir(exist_ok=True)
        yield work
    finally:
        shutil.rmtree(iso, ignore_errors=True)


def new_session() -> str:
    return str(uuid.uuid4())
