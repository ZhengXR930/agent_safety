"""Run the official AutoDojo optimizer against a native AgentDojo defense."""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from code.internal_client import _with_api_logging, client_for_model, read_config_key


ROOT = Path(__file__).resolve().parents[1]
AUTODOJO = ROOT / "baseline" / "AutoDojo" / "agentdojo"
for path in (AUTODOJO / "variant_generation", AUTODOJO / "src"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))

import llm_utils  # noqa: E402
import optimize_variants as autodojo  # noqa: E402


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--defense", required=True)
    parser.add_argument("--suite", default="slack")
    parser.add_argument("--user-task")
    parser.add_argument("--injection-task")
    parser.add_argument("--vector")
    parser.add_argument("--iterations", type=int, default=8)
    parser.add_argument("--n-variants", type=int, default=5)
    parser.add_argument("--attacker-provider", choices=("deepseek", "yunwu"), default="yunwu")
    parser.add_argument("--attacker-model", default="gpt-5.5")
    parser.add_argument("--target-model", default="deepseek-chat")
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--prompt-log", required=True)
    parser.add_argument("--resume", action="store_true")
    return parser.parse_args()


def main():
    args = parse_args()
    provider_key = ("DEEPSEEK_API_KEY" if args.attacker_provider == "deepseek"
                    else "YUNWU_API_KEY")
    key = read_config_key(provider_key)
    if not key:
        raise RuntimeError(f"Missing {provider_key}")
    os.environ.setdefault(provider_key, key)

    llm_utils.PROVIDERS["deepseek"] = {
        "base_url": "https://api.deepseek.com", "api_key_env": "DEEPSEEK_API_KEY",
        "client_type": "openai",
    }
    llm_utils.PROVIDERS["yunwu"] = {
        "base_url": (read_config_key("YUNWU_API_URL") or "https://yunwu.ai/v1").rstrip("/"),
        "api_key_env": "YUNWU_API_KEY", "client_type": "openai",
    }
    original_client_factory = llm_utils.get_openai_client

    def logged_client_factory(provider="openrouter"):
        client = original_client_factory(provider)
        if provider in {"deepseek", "yunwu"}:
            return _with_api_logging(client, args.attacker_model,
                                     f"autodojo-{provider}")
        return client

    llm_utils.get_openai_client = logged_client_factory

    target_model, target_model_id = args.target_model, None
    if args.defense == "camel" and args.target_model == "deepseek-chat":
        deepseek_key = read_config_key("DEEPSEEK_API_KEY")
        if not deepseek_key:
            raise RuntimeError("Missing DEEPSEEK_API_KEY for CaMeL target")
        os.environ["CAMEL_LOCAL_BASE_URL"] = "https://api.deepseek.com"
        os.environ["CAMEL_API_KEY"] = deepseek_key
        target_model, target_model_id = "local", "deepseek-chat"
        # CaMeL consumes the named local target itself, while AutoDojo also
        # builds a separate no-defense reachability pipeline.  Route only that
        # `local` sentinel through the same DeepSeek API instead of OpenRouter.
        import agentdojo.agent_pipeline.agent_pipeline as pipeline_module
        from agentdojo.agent_pipeline.llms.openai_llm import OpenAILLM

        original_get_llm = pipeline_module.get_llm

        def get_llm_with_deepseek_local(model):
            if model == "local":
                llm = OpenAILLM(client_for_model("deepseek-chat"), "deepseek-chat")
                llm.name = "deepseek-chat"
                return llm
            return original_get_llm(model)

        pipeline_module.get_llm = get_llm_with_deepseek_local

    output_dir = Path(args.output_dir).resolve()
    os.environ["AUTODOJO_OUTPUT_DIR"] = str(output_dir)
    autodojo.OUTPUT_CACHE_DIR = output_dir
    argv = [
        "optimize_variants.py", "--suite", args.suite,
        "--n-variants", str(args.n_variants), "--iterations", str(args.iterations),
        "--model", args.attacker_model, "--provider", args.attacker_provider,
        "--eval-asr", "--target-model", target_model,
        "--defense", args.defense, "--run-defense", "--seed-styles", "--store-traces",
        "--prompt-log", args.prompt_log,
    ]
    if args.injection_task:
        argv.extend(("--injection-tasks", args.injection_task))
    if args.vector:
        argv.extend(("--vectors", args.vector))
    if args.user_task:
        argv.extend(("--user-tasks", args.user_task))
    if args.resume:
        argv.append("--resume")
    if target_model_id:
        argv.extend(("--target-model-id", target_model_id))
    sys.argv = argv
    autodojo.main()


if __name__ == "__main__":
    main()
