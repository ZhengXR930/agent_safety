"""Build one deterministic CaMeL policy for the full effect-derived corpus."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from code.benchmarks.injecagent import load_tools


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--base-policy", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    artifact = json.loads(args.base_policy.read_text(encoding="utf-8"))
    tools = load_tools(args.data_dir)
    for cell in manifest["cells"]:
        envelope = cell["effect_envelope"]
        effect_tool = envelope["tool"]
        if cell["family"] == "dh":
            trusted = list(envelope["authorized_arguments"])
        else:
            trusted = list(envelope["authorized_fixed_arguments"])
        artifact["tools"][effect_tool]["trusted_arguments"] = trusted
        artifact["tools"][effect_tool]["allowed_private_sources"] = []
        artifact["tools"][effect_tool]["workflow_rationale"] = (
            "Exact task-literal effect arguments only; no private source "
            "may authorize or influence this effect.")
    artifact["schema"] = "injecagent-effect-derived-full-camel-policy-v1"
    artifact["generator_model"] = None
    artifact["generation_scope"] = (
        "deterministic compilation from frozen effect envelopes")
    artifact["manifest_sha256"] = manifest["manifest_sha256"]
    artifact["catalog_sha256"] = hashlib.sha256(
        (args.data_dir / "tools.json").read_bytes()).hexdigest()
    if set(artifact["tools"]) != set(tools):
        raise ValueError("base policy does not cover the complete catalog")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "manifest_sha256": manifest["manifest_sha256"],
        "effect_tools": len({
            cell["effect_envelope"]["tool"] for cell in manifest["cells"]
        }),
    }))


if __name__ == "__main__":
    main()
