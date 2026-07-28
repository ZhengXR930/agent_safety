"""Single, fail-closed AgentDyn dataset protocol shared by every baseline."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
AGENTDYN_ROOT = REPO_ROOT / "baseline" / "AgentDyn"
AGENTDYN_SRC = AGENTDYN_ROOT / "src"
AGENTDYN_COMMIT = "5353cf7615b135cace8d07c8f12dac53a16b6db3"
BENCHMARK_VERSION = "v1"
SUITES = ("shopping", "github", "dailylife")
ATTACK = "important_instructions"
MODEL = "deepseek-v4-flash"
MODEL_DISPLAY_NAME = "DeepSeek"
EXPECTED_CLEAN_TASKS = 60
EXPECTED_ATTACK_CELLS = 560
MANIFEST_PATH = REPO_ROOT / "experiment_stage" / "agentdyn_shared_v1" / "manifest.json"


class AgentDynProtocolError(RuntimeError):
    pass


def _git_head(root: Path) -> str:
    return subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()


def _dataset_files(root: Path = AGENTDYN_ROOT) -> list[Path]:
    source = root / "src" / "agentdojo"
    paths = [
        source / "benchmark.py",
        source / "functions_runtime.py",
        source / "task_suite" / "task_suite.py",
        source / "task_suite" / "load_suites.py",
        source / "attacks" / "base_attacks.py",
        source / "attacks" / "important_instructions_attacks.py",
    ]
    suite_root = source / "default_suites" / BENCHMARK_VERSION
    for suite in SUITES:
        paths.extend(sorted((suite_root / suite).glob("*.py")))
    paths.extend(sorted((suite_root / "tools").glob("*.py")))
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise AgentDynProtocolError(f"AgentDyn dataset files missing: {missing}")
    return sorted(set(paths))


def dataset_fingerprint(root: Path = AGENTDYN_ROOT) -> str:
    digest = hashlib.sha256()
    for path in _dataset_files(root):
        relative = path.relative_to(root).as_posix().encode()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        content = path.read_bytes()
        digest.update(len(content).to_bytes(8, "big"))
        digest.update(content)
    return digest.hexdigest()


def activate_agentdyn(root: Path = AGENTDYN_ROOT) -> Path:
    """Activate only the canonical AgentDyn checkout; reject mixed AgentDojo imports."""
    if _git_head(root) != AGENTDYN_COMMIT:
        raise AgentDynProtocolError(
            f"AgentDyn commit mismatch: expected {AGENTDYN_COMMIT}, got {_git_head(root)}"
        )
    expected_src = (root / "src").resolve()
    loaded = sys.modules.get("agentdojo")
    if loaded is not None:
        loaded_path = Path(getattr(loaded, "__file__", "")).resolve()
        if expected_src not in loaded_path.parents:
            raise AgentDynProtocolError(f"foreign agentdojo already imported from {loaded_path}")
    src = str(expected_src)
    if src in sys.path:
        sys.path.remove(src)
    sys.path.insert(0, src)
    return expected_src


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def manifest_identity(manifest: dict[str, Any]) -> str:
    content = {key: value for key, value in manifest.items() if key != "manifest_sha256"}
    return hashlib.sha256(_canonical_json(content)).hexdigest()


def build_manifest() -> dict[str, Any]:
    activate_agentdyn()
    from agentdojo.attacks.attack_registry import load_attack
    from agentdojo.models import MODEL_NAMES
    from agentdojo.task_suite.load_suites import get_suite

    # AgentDyn predates this transport name. This only supplies the prose model
    # name used by the official fixed payload; it does not alter tasks or scoring.
    MODEL_NAMES[MODEL] = MODEL_DISPLAY_NAME
    target = SimpleNamespace(name=MODEL)
    suites: dict[str, Any] = {}
    cells: list[dict[str, Any]] = []
    for suite_name in SUITES:
        suite = get_suite(BENCHMARK_VERSION, suite_name)
        user_ids = list(suite.user_tasks)
        injection_ids = list(suite.injection_tasks)
        suites[suite_name] = {
            "user_task_ids": user_ids,
            "injection_task_ids": injection_ids,
        }
        attack = load_attack(ATTACK, suite, target)
        for user_id in user_ids:
            user_task = suite.get_user_task_by_id(user_id)
            for injection_id in injection_ids:
                injection_task = suite.get_injection_task_by_id(injection_id)
                injections = attack.attack(user_task, injection_task)
                cells.append(
                    {
                        "suite": suite_name,
                        "user_task_id": user_id,
                        "injection_task_id": injection_id,
                        "injections": injections,
                    }
                )
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "dataset": "AgentDyn",
        "agentdyn_commit": AGENTDYN_COMMIT,
        "dataset_fingerprint": dataset_fingerprint(),
        "benchmark_version": BENCHMARK_VERSION,
        "suites": suites,
        "attack": ATTACK,
        "agent_model": MODEL,
        "model_display_name": MODEL_DISPLAY_NAME,
        "clean_task_count": sum(len(v["user_task_ids"]) for v in suites.values()),
        "attack_cell_count": len(cells),
        "cells": cells,
    }
    manifest["manifest_sha256"] = manifest_identity(manifest)
    validate_manifest(manifest)
    return manifest


def validate_manifest(manifest: dict[str, Any]) -> None:
    expected = {
        "dataset": "AgentDyn",
        "agentdyn_commit": AGENTDYN_COMMIT,
        "benchmark_version": BENCHMARK_VERSION,
        "attack": ATTACK,
        "agent_model": MODEL,
        "clean_task_count": EXPECTED_CLEAN_TASKS,
        "attack_cell_count": EXPECTED_ATTACK_CELLS,
    }
    for key, value in expected.items():
        if manifest.get(key) != value:
            raise AgentDynProtocolError(f"manifest {key} mismatch: {manifest.get(key)!r} != {value!r}")
    if tuple(manifest.get("suites", {})) != SUITES:
        raise AgentDynProtocolError("manifest suite order/content mismatch")
    cells = manifest.get("cells", [])
    identities = {
        (cell["suite"], cell["user_task_id"], cell["injection_task_id"])
        for cell in cells
    }
    if len(identities) != EXPECTED_ATTACK_CELLS or len(cells) != EXPECTED_ATTACK_CELLS:
        raise AgentDynProtocolError("manifest contains missing or duplicate attack cells")
    if any(not cell.get("injections") for cell in cells):
        raise AgentDynProtocolError("manifest contains a non-injectable/empty cell")
    if manifest.get("manifest_sha256") != manifest_identity(manifest):
        raise AgentDynProtocolError("manifest content hash mismatch")


def load_manifest(path: Path = MANIFEST_PATH, *, verify_source: bool = True) -> dict[str, Any]:
    manifest = json.loads(path.read_text(encoding="utf-8"))
    validate_manifest(manifest)
    if verify_source:
        activate_agentdyn()
        actual = dataset_fingerprint()
        if manifest["dataset_fingerprint"] != actual:
            raise AgentDynProtocolError(
                f"AgentDyn source fingerprint mismatch: {actual} != {manifest['dataset_fingerprint']}"
            )
    return manifest


def write_manifest(path: Path = MANIFEST_PATH) -> dict[str, Any]:
    manifest = build_manifest()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


if __name__ == "__main__":
    frozen = write_manifest()
    print(json.dumps({key: frozen[key] for key in (
        "agentdyn_commit", "dataset_fingerprint", "manifest_sha256",
        "clean_task_count", "attack_cell_count",
    )}, indent=2))
