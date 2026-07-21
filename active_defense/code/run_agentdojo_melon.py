"""Run the official MELON detector on a fixed AgentDojo pair manifest.

The detector implementation is imported unchanged from ``baseline/MELON``.
Only provider wiring and durable result checkpointing live here.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

from code.internal_client import client_for_model, read_config_key


ROOT = Path(__file__).resolve().parents[1]


def _official_melon():
    path = ROOT / "baseline/MELON/pi_detector.py"
    spec = importlib.util.spec_from_file_location("official_melon_pi_detector", path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module.MELON


def melon_pipeline(agent_model: str, embedding_model: str):
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, load_system_message
    from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
    from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop, ToolsExecutor

    llm = OpenAILLM(client_for_model(agent_model), agent_model)
    llm.name = agent_model
    detector = _official_melon()(llm, threshold=0.1)
    from openai import OpenAI
    embedding_key = read_config_key("OPENAI_API_KEY_OFFICIAL")
    if not embedding_key:
        raise RuntimeError("MELON requires OPENAI_API_KEY_OFFICIAL")
    detector.detection_model = OpenAI(api_key=embedding_key)
    # The official implementation fixes this model name at the call site. Keep
    # the argument explicit in metadata and reject accidental protocol drift.
    if embedding_model != "text-embedding-3-large":
        raise ValueError("official MELON requires text-embedding-3-large")
    tools_loop = ToolsExecutionLoop([ToolsExecutor(), detector])
    pipeline = AgentPipeline([
        SystemMessage(load_system_message(None)), InitQuery(), llm, tools_loop])
    pipeline.name = f"{agent_model}-melon"
    return pipeline


def _write(path: Path, value: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    pending.replace(path)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--agent-model", default="deepseek-chat")
    parser.add_argument("--embedding-model", default="text-embedding-3-large")
    parser.add_argument("--attack", default="direct")
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    from agentdojo.attacks.attack_registry import load_attack
    from agentdojo.task_suite.load_suites import get_suite

    suite = get_suite("v1", args.suite)
    pipeline = melon_pipeline(args.agent_model, args.embedding_model)
    attacker = load_attack(args.attack, suite, pipeline)
    pairs = [tuple(item) for item in json.loads(Path(args.pair_manifest).read_text())]
    selected = pairs[:args.max_pairs] if args.max_pairs else pairs
    output = Path(args.output)
    state = {"schema": "agentdojo-melon-v1", "suite": args.suite,
             "agent_model": args.agent_model, "embedding_model": args.embedding_model,
             "attack": args.attack, "expected_pairs": len(pairs),
             "benign_by_task": {}, "attacks": []}
    if args.resume and output.exists():
        saved = json.loads(output.read_text(encoding="utf-8"))
        if saved.get("schema") != state["schema"] or saved.get("suite") != args.suite:
            raise ValueError("checkpoint does not match this MELON run")
        state.update(saved)
    completed = {(item["task"], item["injection"]) for item in state["attacks"]}

    for task_id, injection_id in selected:
        user_task = suite.get_user_task_by_id(task_id)
        if task_id not in state["benign_by_task"]:
            utility, _ = suite.run_task_with_pipeline(
                pipeline, user_task, injection_task=None, injections={})
            state["benign_by_task"][task_id] = bool(utility)
            _write(output, state)
        if (task_id, injection_id) in completed:
            continue
        injection_task = suite.get_injection_task_by_id(injection_id)
        injections = attacker.attack(user_task, injection_task)
        utility, security = suite.run_task_with_pipeline(
            pipeline, user_task, injection_task=injection_task, injections=injections)
        state["attacks"].append({"task": task_id, "injection": injection_id,
                                 "utility": bool(utility),
                                 "attack_success": bool(security)})
        completed.add((task_id, injection_id))
        _write(output, state)
        print(json.dumps({"suite": args.suite, "completed": len(state["attacks"]),
                          "selected": len(selected), "output": str(output)}), flush=True)

    attacks = state["attacks"]
    state["summary"] = {
        "completed_pairs": len(attacks),
        "benign_tasks": len(state["benign_by_task"]),
        "benign_utility": sum(state["benign_by_task"].values()),
        "attack_utility": sum(item["utility"] for item in attacks),
        "asr": sum(item["attack_success"] for item in attacks),
    }
    _write(output, state)
    print(json.dumps(state["summary"], indent=2), flush=True)


if __name__ == "__main__":
    main()
