"""End-to-end MCP-Guard evaluation on native MCPTox clean/attack sets."""
from __future__ import annotations

import argparse
import asyncio
import concurrent.futures
import contextlib
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

from code.benchmarks.mcptox.execution.stackone_e2e import (
    REPO, WORKSPACE, _TOOL, _cases, _checkpoint, _replay_cases, _run_one,
    _summary,
)
from code.benchmarks.mcptox.protocol_runtime import protocol_identity
from code.core.client import client_for_model


MCP_GUARD = WORKSPACE / "benchmarks/external/MCP-Guard"


class MCPGuardScanner:
    """Persistent upstream MCP-Guard scanner with content-addressed caching."""

    def __init__(self, cache_path: Path, detail_log: Path):
        self.cache_path = cache_path
        self.detail_log = detail_log
        self.cache = (
            json.loads(cache_path.read_text(encoding="utf-8"))
            if cache_path.exists() else {}
        )
        sys.path.insert(0, str(MCP_GUARD))
        previous = Path.cwd()
        try:
            os.chdir(MCP_GUARD)
            try:
                from src.mcp_guard.core import guardrail_scan
                from src.mcp_guard.schemas import GuardrailRequest
                self.guardrail_scan = guardrail_scan
                self.request = GuardrailRequest
                self.local_detectors = None
                self.degraded_imports = []
            except ModuleNotFoundError as exc:
                # Upstream imports LearnableShield's heavy torch/onnx stack at
                # module import time, before its own try/except degradation can
                # run. Keep the official local rule detectors active instead of
                # failing the whole baseline when that optional stack is absent.
                if exc.name not in {
                    "torch", "onnx", "onnx2pytorch", "transformers",
                }:
                    raise
                from src.mcp_guard.detectors.cross_origin_detector import (
                    CrossOriginViolationDetector,
                )
                from src.mcp_guard.detectors.important_tag_detector import (
                    ImportantTagDetector,
                )
                from src.mcp_guard.detectors.prompt_injection_detector import (
                    PromptInjectionDetector,
                )
                from src.mcp_guard.detectors.sensitive_file_detector import (
                    SensitiveFileAccessDetector,
                )
                from src.mcp_guard.detectors.shadow_detector import (
                    ShadowHijackDetector,
                )
                from src.mcp_guard.detectors.shell_injection_detector import (
                    ShellInjectionDetector,
                )
                from src.mcp_guard.detectors.sql_injection_detector import (
                    SQLInjectionDetector,
                )
                self.guardrail_scan = None
                self.request = None
                self.local_detectors = [
                    ("prompt_injection_detector", PromptInjectionDetector()),
                    ("sensitive_file_detector", SensitiveFileAccessDetector()),
                    ("shell_detector", ShellInjectionDetector()),
                    ("sql_detector", SQLInjectionDetector()),
                    ("shadow_detector", ShadowHijackDetector()),
                    ("cross_origin_detector", CrossOriginViolationDetector()),
                    ("important_tag_detector", ImportantTagDetector()),
                ]
                self.degraded_imports = [
                    "learnableshield_detector", "model_detector",
                    f"missing_{exc.name}",
                ]
        finally:
            os.chdir(previous)
        self.new = 0

    async def _scan(self, name: str, description: str, schema: dict) -> dict:
        self.detail_log.parent.mkdir(parents=True, exist_ok=True)
        with self.detail_log.open("a", encoding="utf-8") as log:
            with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                if self.guardrail_scan is None:
                    response = self._scan_local(description)
                else:
                    response = await self.guardrail_scan(self.request(
                        tool_name=name, tool_description=description,
                        tool_input_schema=schema))
        if hasattr(response, "dict"):
            response = response.dict()
        return {
            "allowed": bool(response.get("allowed", True)),
            "stage": response.get("detection_stage"),
            "issue_count": len(response.get("issues", [])),
            "degraded_detectors": list(
                response.get("degraded_detectors") or ()),
        }

    def _scan_local(self, description: str) -> dict:
        issues, degraded = [], list(self.degraded_imports)
        assert self.local_detectors is not None
        for detector_name, detector in self.local_detectors:
            try:
                issues.extend(detector.detect(description) or [])
            except Exception:  # noqa: BLE001 - mirror upstream degradation
                degraded.append(detector_name)
        return {
            "allowed": len(issues) == 0,
            "issues": issues,
            "detection_stage": "local",
            "degraded_detectors": degraded,
        }

    def scan(self, name: str, description: str, schema: dict) -> dict:
        digest = hashlib.sha256((
            name + "\0" + description + "\0" +
            json.dumps(schema, sort_keys=True)).encode()).hexdigest()
        if digest in self.cache:
            return self.cache[digest]
        result = asyncio.run(self._scan(name, description, schema))
        self.cache[digest] = result
        self.new += 1
        if self.new % 10 == 0:
            self.save()
            print("mcpguard scans", len(self.cache), flush=True)
        return result

    def save(self) -> None:
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        pending = self.cache_path.with_suffix(self.cache_path.suffix + ".tmp")
        pending.write_text(
            json.dumps(self.cache, ensure_ascii=False, indent=2),
            encoding="utf-8")
        pending.replace(self.cache_path)


def _tool_fields(block: str) -> tuple[str, dict]:
    """Decode MCPTox's rendered catalog into MCP-Guard's native fields."""
    description_match = re.search(
        r"(?ms)^Description:\s*(.*?)\nArguments:\s*\n", block)
    description = (description_match.group(1).strip()
                   if description_match else "")
    arguments = block[description_match.end():] if description_match else ""
    properties, required = {}, []
    for match in re.finditer(r"(?m)^-\s*([^:]+):\s*(.*)$", arguments):
        field, help_text = match.group(1).strip(), match.group(2).strip()
        properties[field] = {"type": "string", "description": help_text}
        if "(required)" in help_text:
            required.append(field)
    return description, {
        "type": "object", "properties": properties,
        "required": required, "additionalProperties": False,
    }


def _filter_system(scanner: MCPGuardScanner, system: str):
    matches = list(_TOOL.finditer(system))
    decisions, kept = [], []
    for match in matches:
        name, block = match.group(1).strip(), match.group(0)
        description, schema = _tool_fields(block)
        verdict = scanner.scan(name, description, schema)
        decisions.append({"tool": name, **verdict})
        if verdict["allowed"]:
            kept.append(block.rstrip())
    prefix = system[:matches[0].start()].rstrip() if matches else system.rstrip()
    suffix = system[matches[-1].end():].strip() if matches else ""
    parts = [prefix, *kept]
    if suffix:
        parts.append(suffix)
    return "\n\n\n".join(part for part in parts if part), decisions


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--evaluation-model", default="gpt-5.4-2026-03-05")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mcptox-replay-rows", type=Path,
                        help="MCP-ITP result JSON whose optimized rows replace attack catalogs")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args()
    if args.workers < 1 or (args.limit is not None and args.limit < 1):
        raise ValueError("workers and limit must be positive")
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    if args.mcptox_replay_rows:
        clean_cases, attack_cases = [], _replay_cases(
            args.mcptox_replay_rows, args.limit)
    else:
        clean_cases, attack_cases = _cases(args.limit)
    protocol = protocol_identity()
    # Construct experiment clients before importing MCP-Guard. Its upstream
    # package loads its own .env for optional detectors; those credentials are
    # not the target-model or judge credentials for this benchmark run.
    agent = client_for_model(args.model)
    evaluator = client_for_model(args.evaluation_model)
    scanner = MCPGuardScanner(
        output.parent / "mcpguard_scan_cache.json",
        output.parent / "mcpguard_detector.log")
    for cases in (clean_cases, attack_cases):
        for index, case in enumerate(cases, 1):
            defended, decisions = _filter_system(scanner, case["system"])
            case["defended_system"] = defended
            case["scan_decisions"] = decisions
            case["blocked_tools"] = [
                row["tool"] for row in decisions if not row["allowed"]]
            if index % 100 == 0:
                scanner.save()
                print("catalog", index, "/", len(cases), flush=True)
    scanner.save()

    result = (
        json.loads(output.read_text(encoding="utf-8"))
        if args.resume and output.exists() else {
            "schema": "mcptox-mcpguard-e2e-v2",
            "benchmark": "MCPTox", "condition": "mcpguard_e2e",
            "model": args.model, "evaluation_model": args.evaluation_model,
            "protocol": protocol,
            "mcpguard": {
                "boundary": "MCP catalog before target inference",
                "implementation": "upstream guardrail_scan",
            },
            "workers": args.workers, "limit": args.limit,
            "mcptox_replay_rows": (
                str(args.mcptox_replay_rows) if args.mcptox_replay_rows else None),
            "clean": [], "attack": [],
        }
    )
    expected_resume = {
        "schema": "mcptox-mcpguard-e2e-v2",
        "model": args.model,
        "evaluation_model": args.evaluation_model,
        "limit": args.limit,
        "mcptox_replay_rows": (
            str(args.mcptox_replay_rows) if args.mcptox_replay_rows else None),
        "protocol": protocol,
    }
    if any(result.get(key) != value
           for key, value in expected_resume.items()):
        raise ValueError(
            "resume artifact protocol/model/evaluator/limit does not match invocation")
    for mode, cases in (("clean", clean_cases), ("attack", attack_cases)):
        done = {row["key"] for row in result[mode]
                if row.get("status") == "ok"}
        pending = [case for case in cases if case["key"] not in done]
        with concurrent.futures.ThreadPoolExecutor(
                max_workers=args.workers) as pool:
            futures = {
                pool.submit(_run_one, agent, args.model, evaluator,
                            args.evaluation_model, case, mode): case
                for case in pending
            }
            for index, future in enumerate(
                    concurrent.futures.as_completed(futures), 1):
                row = future.result()
                case = futures[future]
                row["scan_decisions"] = case["scan_decisions"]
                row["blocked_tools"] = case["blocked_tools"]
                result[mode] = [old for old in result[mode]
                                if old["key"] != row["key"]]
                result[mode].append(row)
                if index % 10 == 0 or index == len(pending):
                    _checkpoint(output, result)
                    print(mode, len(result[mode]), "/", len(cases),
                          json.dumps(_summary(result[mode]),
                                     ensure_ascii=False), flush=True)
    _checkpoint(output, result)
    print(json.dumps({
        "output": str(output), "clean": result["clean_summary"],
        "attack": result["attack_summary"],
        "finished_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
