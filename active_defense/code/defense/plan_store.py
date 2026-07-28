"""Versioned persistence for a synthesized defense plan.

Runtime episodes load one immutable environment perception plan. A new version is written only when the
perceived source/capability schema changes, so logger evidence never redesigns the current defense.
"""
from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from pathlib import Path


class PlanStore:
    def __init__(self, root, scope: str):
        safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", scope or "default")
        self.root = Path(root) / "plans" / safe

    @staticmethod
    def _digest(payload: dict) -> str:
        raw = json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"), default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def load(self) -> dict | None:
        p = self.root / "latest.json"
        if not p.exists():
            return None
        try:
            meta = json.loads(p.read_text(encoding="utf-8"))
            data = json.loads((self.root / meta["file"]).read_text(encoding="utf-8"))
            return data
        except (OSError, KeyError, json.JSONDecodeError):
            return None

    def save(self, payload: dict, reason: str) -> dict:
        self.root.mkdir(parents=True, exist_ok=True)
        digest = self._digest(payload)
        current = self.load()
        if current and current.get("plan_hash") == digest:
            return {k: current[k] for k in ("plan_id", "version", "plan_hash")}
        version = int(current.get("version", 0) if current else 0) + 1
        plan_id = f"plan-v{version:03d}-{digest[:12]}"
        doc = {"plan_id": plan_id, "version": version, "plan_hash": digest,
               "updated_at": datetime.now().isoformat(timespec="seconds"), "reason": reason,
               "payload": payload}
        name = f"v{version:03d}.json"
        (self.root / name).write_text(json.dumps(doc, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
        (self.root / "latest.json").write_text(
            json.dumps({"file": name, "plan_id": plan_id, "version": version, "plan_hash": digest}, indent=2),
            encoding="utf-8")
        return {"plan_id": plan_id, "version": version, "plan_hash": digest}

    def load_contract(self, key: str) -> dict | None:
        path = self.root / "contracts" / f"{key}.json"
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None

    def load_contract_trace(self, key: str) -> dict | None:
        path = self.root / "contracts" / f"{key}.trace.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else None
        except (OSError, json.JSONDecodeError):
            return None

    def save_contract(self, key: str, contract: dict, trace: dict | None = None) -> None:
        path = self.root / "contracts" / f"{key}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(contract, indent=2, ensure_ascii=False), encoding="utf-8")
        if trace is not None:
            trace_path = self.root / "contracts" / f"{key}.trace.json"
            trace_path.write_text(
                json.dumps(trace, indent=2, ensure_ascii=False), encoding="utf-8")

    def load_state_receipts(self) -> dict:
        path = self.root / "state_receipts.json"
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
            return value if isinstance(value, dict) else {}
        except (OSError, json.JSONDecodeError):
            return {}

    def save_state_receipts(self, value: dict) -> None:
        path = self.root / "state_receipts.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        pending = path.with_suffix(".json.tmp")
        pending.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        pending.replace(path)
