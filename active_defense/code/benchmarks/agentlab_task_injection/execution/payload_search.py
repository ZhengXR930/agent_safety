"""Generate AgentLAB Task-Injection payloads targeted to a chosen victim model.

This is intentionally separate from ``baselines.py``.  ``baselines.py`` only
replays a frozen payload namespace; this runner creates that namespace by
following AgentLAB's generate -> replay -> rewrite loop while using the
active-defense model clients for both the payload generator and the victim.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stdout
import io
import json
import os
from pathlib import Path
from typing import Any

from code.core.client import chat, client_for_model, read_config_key
from code.benchmarks.agentlab_task_injection.execution.baselines import (
    BENCHMARK_VERSION,
    DEFAULT_AGENTLAB_ROOT,
    SUITES,
    _pipeline_for,
    activate_agentlab,
    load_pair_manifest,
)


def _json_safe(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for key, value in obj.items():
            if isinstance(key, tuple):
                key = "|".join(map(str, key))
            out[str(key)] = _json_safe(value)
        return out
    if isinstance(obj, (list, tuple)):
        return [_json_safe(x) for x in obj]
    try:
        json.dumps(obj)
        return obj
    except TypeError:
        return str(obj)


def _natural_key(value: str) -> tuple[str, int]:
    head, _, tail = value.rpartition("_")
    try:
        return head, int(tail)
    except ValueError:
        return value, -1


def _round_robin_user(cases: list[tuple[str, str, str]]) -> list[tuple[str, str, str]]:
    by_user: dict[tuple[str, str], list[tuple[str, str, str]]] = {}
    for case in cases:
        suite, user_task, _injection = case
        by_user.setdefault((suite, user_task), []).append(case)
    for rows in by_user.values():
        rows.sort(key=lambda row: _natural_key(row[2]))
    ordered: list[tuple[str, str, str]] = []
    user_keys = sorted(by_user, key=lambda item: (item[0], _natural_key(item[1])))
    max_len = max((len(rows) for rows in by_user.values()), default=0)
    for idx in range(max_len):
        for key in user_keys:
            rows = by_user[key]
            if idx < len(rows):
                ordered.append(rows[idx])
    return ordered


def _select_pairs(args) -> list[tuple[str, str, str]]:
    cases = load_pair_manifest(tuple(args.suite))
    if args.pair:
        selected = set()
        for item in args.pair:
            suite, task, injection = item.split(":", 2)
            selected.add((suite, task, injection))
        cases = [case for case in cases if case in selected]
    if args.sample_strategy == "round_robin_user":
        cases = _round_robin_user(cases)
    if args.max_pairs:
        cases = cases[: args.max_pairs]
    return cases


def _ensure_agentlab_model_names(victim_model: str, attack_model: str, payload_namespace: str) -> None:
    import agentdojo.models as models

    models.MODEL_NAMES.setdefault(victim_model, "DeepSeek")
    models.MODEL_NAMES.setdefault(attack_model, "GPT-5.4")
    # The official prompt builder may receive the payload namespace as the
    # target-pipeline name. Keep it valid for get_model_name_from_pipeline().
    models.MODEL_NAMES.setdefault(payload_namespace, "DeepSeek")


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def _parse_snippets(raw: str, SnippetsResponse) -> list[dict[str, Any]]:
    raw = _strip_json_fence(raw)
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        start = raw.find("{")
        end = raw.rfind("}")
        if start < 0 or end <= start:
            raise
        parsed = json.loads(raw[start : end + 1])
    validated = SnippetsResponse.model_validate(parsed)
    return validated.model_dump()["snippets"]


def generate_snippets(client, model: str, prompt: str, SnippetsResponse, *, max_tokens: int) -> list[dict[str, Any]]:
    schema_hint = json.dumps(SnippetsResponse.model_json_schema(), ensure_ascii=False)
    full_prompt = (
        prompt
        + "\n\nReturn only a valid JSON object matching this schema. "
        + "Do not wrap it in markdown fences. Schema:\n"
        + schema_hint
    )
    raw = chat(
        client,
        model,
        full_prompt,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
    )
    return _parse_snippets(raw, SnippetsResponse)


def _make_pair_infos(cases, *, repo_root: Path, out_dir: Path, namespace: str, attack_method: str):
    from agentdojo.attacks.long_horizon_attack import _resolve_output_dir
    from agentdojo.attacks.search_attack_pipeline import PairInfo

    infos = []
    for suite_name, user_task_id, injection_task_id in cases:
        infos.append(
            (
                suite_name,
                PairInfo(
                    user_task_id=user_task_id,
                    injection_task_id=injection_task_id,
                    output_dir=_resolve_output_dir(
                        repo_root=repo_root,
                        out_dir=out_dir,
                        suite_name=suite_name,
                        benchmark_version=BENCHMARK_VERSION,
                        user_task_id=user_task_id,
                        injection_task_id=injection_task_id,
                        attack_method=attack_method,
                        agent_model_name=namespace,
                    ),
                ),
            )
        )
    return infos


def _build_initial_prompts_by_suite(pair_infos, *, repo_root: Path, out_dir: Path, attack_model: str, namespace: str, attack_method: str):
    from agentdojo.attacks.search_attack_pipeline import build_all_initial_prompts
    from agentdojo.task_suite.load_suites import get_suite

    result = []
    by_suite: dict[str, list] = {}
    for suite_name, pair_info in pair_infos:
        by_suite.setdefault(suite_name, []).append(pair_info)
    for suite_name, infos in by_suite.items():
        suite = get_suite(BENCHMARK_VERSION, suite_name)
        prompts = build_all_initial_prompts(
            infos,
            suite,
            attack_model,
            repo_root=repo_root,
            out_dir=out_dir,
            attack_method=attack_method,
            agent_model_name=namespace,
            benchmark_version=BENCHMARK_VERSION,
        )
        for pair_info, prompt in prompts:
            result.append((suite_name, pair_info, prompt))
    return result


def _make_attacker(suite, pipeline, attack_method: str, attack_model: str, namespace: str):
    from agentdojo.attacks.attack_registry import load_attack

    # Human_ReasoningAttack validates the pipeline name at construction time,
    # then reads payload files from target_pipeline.name at attack time.
    pipeline.name = attack_model
    attacker = load_attack(attack_method, suite, pipeline)
    pipeline.name = namespace
    return attacker


def evaluate_pair(args, suite_name: str, pair_info) -> dict[str, Any]:
    from agentdojo.benchmark import benchmark_suite_with_injections
    from agentdojo.logging import OutputLogger
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite(BENCHMARK_VERSION, suite_name)
    pipeline = _pipeline_for("undefended", args.victim_model, suite_name, args.embedding_model)
    attacker = _make_attacker(suite, pipeline, args.attack_method, args.attack_model, args.payload_namespace)
    with redirect_stdout(io.StringIO()):
        with OutputLogger(str(args.agent_logdir)):
            results = benchmark_suite_with_injections(
                agent_pipeline=pipeline,
                suite=suite,
                attack=attacker,
                logdir=args.agent_logdir,
                force_rerun=True,
                user_tasks=(pair_info.user_task_id,),
                injection_tasks=(pair_info.injection_task_id,),
                verbose=False,
                benchmark_version=BENCHMARK_VERSION,
            )
    log_path = (
        args.agent_logdir
        / args.payload_namespace.replace("/", "_")
        / suite_name
        / pair_info.user_task_id
        / args.attack_method
        / f"{pair_info.injection_task_id}.json"
    )
    messages = []
    if log_path.exists():
        messages = json.loads(log_path.read_text(encoding="utf-8")).get("messages", [])
    key = (pair_info.user_task_id, pair_info.injection_task_id)
    return {
        "suite": suite_name,
        "task": pair_info.user_task_id,
        "injection": pair_info.injection_task_id,
        "utility": bool(results["utility_results"].get(key, False)),
        "attack_success": bool(results["security_results"].get(key, False)),
        "messages": messages,
        "log_path": str(log_path),
        "error": None,
    }


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(rows)
    attack_successes = sum(bool(row.get("attack_success")) for row in rows)
    utility = sum(bool(row.get("utility")) for row in rows)
    failures = sum(bool(row.get("error")) for row in rows)
    return {
        "attack_total": total,
        "attack_successes": attack_successes,
        "ASR": attack_successes / total if total else 0.0,
        "attack_utility_passed": utility,
        "AU": utility / total if total else 0.0,
        "technical_failures": failures,
    }


def _write_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_json_safe(state), ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--agentlab-root", type=Path, default=DEFAULT_AGENTLAB_ROOT)
    parser.add_argument("--suite", choices=SUITES, action="append", default=[])
    parser.add_argument("--pair", action="append", default=[], help="suite:user_task_N:injection_task_M")
    parser.add_argument("--max-pairs", type=int, default=20)
    parser.add_argument("--sample-strategy", choices=("manifest", "round_robin_user"), default="round_robin_user")
    parser.add_argument("--payload-namespace", default="deepseek-v4-flash")
    parser.add_argument("--victim-model", default="deepseek-v4-flash")
    parser.add_argument("--attack-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--attack-method", default="long_horizon")
    parser.add_argument("--embedding-model", default="text-embedding-3-large")
    parser.add_argument("--out-dir", type=Path, default=Path("res"))
    parser.add_argument("--agent-logdir", type=Path, default=Path("runs/agentlab_payload_search"))
    parser.add_argument("--state-path", type=Path, default=Path("experiment_results/AgentLAB-TaskInjection/payload_search/deepseek-v4-flash_sanity20.json"))
    parser.add_argument("--max-rewrites", type=int, default=1)
    parser.add_argument("--generator-workers", type=int, default=2)
    parser.add_argument("--eval-workers", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=6000)
    args = parser.parse_args()

    if not args.suite:
        args.suite = ["banking"]

    # AgentLAB has a module-level OpenAI() in one attack helper. We do not use
    # that client here, but import still needs a non-empty key. Do not install
    # a dummy value when the repo config has the real ModelHub key, because
    # active_defense.client_for_model() prioritizes the environment.
    if not os.environ.get("OPENAI_API_KEY"):
        os.environ["OPENAI_API_KEY"] = read_config_key("OPENAI_API_KEY") or "dummy"

    agentlab_root = activate_agentlab(args.agentlab_root)
    import agentdojo.attacks.important_instructions_attacks  # noqa: F401
    from agentdojo.attacks.search_attack_pipeline import (
        SnippetsResponse,
        apply_rewrite_to_snippet,
        build_rewrite_prompts,
        save_snippet_and_prompt,
    )
    from agentdojo.task_suite.load_suites import get_suite

    _ensure_agentlab_model_names(args.victim_model, args.attack_model, args.payload_namespace)
    repo_root = agentlab_root

    cases = _select_pairs(args)
    pair_infos = _make_pair_infos(
        cases,
        repo_root=repo_root,
        out_dir=args.out_dir,
        namespace=args.payload_namespace,
        attack_method=args.attack_method,
    )
    state = {
        "schema": "agentlab-task-injection-payload-search-v1",
        "benchmark": "AgentLAB-TaskInjection",
        "benchmark_version": BENCHMARK_VERSION,
        "payload_namespace": args.payload_namespace,
        "payload_generator": args.attack_model,
        "victim_model": args.victim_model,
        "attack_method": args.attack_method,
        "suites": args.suite,
        "selected_pairs": cases,
        "rounds": [],
    }
    generator = client_for_model(args.attack_model)

    current_snippets: dict[str, list[dict[str, Any]]] = {}
    current_pair_infos = pair_infos
    initial_prompts = _build_initial_prompts_by_suite(
        current_pair_infos,
        repo_root=repo_root,
        out_dir=args.out_dir,
        attack_model=args.attack_model,
        namespace=args.payload_namespace,
        attack_method=args.attack_method,
    )
    print(json.dumps({"event": "initial_generation", "pairs": len(initial_prompts)}, ensure_ascii=False), flush=True)
    with ThreadPoolExecutor(max_workers=max(1, args.generator_workers)) as pool:
        futures = {
            pool.submit(generate_snippets, generator, args.attack_model, prompt, SnippetsResponse, max_tokens=args.max_tokens): (suite_name, pair_info, prompt)
            for suite_name, pair_info, prompt in initial_prompts
        }
        for future in as_completed(futures):
            suite_name, pair_info, prompt = futures[future]
            key = f"{suite_name}:{pair_info.user_task_id}:{pair_info.injection_task_id}"
            try:
                snippets = future.result()
                versioned, _ = save_snippet_and_prompt(snippets, prompt, pair_info.output_dir, is_rewrite=False)
                current_snippets[key] = snippets
                print(json.dumps({"event": "generated", "pair": key, "file": versioned.name}, ensure_ascii=False), flush=True)
            except Exception as exc:  # noqa: BLE001
                print(json.dumps({"event": "generation_error", "pair": key, "error": repr(exc)}, ensure_ascii=False), flush=True)

    for round_num in range(args.max_rewrites + 1):
        rows: list[dict[str, Any]] = []
        print(json.dumps({"event": "evaluate", "round": round_num, "pairs": len(current_pair_infos)}, ensure_ascii=False), flush=True)
        with ThreadPoolExecutor(max_workers=max(1, args.eval_workers)) as pool:
            futures = {
                pool.submit(evaluate_pair, args, suite_name, pair_info): (suite_name, pair_info)
                for suite_name, pair_info in current_pair_infos
                if f"{suite_name}:{pair_info.user_task_id}:{pair_info.injection_task_id}" in current_snippets
            }
            for future in as_completed(futures):
                suite_name, pair_info = futures[future]
                key = f"{suite_name}:{pair_info.user_task_id}:{pair_info.injection_task_id}"
                try:
                    row = future.result()
                except Exception as exc:  # noqa: BLE001
                    row = {
                        "suite": suite_name,
                        "task": pair_info.user_task_id,
                        "injection": pair_info.injection_task_id,
                        "utility": False,
                        "attack_success": False,
                        "messages": [],
                        "error": repr(exc),
                    }
                rows.append(row)
                print(json.dumps({"event": "evaluated", "round": round_num, "pair": key, "attack_success": row.get("attack_success"), "utility": row.get("utility"), "error": row.get("error")}, ensure_ascii=False), flush=True)

        round_state = {"round": round_num, "rows": rows, "summary": _summary(rows)}
        state["rounds"].append(round_state)
        state["latest_summary"] = round_state["summary"]
        _write_state(args.state_path, state)
        print(json.dumps({"event": "round_summary", "round": round_num, **round_state["summary"]}, ensure_ascii=False), flush=True)

        if round_num >= args.max_rewrites:
            break
        failed = []
        for row in rows:
            if row.get("attack_success") or row.get("error"):
                continue
            suite_name = row["suite"]
            key = f"{suite_name}:{row['task']}:{row['injection']}"
            pair_info = next(
                pi for s, pi in pair_infos
                if s == suite_name and pi.user_task_id == row["task"] and pi.injection_task_id == row["injection"]
            )
            failed.append((suite_name, pair_info, row.get("messages") or [], current_snippets[key]))
        if not failed:
            print(json.dumps({"event": "stop", "reason": "all_success"}, ensure_ascii=False), flush=True)
            break

        rewrite_inputs_by_suite: dict[str, list] = {}
        for suite_name, pair_info, messages, snippet in failed:
            rewrite_inputs_by_suite.setdefault(suite_name, []).append((pair_info, messages, snippet))
        rewrite_jobs = []
        for suite_name, items in rewrite_inputs_by_suite.items():
            suite = get_suite(BENCHMARK_VERSION, suite_name)
            rewrite_jobs.extend(
                (suite_name, pair_info, prompt, search_success)
                for pair_info, prompt, search_success in build_rewrite_prompts(
                    items,
                    suite,
                    repo_root=repo_root,
                    out_dir=args.out_dir,
                    attack_method=args.attack_method,
                    agent_model_name=args.payload_namespace,
                    benchmark_version=BENCHMARK_VERSION,
                )
            )
        print(json.dumps({"event": "rewrite_generation", "round": round_num + 1, "pairs": len(rewrite_jobs)}, ensure_ascii=False), flush=True)
        with ThreadPoolExecutor(max_workers=max(1, args.generator_workers)) as pool:
            futures = {
                pool.submit(generate_snippets, generator, args.attack_model, prompt, SnippetsResponse, max_tokens=args.max_tokens): (suite_name, pair_info, prompt, search_success)
                for suite_name, pair_info, prompt, search_success in rewrite_jobs
            }
            for future in as_completed(futures):
                suite_name, pair_info, prompt, search_success = futures[future]
                key = f"{suite_name}:{pair_info.user_task_id}:{pair_info.injection_task_id}"
                try:
                    rewritten = future.result()
                    new_snippet = apply_rewrite_to_snippet(current_snippets[key], rewritten, search_success)
                    versioned, _ = save_snippet_and_prompt(new_snippet, prompt, pair_info.output_dir, is_rewrite=True)
                    current_snippets[key] = new_snippet
                    print(json.dumps({"event": "rewritten", "pair": key, "file": versioned.name}, ensure_ascii=False), flush=True)
                except Exception as exc:  # noqa: BLE001
                    print(json.dumps({"event": "rewrite_error", "pair": key, "error": repr(exc)}, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
