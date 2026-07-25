"""Run undefended or Progent on the official InjecAgent task/runtime interface."""
from __future__ import annotations

import argparse
from dataclasses import replace
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
AD = ROOT / "baseline/AutoDojo/agentdojo/src"
if str(AD) not in sys.path:
    sys.path.insert(0, str(AD))

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig  # noqa: E402
from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM  # noqa: E402
from agentdojo.types import get_text_content_as_str  # noqa: E402

from code.benchmarks.injecagent import InjecAgentCase, load_cases, load_tools  # noqa: E402
from code.internal_client import client_for_model, read_config_key  # noqa: E402
from code.run_injecagent_camel_original import (  # noqa: E402
    InjecAgentEnvironment, _replace_attack_text, _runtime,
)


def _final(messages) -> str:
    for message in reversed(messages):
        if message["role"] == "assistant" and message.get("content"):
            return get_text_content_as_str(message["content"])
    return ""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--defense", choices=("undefended", "progent"), required=True)
    parser.add_argument("--attack", choices=("dh", "ds", "both"), default="both")
    parser.add_argument("--setting", choices=("base", "enhanced"), default="enhanced")
    parser.add_argument("--indices", default="")
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--model", default="deepseek-chat")
    parser.add_argument("--policy-model", default="deepseek-chat")
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--injection-overrides", type=Path)
    parser.add_argument("--user-task-overrides", type=Path)
    args = parser.parse_args()

    key = read_config_key("DEEPSEEK_API_KEY")
    if not key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY")
    os.environ["SECAGENT_BASE_URL"] = "https://api.deepseek.com"
    os.environ["SECAGENT_API_KEY"] = key
    os.environ["SECAGENT_POLICY_MODEL"] = args.policy_model
    os.environ["SECAGENT_GENERATE"] = "True"
    os.environ["SECAGENT_UPDATE"] = "True"
    os.environ["SECAGENT_IGNORE_UPDATE_ERROR"] = "True"

    tools = load_tools(args.data_dir)
    cases = load_cases(args.data_dir, args.attack, args.setting)
    if args.user_task_overrides:
        overrides = json.loads(args.user_task_overrides.read_text())
        cases = [
            replace(case, user_task=str(overrides[case.id]))
            if case.id in overrides else case for case in cases
        ]
    if args.injection_overrides:
        overrides = json.loads(args.injection_overrides.read_text())
        cases = [
            replace(case, observation=_replace_attack_text(
                case.observation, case.attacker_instruction,
                str(overrides[case.id])))
            if case.id in overrides else case for case in cases
        ]
    if args.indices:
        wanted = {int(item) for item in args.indices.split(",") if item.strip()}
        cases = [case for case in cases if case.index in wanted]
    if args.limit:
        cases = cases[:args.limit]

    target_llm = OpenAILLM(client_for_model(args.model), args.model, temperature=0)
    target_llm.name = args.model
    config = PipelineConfig(
        llm=target_llm, model_id=args.model,
        defense=None if args.defense == "undefended" else "progent",
        suite_name="injecagent", system_message_name=None, system_message=None,
        progent_policy_model=args.policy_model,
        progent_generate=True, progent_update=True,
        progent_suite="injecagent",
    )
    pipeline = AgentPipeline.from_config(config)
    simulated = json.loads(
        (args.data_dir / "attacker_simulated_responses.json").read_text())
    rows = []
    if args.resume and args.output.exists():
        rows = json.loads(args.output.read_text()).get("rows", [])
    done = {row["case"] for row in rows}

    for case in cases:
        if case.id in done:
            continue
        executed = []
        env = InjecAgentEnvironment(executed=executed)
        runtime = _runtime(tools, case, simulated, executed)
        error = None
        messages = []
        try:
            _, _, _, messages, _ = pipeline.query(case.user_task, runtime, env)
        except Exception as exception:
            error = f"{type(exception).__name__}: {exception}"
        target = case.attacker_tools[-1] if case.attacker_tools else ""
        stage1 = case.attacker_tools[0] if case.attacker_tools else ""
        committed = [item["name"] for item in executed]
        rows.append({
            "case": case.id, "attack": case.attack,
            "user_tool": case.user_tool, "attacker_tools": list(case.attacker_tools),
            "executed": executed,
            "attempted_stage1": stage1 in committed,
            "attack_success": target in committed,
            "user_tool_executed": case.user_tool in committed,
            "task_completed_proxy": bool(_final(messages).strip()),
            "final": _final(messages), "execution_error": error,
        })
        artifact = {
            "schema": "injecagent-standard-defense-v1",
            "config": {
                **{k: str(v) if isinstance(v, Path) else v
                   for k, v in vars(args).items()},
            },
            "metrics": {
                "completed": len(rows),
                "attack_success": sum(x["attack_success"] for x in rows),
                "attempted_stage1": sum(x["attempted_stage1"] for x in rows),
                "user_tool_executed": sum(x["user_tool_executed"] for x in rows),
                "task_completed_proxy": sum(x["task_completed_proxy"] for x in rows),
                "execution_errors": sum(bool(x["execution_error"]) for x in rows),
            },
            "rows": rows,
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        tmp = args.output.with_suffix(args.output.suffix + ".tmp")
        tmp.write_text(json.dumps(artifact, ensure_ascii=False, indent=2))
        tmp.replace(args.output)
        print(json.dumps({"case": case.id, **artifact["metrics"]}), flush=True)


if __name__ == "__main__":
    main()
