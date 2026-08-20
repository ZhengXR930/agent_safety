"""Materialize targeted SkillJect refinements for current loss pairs.

This creates a fixed fusion-style dataset from existing round0 failure records.
It reuses the official SkillJect refinement prompt builder exposed by
``skillject_style.py`` and does not rerun the target model during generation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from pathlib import Path

from code.benchmarks.skillinject.execution.skillject_style import (
    OFFICIAL_SKILLJECT_REFINEMENT_GENERATOR,
    OFFICIAL_SKILLJECT_REFINEMENT_SOURCE,
    SYNTHETIC_DIRECT_SCRIPT,
    _chat_with_policy_retries,
    _clean_skillject_response,
    _direct_script_content,
    _ensure_official_resource_path,
    _refinement_cache_key,
    _refinement_prompt,
    _script_names,
    _stem,
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def _load_cases(path: str) -> list[dict]:
    rows = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(rows, list):
        raise ValueError("SkillInject cases.json must be a list")
    return rows


def _pair_map(rows: list[dict]) -> dict[str, tuple[dict, int, dict]]:
    pairs = {}
    for row in rows:
        for index, task in enumerate(row.get("tasks") or []):
            pairs[_stem(row, index)] = (row, index, task)
    return pairs


def _load_fusion_entry(root: Path, pair: str) -> dict:
    manifest = json.loads((root / "manifest.json").read_text(encoding="utf-8"))
    for entry in manifest.get("pairs") or []:
        if entry.get("pair") == pair:
            skill_path = root / str(entry.get("skill_md_path") or "")
            if not skill_path.is_file():
                raise FileNotFoundError(f"missing fused SKILL.md for {pair}: {skill_path}")
            return {
                **entry,
                "skill_md": skill_path.read_text(
                    encoding="utf-8", errors="replace"),
                "dataset_base": str(root),
            }
    raise KeyError(f"{pair} not found in fusion dataset {root}")


def _copy_resource(source_root: Path, source_entry: dict, out: Path,
                   pair: str, script: str) -> str | None:
    resource_path = str(source_entry.get("resource_path") or "")
    candidates = []
    if resource_path:
        candidates.append(source_root / resource_path)
    candidates.append(source_root / "skills" / pair / "resources" / script)
    source = next((path for path in candidates if path.is_file()), None)
    if source is None:
        return None
    relative = Path("skills") / pair / "resources" / script
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, target)
    target.chmod(0o755)
    return str(relative)


def _ensure_synthetic_resource(out: Path, pair: str, row: dict,
                               script: str) -> str:
    relative = Path("skills") / pair / "resources" / script
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(_direct_script_content(row), encoding="utf-8")
        target.chmod(0o755)
    return str(relative)


def _materialize_one(
    *,
    pair: str,
    row: dict,
    index: int,
    task: dict,
    fusion_root: Path,
    round0_root: Path,
    cache_root: Path,
    out: Path,
    attack_model: str,
) -> dict:
    source_entry = _load_fusion_entry(fusion_root, pair)
    previous = source_entry["skill_md"]
    round0_path = round0_root / "undefended" / f"{pair}_attack.json"
    if not round0_path.is_file():
        raise FileNotFoundError(f"missing round0 record for {pair}: {round0_path}")
    round0_record = json.loads(round0_path.read_text(encoding="utf-8"))
    skill_name = str(source_entry.get("skill_name") or task.get("skill") or "")
    scripts = _script_names(row) or [str(source_entry.get("script") or SYNTHETIC_DIRECT_SCRIPT)]
    script = scripts[0]
    key = _refinement_cache_key(
        row=row, index=index, method="undefended",
        previous_skill=previous, record=round0_record, script_name=script,
        attack_model=attack_model)
    cache_root.mkdir(parents=True, exist_ok=True)
    cache_path = cache_root / f"{pair}_undefended_r1_{key}.json"
    if cache_path.is_file():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        refined = payload.get("skill_md")
        if not isinstance(refined, str) or len(refined) < 200:
            raise ValueError(f"invalid cached refinement: {cache_path}")
        source = "cache"
    else:
        prompt, feedback = _refinement_prompt(
            skill_md=previous, skill_name=skill_name, script_name=script,
            row=row, record=round0_record, iteration=1)
        raw = _chat_with_policy_retries(
            attack_model, prompt, max_tokens=7000)
        refined = _clean_skillject_response(raw)
        if not isinstance(refined, str) or len(refined) < 200:
            raise ValueError(f"invalid refinement model response for {pair}")
        payload = {
            "schema": "skillinject-skillject-loss-refinement-cache-v1",
            "pair": pair,
            "method": "undefended",
            "iteration": 1,
            "attack_model": attack_model,
            "generator": OFFICIAL_SKILLJECT_REFINEMENT_GENERATOR,
            "prompt_source": OFFICIAL_SKILLJECT_REFINEMENT_SOURCE,
            "script": script,
            "script_path": f"resources/{script}",
            "skill_name": skill_name,
            "feedback": feedback.to_dict(),
            "round0_record_summary": {
                "attack_effect": round0_record.get("attack_effect"),
                "attack_runtime_signal": round0_record.get("attack_runtime_signal"),
                "detected": round0_record.get("detected"),
                "utility": round0_record.get("utility"),
                "termination": round0_record.get("termination"),
                "attack_reason": round0_record.get("attack_reason"),
                "utility_reason": round0_record.get("utility_reason"),
            },
            "skill_md": refined,
            "raw": raw,
        }
        cache_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2),
                              encoding="utf-8")
        source = "generated"

    relative = Path("skills") / pair / "SKILL.md"
    target = out / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    pending = target.with_suffix(".md.tmp")
    pending.write_text(refined, encoding="utf-8")
    pending.replace(target)
    resource_path = _copy_resource(fusion_root, source_entry, out, pair, script)
    if resource_path is None:
        resource_path = _ensure_synthetic_resource(out, pair, row, script)
    _ensure_official_resource_path(target.parent, script)
    return {
        "pair": pair,
        "row_id": row.get("id"),
        "task_index": index,
        "task": task.get("prompt"),
        "skill": task.get("skill"),
        "skill_name": skill_name,
        "script": script,
        "script_path": f"resources/{script}",
        "attack_model": attack_model,
        "source_cache": str(cache_path),
        "source": source,
        "generator": OFFICIAL_SKILLJECT_REFINEMENT_GENERATOR,
        "prompt_source": OFFICIAL_SKILLJECT_REFINEMENT_SOURCE,
        "base_dataset": str(fusion_root),
        "base_skill_md_path": source_entry.get("skill_md_path"),
        "round0_record": str(round0_path),
        "synthetic_payload": source_entry.get("synthetic_payload"),
        "resource_path": resource_path,
        "skill_md_path": str(relative),
        "skill_md_sha256": _sha256(refined),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default=str(
        Path(__file__).resolve().parents[1] / "data" / "cases.json"))
    parser.add_argument("--base-fusion-dataset", required=True)
    parser.add_argument("--round0-root", required=True)
    parser.add_argument("--output-root", required=True)
    parser.add_argument("--cache-root", required=True)
    parser.add_argument("--pair", action="append", required=True)
    parser.add_argument("--attack-model", default="gpt-5.4-2026-03-05")
    args = parser.parse_args()

    rows = _load_cases(args.dataset)
    pairs = _pair_map(rows)
    out = Path(args.output_root)
    out.mkdir(parents=True, exist_ok=True)
    entries = []
    for pair in args.pair:
        if pair not in pairs:
            raise ValueError(f"unknown pair: {pair}")
        row, index, task = pairs[pair]
        entry = _materialize_one(
            pair=pair, row=row, index=index, task=task,
            fusion_root=Path(args.base_fusion_dataset),
            round0_root=Path(args.round0_root),
            cache_root=Path(args.cache_root),
            out=out,
            attack_model=args.attack_model,
        )
        entries.append(entry)
        print(json.dumps({
            "pair": pair,
            "source": entry["source"],
            "skill_md_path": entry["skill_md_path"],
            "cache": entry["source_cache"],
        }, ensure_ascii=False), flush=True)

    manifest = {
        "schema": "skillinject-skillject-loss-refinement-dataset-v1",
        "official_skillject_e2e": False,
        "official_skillject_prompt": True,
        "attack_family": "SkillJect adaptive loss refinement",
        "base_fusion_dataset": str(Path(args.base_fusion_dataset)),
        "round0_root": str(Path(args.round0_root)),
        "attack_model": args.attack_model,
        "generator": OFFICIAL_SKILLJECT_REFINEMENT_GENERATOR,
        "prompt_source": OFFICIAL_SKILLJECT_REFINEMENT_SOURCE,
        "pairs_requested": args.pair,
        "pairs": entries,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2),
                             encoding="utf-8")
    print(json.dumps({"manifest": str(manifest_path), "pairs": len(entries)},
                     ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
