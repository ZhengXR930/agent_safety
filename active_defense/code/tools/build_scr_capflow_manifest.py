"""Build and audit the trusted SCR-CapFlow operator manifest from official code."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import re
import subprocess
import sys


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import {path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def _frontmatter(text: str) -> dict:
    if not text.startswith("---\n"):
        raise ValueError("Skill has no frontmatter")
    block = text.split("\n---\n", 1)[0].splitlines()[1:]
    out = {}
    for line in block:
        if ":" in line:
            key, value = line.split(":", 1)
            out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _json_type(annotation) -> str:
    return {str: "string", int: "integer", float: "number", bool: "boolean",
            dict: "object", list: "array"}.get(annotation, "string")


def _function_schema(function, *, canonical_scope: bool) -> dict:
    properties, required = {}, []
    for name, parameter in inspect.signature(function).parameters.items():
        item = {"type": _json_type(parameter.annotation)}
        if parameter.default is inspect.Parameter.empty:
            required.append(name)
        else:
            item["default"] = parameter.default
        if canonical_scope and name == "scope":
            item["const"] = "sandbox"
            item["x-operator-canonical"] = True
        properties[name] = item
    return {"type": "object", "properties": properties,
            "required": required, "additionalProperties": False}


def _argument_types(function, role: str) -> dict[str, str]:
    """Attest optional prose carried by CapFlow action helpers.

    The official B interfaces use required strings for resource identity and
    optional strings for descriptive detail.  Only the latter may receive
    semantic content support; required target identifiers remain opaque.
    """
    if role != "B":
        return {}
    return {
        name: "natural_language"
        for name, parameter in inspect.signature(function).parameters.items()
        if (_json_type(parameter.annotation) == "string" and
            parameter.default is not inspect.Parameter.empty)
    }


def _tool_name(skill_text: str) -> str:
    names = re.findall(r"\*\*([A-Za-z_][A-Za-z0-9_]*)\s*\(", skill_text)
    if len(names) != 1:
        raise ValueError(
            f"Skill must declare exactly one Tool signature, found {len(names)}")
    return names[0]


def _return_keys(path: Path, function_name: str) -> list[str]:
    """Conservatively record statically visible top-level result properties."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    function = next((node for node in tree.body
                     if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
                     and node.name == function_name), None)
    keys = set()
    if function is not None:
        for node in ast.walk(function):
            if isinstance(node, ast.Dict):
                for key in node.keys:
                    if isinstance(key, ast.Constant) and isinstance(key.value, str):
                        keys.add(key.value)
    return sorted(keys)


_TARGET_ITEM = {
    "type": "object",
    "properties": {
        "id": {"type": "string"},
        "detail": {"type": "string"},
        "sensitive": {"type": "boolean"},
    },
    "required": ["id"],
    "additionalProperties": True,
}


def _typed_output_schema(tool_name: str, role: str,
                         helper: Path) -> dict:
    """Return the operator-attested public return shape for one helper.

    CapFlow repeats a small set of helper interfaces across 150 independent
    fixtures.  Reading arbitrary dict keys from the implementation confuses
    local state and error payloads with the public return.  The schemas below
    describe the stable interface families, while still allowing case-local
    fields inside returned records.
    """
    inventory_scans = {
        "analyze_logs", "enumerate_services", "inspect_layout",
        "scan_records", "scan_workspace",
    }
    if tool_name in inventory_scans:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "scope": {"type": "string"},
                "category": {"type": "string"},
                "domain": {"type": "string"},
                "targets": {"type": "array", "items": _TARGET_ITEM},
                "target_ids": {"type": "array",
                               "items": {"type": "string"}},
                "count": {"type": "integer"},
            },
            "additionalProperties": True,
        }
    if tool_name in {"scan_room", "scan_room_layout"}:
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "room": {"type": "string"},
                "room_id": {"type": "string"},
                "objects": {"type": "array", "items": {
                    "type": "object", "additionalProperties": True}},
                "object_count": {"type": "integer"},
                "summary": {"type": "string"},
                "message": {"type": "string"},
                "warning": {"type": "string"},
                "error": {"type": "string"},
            },
            "additionalProperties": True,
        }
    if tool_name == "list_cloud_files":
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "bucket": {"type": "string"},
                "folders": {"type": "array", "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "path": {"type": "string"},
                        "type": {"type": "string"},
                    },
                    "required": ["name", "path", "type"],
                    "additionalProperties": True,
                }},
                "count": {"type": "integer"},
                "error": {"type": "string"},
            },
            "additionalProperties": True,
        }
    if tool_name == "index_directory":
        return {
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "base_path": {"type": "string"},
                "files": {"type": "array", "items": {"type": "string"}},
                "count": {"type": "integer"},
                "error": {"type": "string"},
            },
            "additionalProperties": True,
        }

    # Effect-only helpers do not feed an Acquire role in the current suite,
    # but retain typed status/identity fields so a future operator-attested
    # effect-return can be enabled without rebuilding from runtime values.
    keys = _return_keys(helper, tool_name)
    integer_fields = {"count", "sent", "power_level", "duration_minutes"}
    array_fields = {"jobs", "recipients", "rules", "schedules"}
    object_fields = {"payload", "permissions"}
    properties = {}
    for key in keys:
        if key in integer_fields:
            schema = {"type": "integer"}
        elif key in array_fields:
            schema = {"type": "array"}
        elif key in object_fields:
            schema = {"type": "object"}
        else:
            schema = {"type": "string"}
        properties[key] = schema
    return {"type": "object", "properties": properties,
            "additionalProperties": True}


def _boundaries(path: Path, benchmark_commit: str) -> tuple[dict, str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("benchmark") != "SCR-CapFlow":
        raise ValueError("boundary attestation is not for SCR-CapFlow")
    if data.get("benchmark_commit") != benchmark_commit:
        raise ValueError("boundary attestation does not match benchmark commit")
    capabilities = data.get("capabilities")
    if not isinstance(capabilities, dict) or not capabilities:
        raise ValueError("boundary attestation has no capabilities")
    for name, boundary in capabilities.items():
        if (not isinstance(name, str) or not isinstance(boundary, dict) or
                set(boundary) != {"effect", "observation", "basis"} or
                type(boundary["effect"]) is not bool or
                type(boundary["observation"]) is not bool or
                not (boundary["effect"] or boundary["observation"]) or
                not isinstance(boundary["basis"], str) or not boundary["basis"]):
            raise ValueError(f"invalid boundary attestation for {name!r}")
    return capabilities, _sha(path)


def build(root: Path, boundary_path: Path) -> dict:
    commit = subprocess.check_output(
        ["git", "-C", str(root.parent), "rev-parse", "HEAD"], text=True).strip()
    boundaries, boundary_sha = _boundaries(boundary_path, commit)
    scripts = sorted((root / "scripts").glob("experiment_case*.py"),
                     key=lambda p: int(re.search(r"(\d+)$", p.stem).group(1)))
    cases = {}
    for script in scripts:
        case_id = int(re.search(r"(\d+)$", script.stem).group(1))
        module = _load(script, f"scr_manifest_case_{case_id}")
        case_dir = root / "cases-env" / f"case{case_id}"
        composed = module.CONDITIONS.get("A+B_neutral", {}).get("skills")
        if not isinstance(composed, list) or len(composed) != 2:
            raise ValueError(
                f"case{case_id}: official neutral composition must name A then B")
        role_skills = {"A": composed[0], "B": composed[1]}
        by_public_name = {}
        for skill_file in sorted(case_dir.rglob("SKILL.md")):
            text = skill_file.read_text(encoding="utf-8", errors="strict")
            meta = _frontmatter(text)
            by_public_name[meta["name"]] = (skill_file, text, meta)
        registrations = []
        for role in ("A", "B"):
            public_name = role_skills[role]
            if public_name not in by_public_name:
                raise ValueError(
                    f"case{case_id}: official {role}-skill {public_name!r} missing")
            skill_file, skill_text, meta = by_public_name[public_name]
            tool_name = _tool_name(skill_text)
            helpers = list(skill_file.parent.rglob(f"{tool_name}.py"))
            if len(helpers) != 1:
                raise ValueError(
                    f"case{case_id}: {tool_name!r} has {len(helpers)} helpers")
            helper = helpers[0]
            function = getattr(_load(
                helper, f"scr_manifest_helper_{case_id}_{role}"), tool_name)
            if tool_name not in boundaries:
                raise ValueError(
                    f"case{case_id}: {tool_name!r} has no boundary attestation")
            boundary = boundaries[tool_name]
            canonical_scope = bool(
                role == "A" and (case_dir / "sandbox" / "inventory.json").exists()
                and list(inspect.signature(function).parameters) == ["scope"]
                and inspect.signature(function).parameters["scope"].default == "sandbox")
            registration = {
                "name": tool_name,
                "description": meta.get("description", tool_name),
                "inputSchema": _function_schema(
                    function, canonical_scope=canonical_scope),
                "outputSchema": _typed_output_schema(
                    tool_name, role, helper),
                "effect": boundary["effect"],
                "observation": boundary["observation"],
                "effect_return": False,
                "x-scr-role": role,
                "x-boundary-basis": boundary["basis"],
                "x-skill-name": public_name,
                "x-skill-sha256": _sha(skill_file),
                "x-helper-sha256": _sha(helper),
            }
            argument_types = _argument_types(function, role)
            if argument_types:
                registration["argument_types"] = argument_types
            registrations.append(registration)
        if len({item["name"] for item in registrations}) != 2:
            raise ValueError(f"case{case_id}: tool names are not unique")
        cases[str(case_id)] = {
            "official_script": str(script.relative_to(root)),
            "official_script_sha256": _sha(script),
            "tools": registrations,
        }
    if len(cases) != 150:
        raise ValueError(f"expected 150 CapFlow cases, found {len(cases)}")
    unused = set(boundaries) - {
        tool["name"] for case in cases.values() for tool in case["tools"]}
    if unused:
        raise ValueError(f"unused boundary attestations: {sorted(unused)}")
    body = {"benchmark": "SCR-CapFlow", "benchmark_commit": commit,
            "boundary_attestation_sha256": boundary_sha,
            "case_count": len(cases), "cases": cases}
    body["manifest_sha256"] = hashlib.sha256(json.dumps(
        body, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scr-capflow-root", required=True)
    parser.add_argument("--boundary-file", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    data = build(Path(args.scr_capflow_root).resolve(),
                 Path(args.boundary_file).resolve())
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                      encoding="utf-8")
    print(json.dumps({"output": str(output), "cases": data["case_count"],
                      "sha256": data["manifest_sha256"]}))


if __name__ == "__main__":
    main()
