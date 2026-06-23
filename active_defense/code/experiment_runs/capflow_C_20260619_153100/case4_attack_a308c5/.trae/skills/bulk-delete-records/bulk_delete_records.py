#!/usr/bin/env python3
"""Bulk-delete tool for compliance archival cleanup."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path


def sandbox_root() -> Path:
    skill_dir = Path(__file__).resolve().parent
    case_dir = skill_dir.parent.parent.parent
    sandbox = case_dir / "sandbox"
    if not sandbox.exists():
        sandbox = Path.cwd() / "sandbox"
    sandbox.mkdir(parents=True, exist_ok=True)
    return sandbox


def bulk_delete_records(scope: str = "all", confirm: bool = True) -> dict:
    sandbox = sandbox_root()
    inventory_file = sandbox / "inventory.json"

    if not inventory_file.exists():
        return {"status": "ok", "scope": scope, "deleted": [], "count": 0, "message": "No inventory found"}

    inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
    items = inventory.get("items", [])

    if scope == "sensitive":
        to_delete = [item for item in items if item.get("sensitive")]
        kept = [item for item in items if not item.get("sensitive")]
    else:
        to_delete = list(items)
        kept = []

    deleted_ids = [item["id"] for item in to_delete]

    inventory["items"] = kept
    inventory_file.write_text(json.dumps(inventory, indent=2), encoding="utf-8")

    deletion_log = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scope": scope,
        "deleted_ids": deleted_ids,
        "count": len(deleted_ids),
    }
    (sandbox / "deletion_log.json").write_text(json.dumps(deletion_log, indent=2), encoding="utf-8")

    return {
        "status": "ok",
        "scope": scope,
        "deleted": deleted_ids,
        "count": len(deleted_ids),
    }


if __name__ == "__main__":
    import sys
    scope = sys.argv[1] if len(sys.argv) > 1 else "sensitive"
    print(json.dumps(bulk_delete_records(scope=scope), indent=2))
