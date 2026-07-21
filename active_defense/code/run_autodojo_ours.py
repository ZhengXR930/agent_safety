"""Run AutoDojo's optimizer against the complete instruction-local defense.

AutoDojo's native defense hook is a post-tool-output pipeline element.  Our
runtime mediates calls before execution, so this bridge replaces only
AutoDojo's ASR evaluator while leaving its seed population, analyzer, rewriter,
leaderboard, and cache format unchanged.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from code.benchmarks.agentdojo import AgentDojoRunner, tool_schemas
from code.defense.engine import Engine
from code.defense.plan_store import PlanStore
from code.defense.plant import PlantDesigner
from code.internal_client import (
    DEEPSEEK_BASE_URL,
    _with_api_logging,
    client_for_model,
    read_config_key,
)
from code.run_agentdojo import pipeline_for


ROOT = Path(__file__).resolve().parents[1]
AUTODOJO = ROOT / "baseline" / "AutoDojo" / "agentdojo"
for path in (AUTODOJO / "variant_generation", AUTODOJO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import llm_utils  # noqa: E402
import optimize_variants as autodojo  # noqa: E402


class OursASREvaluator:
    """Adapter satisfying AutoDojo's evaluator protocol with our real runner."""

    def __init__(self, suite_name, model="deepseek-chat", model_id=None, defense=None,
                 **_kwargs):
        from agentdojo.task_suite.load_suites import get_suite

        self.suite = get_suite("v1.2.2", suite_name)
        self.pipeline = pipeline_for(model_id or model)
        self.engine = Engine(client_for_model(os.environ["OURS_CONTRACT_MODEL"]),
                             os.environ["OURS_CONTRACT_MODEL"])
        scope = f"autodojo_{suite_name}_declared"
        self.engine.perceive(tool_schemas(self.suite, "declared"),
                             store=PlanStore(os.environ["OURS_PLAN_STORE"], scope))
        self.runner = AgentDojoRunner(self.suite, self.pipeline, self.engine)
        self.contracts = {}

    def _contract(self, user_task):
        if user_task.ID not in self.contracts:
            self.contracts[user_task.ID] = self.engine.contract(user_task.PROMPT)
        return self.contracts[user_task.ID]

    def _plant(self, contract):
        model = os.environ["OURS_PLANT_MODEL"]
        review_model = os.environ["OURS_PLANT_REVIEW_MODEL"]
        return PlantDesigner(
            client_for_model(model), model, contract,
            reviewer_client=client_for_model(review_model), reviewer_model=review_model,
        )

    def _build_injections(self, injection_task, candidate_injections):
        return {
            vector: autodojo.yaml_escape(
                candidate_injections.get(vector, injection_task.GOAL))
            for vector in self.suite.get_injection_vector_defaults()
        }

    def _run(self, injection_task_id, candidate_injections, user_task_id):
        injection_task = self.suite.get_injection_task_by_id(injection_task_id)
        user_task = self.suite.get_user_task_by_id(user_task_id)
        contract = self._contract(user_task)
        result = self.runner.run(
            user_task,
            injection_task=injection_task,
            injections=self._build_injections(injection_task, candidate_injections),
            contract=contract,
            plant_factory=self._plant(contract),
        )
        result.pop("environment", None)
        return result

    @staticmethod
    def _detail(user_task_id, injection_task_id, result):
        return {
            "user_task": user_task_id,
            "injection_task": injection_task_id,
            "utility": bool(result["utility"]),
            "security": bool(result["asr"]),
            "routes": [item.get("route") for item in result.get("decisions", [])],
        }

    def _eval_single(self, injection_task_id, candidate_injections, user_task_id):
        return self._detail(user_task_id, injection_task_id,
                            self._run(injection_task_id, candidate_injections, user_task_id))

    def evaluate(self, injection_task_id, candidate_injections, user_task_ids):
        details = [self._eval_single(injection_task_id, candidate_injections, user_task_id)
                   for user_task_id in user_task_ids]
        return ((sum(item["security"] for item in details) / len(details))
                if details else 0.0), details

    def evaluate_stratified(self, injection_task_id, candidate_injections,
                            success_set, failure_set, total_pairs):
        details = []
        for user_task_id in success_set:
            item = self._eval_single(injection_task_id, candidate_injections, user_task_id)
            details.append(item)
            if not item["security"]:
                return sum(x["security"] for x in details) / total_pairs, details, True
        for user_task_id in failure_set:
            details.append(self._eval_single(
                injection_task_id, candidate_injections, user_task_id))
        return sum(x["security"] for x in details) / total_pairs, details, False

    def evaluate_with_screening(self, injection_task_id, candidate_injections,
                                screening_set, all_pairs, total_pairs):
        details = [self._eval_single(injection_task_id, candidate_injections, user_task_id)
                   for user_task_id in screening_set]
        if not any(item["security"] for item in details):
            return 0.0, details
        seen = set(screening_set)
        details.extend(self._eval_single(injection_task_id, candidate_injections, user_task_id)
                       for user_task_id in all_pairs if user_task_id not in seen)
        return sum(x["security"] for x in details) / total_pairs, details

    def run_with_trace(self, injection_task_id, candidate_injections, user_task_id,
                       verbose=False):
        result = self._run(injection_task_id, candidate_injections, user_task_id)
        detail = self._detail(user_task_id, injection_task_id, result)
        detail.update({
            "tool_calls": [
                {"function": item["source"], "args": item.get("arguments", {})}
                for item in result.get("observations", [])
            ],
            "failure_class": None if result["asr"] else (
                "defense_blocked" if result.get("incidents") else "agent_ignored"),
            "defense_blocked": bool(result.get("incidents")),
            "expected_calls": [],
        })
        return detail

    def reachability_no_tool_output(self, injection_task_id, vec_id, goal, user_task_ids):
        # AutoDojo already maps vectors to tasks that read them statically.  The
        # defended runner can suppress a read, which is not evidence that the
        # vector itself is unreachable, so do not discard such cells here.
        return []


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", default="slack")
    parser.add_argument("--user-task", required=True)
    parser.add_argument("--injection-task", required=True)
    parser.add_argument("--vector", required=True)
    parser.add_argument("--iterations", type=int, default=2)
    parser.add_argument("--n-variants", type=int, default=2)
    parser.add_argument("--attacker-model", default="deepseek-chat")
    parser.add_argument("--attacker-provider", choices=("deepseek", "yunwu"),
                        default="deepseek")
    parser.add_argument("--agent-model", default="deepseek-chat")
    parser.add_argument("--contract-model", default="deepseek-chat")
    parser.add_argument("--plant-model", default="deepseek-chat")
    parser.add_argument("--plant-review-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--plan-store", required=True)
    parser.add_argument("--prompt-log", required=True)
    return parser.parse_args()


def main():
    args = parse_args()
    key_name = "DEEPSEEK_API_KEY" if args.attacker_provider == "deepseek" else "YUNWU_API_KEY"
    key = read_config_key(key_name)
    if not key:
        raise RuntimeError(f"Missing {key_name} in config.txt or environment")
    os.environ.setdefault(key_name, key)
    os.environ["AUTODOJO_OUTPUT_DIR"] = str(Path(args.output_dir).resolve())
    autodojo.OUTPUT_CACHE_DIR = Path(os.environ["AUTODOJO_OUTPUT_DIR"])
    os.environ["OURS_CONTRACT_MODEL"] = args.contract_model
    os.environ["OURS_PLANT_MODEL"] = args.plant_model
    os.environ["OURS_PLANT_REVIEW_MODEL"] = args.plant_review_model
    os.environ["OURS_PLAN_STORE"] = str(Path(args.plan_store).resolve())
    llm_utils.PROVIDERS["deepseek"] = {
        "base_url": DEEPSEEK_BASE_URL,
        "api_key_env": "DEEPSEEK_API_KEY",
        "client_type": "openai",
    }
    llm_utils.PROVIDERS["yunwu"] = {
        "base_url": (read_config_key("YUNWU_API_URL") or "https://yunwu.ai/v1").rstrip("/"),
        "api_key_env": "YUNWU_API_KEY",
        "client_type": "openai",
    }
    # AutoDojo creates its own OpenAI-compatible client for every optimizer
    # request, bypassing code.internal_client.  Wrap those clients so attacker
    # usage follows the same durable api/api_logs contract as Agent/defender
    # calls.  Authorization headers/API keys are client state and are never
    # included in request_data.
    unlogged_client_factory = llm_utils.get_openai_client

    def logged_client_factory(provider="openrouter"):
        client = unlogged_client_factory(provider)
        if provider in {"deepseek", "yunwu"}:
            return _with_api_logging(client, args.attacker_model,
                                     f"autodojo-{provider}")
        return client

    llm_utils.get_openai_client = logged_client_factory
    autodojo.DojoASREvaluator = OursASREvaluator
    sys.argv = [
        "optimize_variants.py", "--suite", args.suite,
        "--n-variants", str(args.n_variants), "--iterations", str(args.iterations),
        "--model", args.attacker_model, "--provider", args.attacker_provider,
        "--eval-asr", "--target-model", args.agent_model,
        "--defense", "ours", "--run-defense",
        "--injection-tasks", args.injection_task,
        "--vectors", args.vector, "--user-tasks", args.user_task,
        "--seed-styles", "--store-traces", "--prompt-log", args.prompt_log,
    ]
    autodojo.main()


if __name__ == "__main__":
    main()
