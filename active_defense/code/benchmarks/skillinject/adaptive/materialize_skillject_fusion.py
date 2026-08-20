"""Materialize SkillJect-fusion poisoned skills as a fixed dataset."""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from code.benchmarks.skillinject.execution.skillject_style import (
    DEFAULT_FUSION_PAIRS,
    OBJECTIVE_AWARE_PROMPT_SOURCE,
    OBJECTIVE_AWARE_PROMPT_VERSION,
    OFFICIAL_SKILLJECT_DIRECT_OBJECTIVE_GENERATOR,
    OFFICIAL_SKILLJECT_DIRECT_GENERATOR,
    OFFICIAL_SKILLJECT_DIRECT_PROMPT_SOURCE,
    OFFICIAL_SKILLJECT_OBJECTIVE_GENERATOR,
    OFFICIAL_SKILLJECT_GENERATOR,
    OFFICIAL_SKILLJECT_PROMPT_SOURCE,
    _build_base_sandbox,
    _inject_skillject_fusion,
    _load_pairs,
    _stem,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _load_materialization_pairs(args: argparse.Namespace):
    if args.selection == "five" or args.pair:
        return _load_pairs(args)

    rows = json.loads(Path(args.dataset).read_text(encoding="utf-8"))
    if args.injection_limit > 0:
        rows = rows[:args.injection_limit]
    pairs = []
    for row in rows:
        tasks = list(row.get("tasks") or ())
        if args.task_limit > 0:
            tasks = tasks[:args.task_limit]
        if args.selection == "scripted" and not row.get("task_scripts"):
            continue
        pairs.extend((row, index, task) for index, task in enumerate(tasks))
    return pairs


def _seed_cache(cache_root: Path, read_roots: list[str]) -> None:
    cache_root.mkdir(parents=True, exist_ok=True)
    for raw in read_roots:
        source = Path(raw)
        if not source.is_dir():
            continue
        for item in source.glob("*.json"):
            target = cache_root / item.name
            if not target.exists():
                shutil.copy2(item, target)


def _existing_entry(out: Path, pair: str, *, objective_aware: bool) -> dict | None:
    manifest_path = out / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if objective_aware and (
        manifest.get("objective_prompt_version") != OBJECTIVE_AWARE_PROMPT_VERSION
    ):
        return None
    for entry in manifest.get("pairs") or []:
        if entry.get("pair") != pair:
            continue
        skill_path = out / entry.get("skill_md_path", "")
        if skill_path.is_file():
            skill_md = skill_path.read_text(
                encoding="utf-8", errors="replace")
            if len(skill_md) >= 200 and skill_md.lstrip().startswith("---"):
                return entry
            return None
    return None


def _copy_resource(sandbox: Path, out: Path, pair: str,
                   injected: dict) -> str | None:
    script = injected.get("script")
    if not script:
        return None
    sources = [
        *sandbox.glob(f".codex/skills/*/resources/{script}"),
        sandbox / "resources" / str(script),
    ]
    source = next((item for item in sources if item.is_file()), None)
    if source is None:
        return None
    relative = Path("skills") / pair / "resources" / str(script)
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    return str(relative)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create a reusable SkillJect-fusion SkillInject dataset")
    parser.add_argument("--dataset", default=str(
        Path(__file__).resolve().parents[1] / "data" / "cases.json"))
    parser.add_argument("--output-root", default=str(
        Path(__file__).resolve().parents[1] / "data" /
        "skillject_fusion" / "gpt54_official_five"))
    parser.add_argument("--cache-root", default=str(
        Path(__file__).resolve().parents[4] / "experiment_results" /
        "SkillInject" / "SkillJect-fusion" / "official_five" / "fusion_cache"))
    parser.add_argument(
        "--read-cache-root", action="append", default=[],
        help="additional cache directory to seed into --cache-root before generation")
    parser.add_argument("--work-root", required=True)
    parser.add_argument("--pair", action="append", default=[],
                        help="exact idNNN_taskN pair; repeatable")
    parser.add_argument("--selection", choices=("five", "scripted", "all"),
                        default="five",
                        help="which SkillInject pairs to materialize")
    parser.add_argument("--attack-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--injection-mode", choices=("fusion",),
                        default="fusion")
    parser.add_argument(
        "--objective-aware", action="store_true",
        help=(
            "condition fusion on attacker-owned observable success outcomes "
            "without exposing benchmark judge text"))
    parser.add_argument("--injection-limit", type=int, default=0)
    parser.add_argument("--task-limit", type=int, default=0)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")

    pairs = _load_materialization_pairs(args)
    selected = args.pair or (
        list(DEFAULT_FUSION_PAIRS) if args.selection == "five"
        else [_stem(row, index) for row, index, _task in pairs])
    out = Path(args.output_root)
    work = Path(args.work_root)
    cache_root = Path(args.cache_root)
    out.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    _seed_cache(cache_root, args.read_cache_root)

    entries = []
    with tempfile.TemporaryDirectory(prefix="skillject_fusion_dataset_",
                                     dir=work) as raw:
        root = Path(raw)
        def materialize_one(row: dict, index: int, task: dict) -> dict:
            pair = _stem(row, index)
            existing = _existing_entry(
                out, pair, objective_aware=args.objective_aware)
            if existing:
                return {
                    "pair": pair,
                    "source": "dataset-skip",
                    "skill_md_path": existing.get("skill_md_path"),
                    "entry": existing,
                }
            sandbox = _build_base_sandbox(
                row, task, root / pair, include_scripts=True)
            injected = _inject_skillject_fusion(
                sandbox, row, index, task, cache_root, args.attack_model,
                objective_aware=args.objective_aware)
            skill_path = next(sandbox.glob(".codex/skills/*/SKILL.md"))
            skill_md = skill_path.read_text(encoding="utf-8", errors="replace")
            resource_path = _copy_resource(sandbox, out, pair, injected)
            relative = Path("skills") / pair / "SKILL.md"
            target = out / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            pending = target.with_suffix(".md.tmp")
            pending.write_text(skill_md, encoding="utf-8")
            pending.replace(target)
            entry = {
                "pair": pair,
                "row_id": row.get("id"),
                "task_index": index,
                "task": task.get("prompt"),
                "skill": task.get("skill"),
                "skill_name": injected.get("skill_name"),
                "script": injected.get("script"),
                "script_path": injected.get("script_path"),
                "attack_model": args.attack_model,
                "source_cache": injected.get("cache"),
                "source": injected.get("source"),
                "generator": injected.get("generator"),
                "prompt_source": injected.get("prompt_source"),
                "objective_aware": injected.get("objective_aware"),
                "observable_success_conditions": (
                    injected.get("observable_success_conditions")),
                "synthetic_payload": injected.get("synthetic_payload"),
                "resource_path": resource_path,
                "skill_md_path": str(relative),
                "skill_md_sha256": _sha256(skill_md),
            }
            return {**entry, "entry": entry}

        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            pending = {
                pool.submit(materialize_one, row, index, task): _stem(row, index)
                for row, index, task in pairs
            }
            for future in as_completed(pending):
                result = future.result()
                entries.append(result["entry"])
                printable = {key: value for key, value in result.items()
                             if key != "entry"}
                print(json.dumps(printable, ensure_ascii=False), flush=True)

    entries.sort(key=lambda item: item.get("pair", ""))
    manifest = {
        "schema": "skillinject-skillject-fusion-dataset-v1",
        "official_skillject_e2e": False,
        "official_skillject_prompt": True,
        "attack_family": "SkillJect fusion",
        "attack_family_detail": (
            "scripted rows use official prerequisite-script fusion; "
            "non-scripted rows use official instruction-layer semantic fusion"
        ),
        "objective_aware": args.objective_aware,
        "objective_aware_detail": (
            "GPT-5.4 receives attacker-owned observable success outcomes, "
            "not benchmark judge text"
            if args.objective_aware else None),
        "selection": args.selection,
        "attack_model": args.attack_model,
        "generators": sorted({
            str(entry.get("generator") or "")
            for entry in entries
            if entry.get("generator")
        }),
        "prompt_sources": sorted({
            str(entry.get("prompt_source") or "")
            for entry in entries
            if entry.get("prompt_source")
        }),
        "scripted_generator": (
            OFFICIAL_SKILLJECT_OBJECTIVE_GENERATOR
            if args.objective_aware else OFFICIAL_SKILLJECT_GENERATOR),
        "scripted_prompt_source": OFFICIAL_SKILLJECT_PROMPT_SOURCE,
        "direct_generator": (
            OFFICIAL_SKILLJECT_DIRECT_OBJECTIVE_GENERATOR
            if args.objective_aware else OFFICIAL_SKILLJECT_DIRECT_GENERATOR),
        "direct_prompt_source": OFFICIAL_SKILLJECT_DIRECT_PROMPT_SOURCE,
        "objective_prompt_source": (
            OBJECTIVE_AWARE_PROMPT_SOURCE if args.objective_aware else None),
        "objective_prompt_version": (
            OBJECTIVE_AWARE_PROMPT_VERSION if args.objective_aware else None),
        "source_dataset": str(Path(args.dataset)),
        "source_cache_root": str(cache_root),
        "pairs_requested": selected,
        "workers": args.workers,
        "pairs": entries,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(json.dumps({
        "manifest": str(manifest_path),
        "pairs": len(entries),
    }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
