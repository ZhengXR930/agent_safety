"""Trusted MCPTox manifest location and loader."""

import json
from pathlib import Path
import re

from code.defense.memory import EnvironmentPlan

DEFAULT_PATH = Path(__file__).resolve().parent / "data" / "mcptox.json"


def load(path=DEFAULT_PATH) -> EnvironmentPlan:
    return EnvironmentPlan.from_dict(
        json.loads(Path(path).read_text(encoding="utf-8")))


def canonical(server: str, name: str) -> str:
    clean = lambda text: re.sub(
        r"[^A-Za-z0-9_-]+", "_", str(text)).strip("_")
    return clean(server) + "__" + clean(name)


def registration(server: str, tool: dict, *, effect=True,
                 observation=True) -> dict:
    """Register one complete mediated MCP boundary."""
    return {
        "name": canonical(server, tool["name"]),
        "description": tool["description"],
        "effect": bool(effect), "observation": bool(observation),
        "inputSchema": tool["inputSchema"],
        "outputSchema": {"type": "string"},
        "argument_types": dict(tool.get("argument_types") or {}),
        "output_types": dict(tool.get("output_types") or {}),
        "receipt_role": str(tool.get("receipt_role", "data")),
        "effect_return": bool(effect and observation),
    }
