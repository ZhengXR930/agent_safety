"""Run Task Shield on the frozen AgentDojo pair protocol.

Task Shield (Jia et al., 2025) was originally evaluated on AgentDojo: it
extracts the user's trusted task instructions, then scores every tool call for
"ContributesTo" that task and blocks the call when all contribution scores are
zero.  The published paper released no implementation; the paper-faithful
adapter lives in ``code/baselines/guards.py`` (``TaskShieldAdapter``) and is the
same object used on the Skill benchmarks.  This runner only wires that guard
into AgentDojo's tool-execution boundary so BU/AU/ASR share the same
denominator as Ours, CaMeL, DRIFT, MELON, Progent, Spotlighting, Tool Filter,
and AgentShield.

Task Shield is an enforcement defense, not a detector: a blocked tool call is
replaced with a refusal observation and the agent continues, so utility and
attack success are read straight from ``run_task_with_pipeline`` (as in
``native.py``/``melon.py``), not through a detect-as-defense discount.
"""
from __future__ import annotations

import argparse
import json
from ast import literal_eval
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from code.benchmarks.agentdojo_protocol_runtime import (AGENT_MODEL, BENCHMARK_VERSION,
                                     activate_vendored_agentdojo,
                                     load_pair_manifest)
from code.core.client import client_for_model
from code.baselines.guards import make_guard

activate_vendored_agentdojo()

ROOT = Path(__file__).resolve().parents[4]


def _is_string_list(value: str) -> bool:
    try:
        return isinstance(literal_eval(value), list)
    except (ValueError, SyntaxError):
        return False


def _build_executor(guard):
    """Task Shield's enforcement boundary as an AgentDojo pipeline element."""
    from agentdojo.agent_pipeline.base_pipeline_element import BasePipelineElement
    from agentdojo.agent_pipeline.llms.google_llm import EMPTY_FUNCTION_NAME
    from agentdojo.agent_pipeline.tool_execution import tool_result_to_str
    from agentdojo.functions_runtime import EmptyEnv, Env, FunctionsRuntime
    from agentdojo.types import (ChatMessage, ChatToolResultMessage,
                                 get_text_content_as_str, text_content_block_from_string)

    class TaskShieldToolsExecutor(BasePipelineElement):
        """Execute tool calls, but deny those Task Shield scores as misaligned.

        Mirrors AgentDojo's stock ``ToolsExecutor`` (same list-argument coercion
        and result formatting) so that allowed calls behave identically.  Before
        running a call it asks the guard's ContributesTo check; a denied call is
        never executed and returns the guard's refusal as its observation, and
        every executed call's output is passed through the guard's content review
        so misaligned instructions in tool outputs get Task Shield feedback.
        """

        def __init__(self, guard) -> None:
            self.guard = guard
            self.output_formatter = tool_result_to_str

        def query(
            self,
            query: str,
            runtime: FunctionsRuntime,
            env: Env = EmptyEnv(),
            messages: Sequence[ChatMessage] = [],
            extra_args: dict = {},
        ):
            if len(messages) == 0 or messages[-1]["role"] != "assistant":
                return query, runtime, env, messages, extra_args
            tool_calls = messages[-1]["tool_calls"]
            if not tool_calls:
                return query, runtime, env, messages, extra_args

            related = ""
            for message in reversed(messages[:-1]):
                if message["role"] == "tool":
                    related = get_text_content_as_str(message["content"]) or ""
                    break

            results = []
            for tool_call in tool_calls:
                if tool_call.function == EMPTY_FUNCTION_NAME:
                    results.append(ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string("")],
                        tool_call_id=tool_call.id, tool_call=tool_call,
                        error="Empty function name provided. Provide a valid function name."))
                    continue
                if tool_call.function not in (t.name for t in runtime.functions.values()):
                    results.append(ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string("")],
                        tool_call_id=tool_call.id, tool_call=tool_call,
                        error=f"Invalid tool {tool_call.function} provided."))
                    continue

                decision = self.guard.check(
                    tool_call.function, dict(tool_call.args), related_content=related)
                if not decision.allowed:
                    results.append(ChatToolResultMessage(
                        role="tool",
                        content=[text_content_block_from_string(
                            "Task Shield blocked this tool call: " + decision.reason)],
                        tool_call_id=tool_call.id, tool_call=tool_call,
                        error="Blocked by Task Shield"))
                    continue

                for arg_k, arg_v in tool_call.args.items():
                    if isinstance(arg_v, str) and _is_string_list(arg_v):
                        tool_call.args[arg_k] = literal_eval(arg_v)
                tool_result, error = runtime.run_function(env, tool_call.function, tool_call.args)
                text = self.output_formatter(tool_result)
                shielded, _ = self.guard.review_content(
                    text, source="tool", source_detail=str(tool_call.function))
                results.append(ChatToolResultMessage(
                    role="tool",
                    content=[text_content_block_from_string(shielded)],
                    tool_call_id=tool_call.id, tool_call=tool_call, error=error))
            return query, runtime, env, [*messages, *results], extra_args

    return TaskShieldToolsExecutor(guard)


def taskshield_pipeline(agent_model: str, guard):
    from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, load_system_message
    from agentdojo.agent_pipeline.basic_elements import InitQuery, SystemMessage
    from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM
    from agentdojo.agent_pipeline.tool_execution import ToolsExecutionLoop

    llm = OpenAILLM(client_for_model(agent_model), agent_model)
    llm.name = agent_model
    tools_loop = ToolsExecutionLoop([_build_executor(guard), llm])
    pipeline = AgentPipeline([
        SystemMessage(load_system_message(None)), InitQuery(), llm, tools_loop])
    pipeline.name = f"{agent_model}-taskshield"
    return pipeline


def _openai_tools(suite) -> list[dict]:
    from agentdojo.agent_pipeline.llms.openai_llm import _function_to_openai
    return [_function_to_openai(tool) for tool in suite.tools]


def _run_one(suite, pipeline, guard, tools, user_task,
             injection_task=None, injections=None) -> dict[str, Any]:
    try:
        guard.prepare(user_task.PROMPT, tools)
        utility, security = suite.run_task_with_pipeline(
            pipeline, user_task, injection_task=injection_task,
            injections=injections or {})
        return {"utility": bool(utility), "attack_success": bool(security), "error": None}
    except Exception as exc:  # noqa: BLE001 - checkpoint model/transport/guard failures
        return {"utility": False, "attack_success": False, "error": repr(exc)}


def _write(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + ".tmp")
    pending.write_text(json.dumps(value, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    pending.replace(path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", required=True)
    parser.add_argument("--pair-manifest", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--agent-model", default=AGENT_MODEL)
    parser.add_argument("--guard-model", default=None,
                        help="Task Shield alignment model (defaults to --agent-model)")
    parser.add_argument("--attack", default="important_instructions")
    parser.add_argument("--max-pairs", type=int, default=0)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()

    from agentdojo.attacks.attack_registry import load_attack
    from agentdojo.task_suite.load_suites import get_suite

    guard_model = args.guard_model or args.agent_model
    suite = get_suite(BENCHMARK_VERSION, args.suite)
    guard = make_guard("taskshield", ROOT, guard_model)
    pipeline = taskshield_pipeline(args.agent_model, guard)
    tools = _openai_tools(suite)
    attacker = load_attack(args.attack, suite, pipeline)
    pairs = load_pair_manifest(args.pair_manifest)
    selected = pairs[:args.max_pairs] if args.max_pairs else pairs
    output = Path(args.output)
    state = {
        "schema": "agentdojo-taskshield-v1", "suite": args.suite,
        "benchmark_version": BENCHMARK_VERSION, "defense": "taskshield",
        "agent_model": args.agent_model, "guard_model": guard_model,
        "attack": args.attack, "pair_manifest": args.pair_manifest,
        "expected_pairs": len(pairs), "selected_pairs": len(selected),
        "benign_by_task": {}, "attacks": [],
    }
    if args.resume and output.exists():
        saved = json.loads(output.read_text(encoding="utf-8"))
        identity = ("schema", "benchmark_version", "suite", "defense",
                    "agent_model", "guard_model", "attack", "pair_manifest",
                    "expected_pairs", "selected_pairs")
        if any(saved.get(key) != state.get(key) for key in identity):
            raise ValueError("checkpoint does not match this Task Shield run")
        state.update(saved)
    completed = {(row["task"], row["injection"]) for row in state["attacks"]}

    for task_id, injection_id in selected:
        user_task = suite.get_user_task_by_id(task_id)
        if task_id not in state["benign_by_task"]:
            state["benign_by_task"][task_id] = _run_one(
                suite, pipeline, guard, tools, user_task,
                injection_task=None, injections={})
            _write(output, state)
        if (task_id, injection_id) in completed:
            continue
        injection_task = suite.get_injection_task_by_id(injection_id)
        injections = attacker.attack(user_task, injection_task)
        row = _run_one(suite, pipeline, guard, tools, user_task,
                       injection_task=injection_task, injections=injections)
        row.update({"task": task_id, "injection": injection_id})
        state["attacks"].append(row)
        completed.add((task_id, injection_id))
        _write(output, state)
        print(json.dumps({"defense": "taskshield", "suite": args.suite,
                          "completed": len(state["attacks"]),
                          "selected": len(selected)}), flush=True)

    attacks = state["attacks"]
    benign = state["benign_by_task"]
    benign_count = len(benign)
    state["summary"] = {
        "benign_utility": sum(bool(r["utility"]) for r in benign.values()) / benign_count
        if benign_count else 0.0,
        "asr": sum(bool(r["attack_success"]) for r in attacks) / len(attacks)
        if attacks else 0.0,
        "utility_under_attack": sum(bool(r["utility"]) for r in attacks) / len(attacks)
        if attacks else 0.0,
        "benign_passed": sum(bool(r["utility"]) for r in benign.values()),
        "benign_total": benign_count,
        "attack_successes": sum(bool(r["attack_success"]) for r in attacks),
        "attack_utility_passed": sum(bool(r["utility"]) for r in attacks),
        "attack_total": len(attacks),
    }
    _write(output, state)
    print(json.dumps(state["summary"], ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
