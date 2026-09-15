"""Run AgentLAB Task Injection baselines on frozen payload manifests.

This runner is deliberately separate from ``code.benchmarks.agentdojo``. The
suite implementation is AgentDojo-compatible, but the attack payloads and
frozen denominators are AgentLAB's long-horizon task-injection artifact.
"""
from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import os
from pathlib import Path
import sys
import threading
import time
import types
from typing import Any

from code.core.client import client_for_model, read_config_key


BENCHMARK_VERSION = "v1.2.1"
DEFAULT_AGENTLAB_ROOT = Path("/tmp/agentlab_probe_20260911/Task-Injection/agentdojo")
REPO = Path(__file__).resolve().parents[4]
BENCH = Path(__file__).resolve().parents[1]
SUITES = ("banking", "workspace", "travel", "slack")
METHODS = ("undefended", "camel", "melon")
_THREAD = threading.local()


def activate_agentlab(agentlab_root: str | Path | None = None) -> Path:
    root = Path(
        agentlab_root
        or os.environ.get("AGENTLAB_TASK_INJECTION_ROOT", "")
        or DEFAULT_AGENTLAB_ROOT
    ).expanduser().resolve()
    source = root if root.name == "src" else root / "src"
    if not source.is_dir():
        raise RuntimeError(
            f"AgentLAB Task-Injection source is missing: {source}. "
            "Pass --agentlab-root or set AGENTLAB_TASK_INJECTION_ROOT."
        )
    source_text = str(source)
    for name in list(sys.modules):
        if name == "agentdojo" or name.startswith("agentdojo."):
            del sys.modules[name]
    if source_text in sys.path:
        sys.path.remove(source_text)
    sys.path.insert(0, source_text)
    return root if root.name != "src" else root.parent


def load_clean_manifest(suites: tuple[str, ...]) -> list[tuple[str, str]]:
    raw = json.loads((BENCH / "data" / "clean_tasks.json").read_text(encoding="utf-8"))
    cases: list[tuple[str, str]] = []
    for suite in suites:
        for task in raw[suite]:
            cases.append((suite, task))
    return cases


def load_pair_manifest(suites: tuple[str, ...]) -> list[tuple[str, str, str]]:
    cases: list[tuple[str, str, str]] = []
    for suite in suites:
        rows = json.loads((BENCH / "data" / f"{suite}_pairs.json").read_text(encoding="utf-8"))
        for task, injection in rows:
            cases.append((suite, str(task), str(injection)))
    return cases


def payload_path(agentlab_root: str | Path, payload_model_label: str, suite: str, task: str, injection: str) -> Path:
    base = Path(agentlab_root).expanduser().resolve() / "res" / "long_horizon"
    if payload_model_label:
        base = base / payload_model_label
    return base / suite / BENCHMARK_VERSION / f"{task}_{injection}" / "newest_injection.json"


def audit_manifest(args, clean_cases, attack_cases) -> dict[str, Any]:
    protocol = json.loads((BENCH / "protocol.json").read_text(encoding="utf-8"))
    suites: dict[str, dict[str, int]] = {}
    for suite, _task in clean_cases:
        suites.setdefault(suite, {"clean": 0, "attack": 0})["clean"] += 1
    missing_payload: list[str] = []
    seen: set[tuple[str, str, str]] = set()
    for suite, task, injection in attack_cases:
        suites.setdefault(suite, {"clean": 0, "attack": 0})["attack"] += 1
        key = (suite, task, injection)
        if key in seen:
            missing_payload.append(f"DUPLICATE:{suite}:{task}:{injection}")
        seen.add(key)
        if not payload_path(args.agentlab_root, args.payload_model_label, suite, task, injection).is_file():
            missing_payload.append(f"{suite}:{task}:{injection}")
    expected = protocol["denominators"]
    report = {
        "benchmark": protocol["benchmark"],
        "method": args.method,
        "payload_model_label": args.payload_model_label,
        "clean": len(clean_cases),
        "attack": len(attack_cases),
        "attack_utility": len(attack_cases),
        "suites": suites,
        "expected": expected,
        "missing_payload": len(missing_payload),
        "missing_payload_examples": missing_payload[:10],
        "status": "PASS",
    }
    if len(clean_cases) != expected["clean"] or len(attack_cases) != expected["attack"] or missing_payload:
        report["status"] = "FAIL"
    return report


def _write(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + f".tmp.{os.getpid()}")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def _melon_content_text(value) -> str:
    if isinstance(value, str):
        return value
    from agentdojo.types import get_text_content_as_str

    return get_text_content_as_str(value or [])


def _melon_text_block(text: str):
    from agentdojo.types import text_content_block_from_string

    return text_content_block_from_string(text)


def _melon_block_messages(messages):
    from agentdojo.types import text_content_block_from_string

    converted = deepcopy(messages)
    for message in converted:
        if not isinstance(message, dict):
            continue
        content = message.get("content")
        if isinstance(content, str):
            message["content"] = [text_content_block_from_string(content)]
        elif isinstance(content, (list, tuple)):
            message["content"] = [
                text_content_block_from_string(item) if isinstance(item, str) else item
                for item in content
            ]
        if (
            message.get("role") == "assistant"
            and message.get("tool_calls")
            and "reasoning_content" not in message
        ):
            message["reasoning_content"] = ""
    return converted


def _adapt_official_melon_source(source: str) -> str:
    source = source.replace(
        '+ original_msg["content"] +',
        '+ _melon_content_text(original_msg["content"]) +',
    )
    source = source.replace(
        "self.llm.query(masked_query, masked_runtime, masked_env, masked_messages, masked_extra_args)",
        "self.llm.query(masked_query, masked_runtime, masked_env, "
        "_melon_block_messages(masked_messages), masked_extra_args)",
    )
    source = source.replace(
        '"content": "The tool outputs contain potential prompt injection, stopping execution.",',
        '"content": [_melon_text_block('
        '"The tool outputs contain potential prompt injection, stopping execution.")],',
    )
    return source


def _official_melon():
    path = REPO / "baseline/MELON/pi_detector.py"
    source = _adapt_official_melon_source(path.read_text(encoding="utf-8"))
    module = types.ModuleType("official_melon_pi_detector_agentlab")
    module.__file__ = str(path)
    module.__dict__.update(
        {
            "_melon_content_text": _melon_content_text,
            "_melon_block_messages": _melon_block_messages,
            "_melon_text_block": _melon_text_block,
        }
    )
    sys.modules[module.__name__] = module
    exec(compile(source, str(path), "exec"), module.__dict__)
    return module.MELON


def _pipeline_for(method: str, agent_model: str, suite_name: str, embedding_model: str):
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig, load_system_message
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM

    llm = OpenAILLM(client_for_model(agent_model), agent_model)
    llm.name = agent_model
    if method == "undefended":
        pipeline = AgentPipeline.from_config(
            PipelineConfig(
                llm=llm,
                model_id=None,
                defense=None,
                system_message_name=None,
                system_message=load_system_message(None),
            )
        )
    elif method == "camel":
        pipeline = AgentPipeline.from_config(
            PipelineConfig(
                llm=llm,
                model_id=None,
                defense="camel",
                suite_name=suite_name,
                system_message_name=None,
                system_message=load_system_message(None),
            )
        )
    elif method == "melon":
        from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
        from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop, ToolsExecutor

        detector = _official_melon()(llm, threshold=0.1)
        from openai import OpenAI

        zhizeng_key = read_config_key("OPENAI_API_ZHIZENGZENG")
        if zhizeng_key:
            detector.detection_model = OpenAI(
                base_url="https://api.zhizengzeng.com/v1",
                api_key=zhizeng_key,
            )
        else:
            embedding_key = read_config_key("OPENAI_API_KEY_OFFICIAL")
            if not embedding_key:
                raise RuntimeError("MELON requires OPENAI_API_ZHIZENGZENG or OPENAI_API_KEY_OFFICIAL")
            detector.detection_model = OpenAI(api_key=embedding_key)
        if embedding_model != "text-embedding-3-large":
            raise ValueError("official MELON requires text-embedding-3-large")
        pipeline = AgentPipeline(
            [SystemMessage(load_system_message(None)), InitQuery(), llm, ToolsExecutionLoop([ToolsExecutor(), detector])]
        )
    else:
        raise ValueError(f"unknown method: {method}")
    pipeline.name = agent_model
    return pipeline


def _thread_cache() -> dict:
    cache = getattr(_THREAD, "cache", None)
    if cache is None:
        cache = {}
        _THREAD.cache = cache
    return cache


def _context(args, suite_name: str, *, attack: bool):
    from agentdojo.attacks.attack_registry import load_attack
    from agentdojo.task_suite.load_suites import get_suite

    cache = _thread_cache()
    base_key = (args.method, suite_name, args.agent_model, args.embedding_model)
    if base_key not in cache:
        suite = get_suite(BENCHMARK_VERSION, suite_name)
        pipeline = _pipeline_for(args.method, args.agent_model, suite_name, args.embedding_model)
        cache[base_key] = {"suite": suite, "pipeline": pipeline}
    ctx = cache[base_key]
    if attack:
        attack_key = (*base_key, args.attack, args.attack_model_name, args.payload_model_label)
        if attack_key not in cache:
            pipeline = ctx["pipeline"]
            pipeline.name = args.attack_model_name
            attacker = load_attack(args.attack, ctx["suite"], pipeline)
            pipeline.name = args.payload_model_label
            cache[attack_key] = attacker
        ctx = {**ctx, "attacker": cache[attack_key]}
    return ctx


def _with_retries(args, fn):
    delay = 1.0
    last: Exception | None = None
    for _attempt in range(max(1, args.retries + 1)):
        try:
            return fn()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(delay)
            delay = min(delay * 2, 8.0)
    raise last  # type: ignore[misc]


def run_clean_case(args, suite_name: str, task_id: str) -> dict[str, Any]:
    def once():
        ctx = _context(args, suite_name, attack=False)
        suite = ctx["suite"]
        user_task = suite.get_user_task_by_id(task_id)
        utility, _security = suite.run_task_with_pipeline(
            ctx["pipeline"], user_task, injection_task=None, injections={}
        )
        return {
            "suite": suite_name,
            "task": task_id,
            "utility": bool(utility),
            "technical_failure": False,
        }

    try:
        return _with_retries(args, once)
    except Exception as exc:  # noqa: BLE001
        return {
            "suite": suite_name,
            "task": task_id,
            "utility": False,
            "technical_failure": True,
            "error": repr(exc),
        }


def run_attack_case(args, suite_name: str, task_id: str, injection_id: str) -> dict[str, Any]:
    def once():
        ctx = _context(args, suite_name, attack=True)
        suite = ctx["suite"]
        user_task = suite.get_user_task_by_id(task_id)
        injection_task = suite.get_injection_task_by_id(injection_id)
        with redirect_stdout(io.StringIO()):
            injections = ctx["attacker"].attack(user_task, injection_task)
        utility, security = suite.run_task_with_pipeline(
            ctx["pipeline"], user_task, injection_task=injection_task, injections=injections
        )
        return {
            "suite": suite_name,
            "task": task_id,
            "injection": injection_id,
            "utility": bool(utility),
            "attack_success": bool(security),
            "technical_failure": False,
        }

    try:
        return _with_retries(args, once)
    except Exception as exc:  # noqa: BLE001
        return {
            "suite": suite_name,
            "task": task_id,
            "injection": injection_id,
            "utility": False,
            "attack_success": False,
            "technical_failure": True,
            "error": repr(exc),
        }


def _summary(state: dict[str, Any]) -> dict[str, Any]:
    clean_rows = list(state["benign_by_task"].values())
    attack_rows = state["attacks"]
    clean_total = len(clean_rows)
    attack_total = len(attack_rows)
    clean_passed = sum(bool(row.get("utility")) for row in clean_rows)
    attack_utility_passed = sum(bool(row.get("utility")) for row in attack_rows)
    attack_successes = sum(bool(row.get("attack_success")) for row in attack_rows)
    clean_failures = sum(bool(row.get("technical_failure")) for row in clean_rows)
    attack_failures = sum(bool(row.get("technical_failure")) for row in attack_rows)
    return {
        "BU": clean_passed / clean_total if clean_total else 0.0,
        "AU": attack_utility_passed / attack_total if attack_total else 0.0,
        "ASR": attack_successes / attack_total if attack_total else 0.0,
        "benign_utility": clean_passed / clean_total if clean_total else 0.0,
        "utility_under_attack": attack_utility_passed / attack_total if attack_total else 0.0,
        "asr": attack_successes / attack_total if attack_total else 0.0,
        "benign_passed": clean_passed,
        "benign_total": clean_total,
        "attack_utility_passed": attack_utility_passed,
        "attack_successes": attack_successes,
        "attack_total": attack_total,
        "technical_failures": {"clean": clean_failures, "attack": attack_failures},
    }


def _coverage(state: dict[str, Any]) -> dict[str, Any]:
    suites: dict[str, dict[str, int]] = {}
    for key in state["benign_by_task"]:
        suite = key.split(":", 1)[0]
        suites.setdefault(suite, {"clean": 0, "attack": 0})["clean"] += 1
    for row in state["attacks"]:
        suites.setdefault(row["suite"], {"clean": 0, "attack": 0})["attack"] += 1
    return {
        "clean": len(state["benign_by_task"]),
        "attack": len(state["attacks"]),
        "attack_utility": len(state["attacks"]),
        "suites": suites,
    }


def _initial_state(args, clean_cases, attack_cases) -> dict[str, Any]:
    return {
        "schema": "agentlab-task-injection-baseline-v1",
        "benchmark": "AgentLAB-TaskInjection",
        "benchmark_version": BENCHMARK_VERSION,
        "method": args.method,
        "agent_model": args.agent_model,
        "attack": args.attack,
        "attack_model_name": args.attack_model_name,
        "payload_model_label": args.payload_model_label,
        "agentlab_root": str(Path(args.agentlab_root).expanduser().resolve()),
        "suites": list(args.suite),
        "expected_clean": len(clean_cases),
        "expected_pairs": len(attack_cases),
        "benign_by_task": {},
        "attacks": [],
    }


def _identity_keys() -> tuple[str, ...]:
    return (
        "schema",
        "benchmark",
        "benchmark_version",
        "method",
        "agent_model",
        "attack",
        "attack_model_name",
        "payload_model_label",
        "suites",
        "expected_clean",
        "expected_pairs",
    )


def _selected_cases(args):
    suites = tuple(args.suite)
    clean_cases = load_clean_manifest(suites)
    attack_cases = load_pair_manifest(suites)
    if args.pair:
        selected = set()
        for item in args.pair:
            suite, task, injection = item.split(":", 2)
            selected.add((suite, task, injection))
        attack_cases = [case for case in attack_cases if case in selected]
        clean_keys = {(suite, task) for suite, task, _inj in attack_cases}
        clean_cases = [case for case in clean_cases if case in clean_keys]
    if args.max_clean:
        clean_cases = clean_cases[: args.max_clean]
    if args.max_pairs:
        attack_cases = attack_cases[: args.max_pairs]
    return clean_cases, attack_cases


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--method", required=True, choices=METHODS)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--agent-model", default="deepseek-v4-flash")
    parser.add_argument("--agentlab-root", default=os.environ.get("AGENTLAB_TASK_INJECTION_ROOT", str(DEFAULT_AGENTLAB_ROOT)))
    parser.add_argument("--attack", default="long_horizon")
    parser.add_argument("--attack-model-name", default="gpt-5.1")
    parser.add_argument(
        "--payload-model-label",
        default="",
        help="AgentLAB payload namespace. Empty string uses res/long_horizon/<suite>/...",
    )
    parser.add_argument("--embedding-model", default="text-embedding-3-large")
    parser.add_argument("--suite", choices=SUITES, action="append", default=[])
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--split", choices=("all", "clean", "attack"), default="all")
    parser.add_argument("--max-clean", type=int, default=0)
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument("--pair", action="append", default=[], help="suite:user_task_N:injection_task_M")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--retries", type=int, default=2)
    parser.add_argument("--audit-only", action="store_true")
    parser.add_argument("--allow-failures", action="store_true")
    args = parser.parse_args()

    if not args.suite:
        args.suite = list(SUITES)
    clean_cases, attack_cases = _selected_cases(args)
    if args.audit_only:
        report = audit_manifest(args, clean_cases, attack_cases)
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        if report["status"] != "PASS":
            raise SystemExit(1)
        return

    activate_agentlab(args.agentlab_root)
    import agentdojo.attacks.important_instructions_attacks  # noqa: F401

    output = args.output_root / f"{args.method}.json"
    state = _initial_state(args, clean_cases, attack_cases)
    if args.resume and output.exists():
        saved = json.loads(output.read_text(encoding="utf-8"))
        if any(saved.get(key) != state.get(key) for key in _identity_keys()):
            raise ValueError(f"checkpoint does not match this run: {output}")
        state.update(saved)

    if args.split in {"all", "clean"}:
        completed_clean = set(state["benign_by_task"])
        pending_clean = [case for case in clean_cases if f"{case[0]}:{case[1]}" not in completed_clean]
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {pool.submit(run_clean_case, args, suite, task): (suite, task) for suite, task in pending_clean}
            for future in as_completed(futures):
                row = future.result()
                key = f"{row['suite']}:{row['task']}"
                state["benign_by_task"][key] = row
                state["summary"] = _summary(state)
                state["coverage"] = _coverage(state)
                _write(output, state)
                print(json.dumps({"method": args.method, "split": "clean", "completed": len(state["benign_by_task"]), "total": len(clean_cases)}), flush=True)

    if args.split in {"all", "attack"}:
        completed_attack = {(row["suite"], row["task"], row["injection"]) for row in state["attacks"]}
        pending_attack = [case for case in attack_cases if case not in completed_attack]
        with ThreadPoolExecutor(max_workers=max(1, args.workers)) as pool:
            futures = {
                pool.submit(run_attack_case, args, suite, task, injection): (suite, task, injection)
                for suite, task, injection in pending_attack
            }
            for future in as_completed(futures):
                row = future.result()
                state["attacks"].append(row)
                state["summary"] = _summary(state)
                state["coverage"] = _coverage(state)
                _write(output, state)
                print(json.dumps({"method": args.method, "split": "attack", "completed": len(state["attacks"]), "total": len(attack_cases)}), flush=True)

    state["summary"] = _summary(state)
    state["coverage"] = _coverage(state)
    _write(output, state)
    failures = state["summary"]["technical_failures"]
    print(json.dumps(state["summary"], ensure_ascii=False, indent=2), flush=True)
    if not args.allow_failures and (failures["clean"] or failures["attack"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
