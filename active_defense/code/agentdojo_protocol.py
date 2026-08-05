"""Single source of truth for the paper's AgentDojo evaluation protocol."""
from __future__ import annotations

import json
import hashlib
import sys
from pathlib import Path


BENCHMARK_VERSION = "v1.2.2"
AGENT_MODEL = "deepseek-v4-flash"


def activate_vendored_agentdojo() -> Path:
    """Force every runner to import the exact same vendored AgentDojo tree."""
    root = Path(__file__).resolve().parents[1]
    source = root / "baseline" / "AutoDojo" / "agentdojo" / "src"
    if not source.is_dir():
        raise RuntimeError(f"vendored AgentDojo source is missing: {source}")
    source_text = str(source)
    if source_text in sys.path:
        sys.path.remove(source_text)
    sys.path.insert(0, source_text)
    return source


def load_pair_manifest(path: str | Path) -> list[tuple[str, str]]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    pairs = raw.get("pairs") if isinstance(raw, dict) else raw
    if not isinstance(pairs, list):
        raise ValueError("pair manifest must be a JSON list or an object with a pairs list")
    normalized = []
    for item in pairs:
        if isinstance(item, str) and ":" in item:
            task, injection = item.split(":", 1)
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            task, injection = item
        else:
            raise ValueError(f"invalid pair manifest entry: {item!r}")
        normalized.append((str(task), str(injection)))
    if len(set(normalized)) != len(normalized):
        raise ValueError("pair manifest contains duplicate task/injection pairs")
    return normalized


def contracts_digest(contracts: dict) -> str:
    payload = json.dumps(contracts, sort_keys=True, ensure_ascii=False,
                         separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def load_frozen_contracts(path: str | Path) -> tuple[dict, dict]:
    """Load a frozen bundle and reject silent Contract edits."""
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if (isinstance(raw, dict) and isinstance(raw.get("contracts"), dict)
            and "contracts_sha256" in raw):
        contracts = raw.get("contracts")
        actual = contracts_digest(contracts)
        if raw.get("contracts_sha256") != actual:
            raise ValueError("frozen Contract bundle hash mismatch")
        return contracts, raw
    if (isinstance(raw, dict) and raw.get("schema") == "agentdojo-lean-full-v1"
            and isinstance(raw.get("contracts"), dict)):
        # A checkpoint is itself a frozen view of the exact Contracts used by
        # its completed episodes.  Reusing that view must not accidentally
        # treat config/results metadata as task ids.
        return raw["contracts"], raw
    if not isinstance(raw, dict):
        raise ValueError("Contract file must be a mapping or frozen bundle")
    return raw, {"schema": "legacy-contract-mapping", "contracts_sha256": contracts_digest(raw)}
