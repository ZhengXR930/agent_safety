"""Build the trusted MSB case manifest from official dataset metadata."""

import json
from pathlib import Path

import yaml

from code.manifest.mcptox import registration


DEFAULT_CASE_PATH = Path(__file__).resolve().parent / "msb_cases.json"
DEFAULT_TOOL_PATH = Path(__file__).resolve().parent / "msb_tools.json"


def _jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines()
            if line.strip()]


def _slug(task: str) -> str:
    return task[:20].replace(" ", "_").replace(":", "").replace(
        "/", "").replace(".", "")


def _attack_tool_exists(root: Path, agent: str, tool: str) -> bool:
    if agent == "image_generation":
        return False
    directory = root / "data/tools/attack_tools" / agent
    return directory.is_dir() and tool in {
        path.name for path in directory.iterdir()}


def case_ids_from_logs(log_dir: Path, baseline: str) -> set[str]:
    """Recover the exact cases completed by one baseline implementation."""
    case_ids = set()
    for path in Path(log_dir).glob("*.operation.json"):
        parts = path.name.removesuffix(".operation.json").split("#")
        if len(parts) != 6:
            continue
        _model, separator, defense = parts[1].rpartition("+")
        if not separator or defense != baseline:
            continue
        case_ids.add("#".join((parts[0], *parts[2:])))
    if not case_ids:
        raise ValueError(f"no completed {baseline!r} MSB cases in {log_dir}")
    return case_ids


def build(root: Path, config_path: Path, *,
          allowed_case_ids: set[str] | None = None,
          alignment: dict | None = None) -> dict:
    config = yaml.safe_load(config_path.read_text())
    requested_types = config["attack_type"]
    available = _jsonl(root / "data/attack_type.jsonl")[-1]["attack_type"]
    attack_types = available if requested_types == ["all"] else requested_types
    tasks = _jsonl(root / "data/attack_task.jsonl")
    if config.get("attack_task", ["all"]) != ["all"]:
        tasks = [row for row in tasks
                 if row["attack_task"] in config["attack_task"]]
    agents = _jsonl(root / "data/agent_task.jsonl")
    if config.get("agents", ["all"]) != ["all"]:
        agents = [row for row in agents if row["agent_name"] in config["agents"]]
    skipped = set(config.get("skip_tools", []))
    restricted = ("tool_transfer", "name_overlap", "out_of_scope_parameter",
                  "preference_manipulation")
    source_only = {"out_of_scope_parameter", "search_term_deception",
                   "tool_transfer"}
    cases = []
    for attack_type in attack_types:
        for agent_row in agents:
            agent = agent_row["agent_name"]
            if ((agent == "information_retrieval") !=
                    (attack_type == "search_term_deception")):
                continue
            for task_tool in agent_row["task_tool"]:
                task, tool = task_tool["task"], task_tool["tool"]
                if (any(name in attack_type for name in restricted) and
                        not _attack_tool_exists(root, agent, tool)):
                    continue
                if tool in skipped and attack_type not in source_only:
                    continue
                for attack in tasks:
                    case_id = "#".join((attack_type, agent, _slug(task), tool,
                                        attack["attack_task"]))
                    cases.append({
                        "case_id": case_id, "attack_type": attack_type,
                        "agent": agent, "system_prompt": agent_row["system_prompt"],
                        "task": task, "tool": tool,
                        "attack_task": attack["attack_task"],
                        "implementation": attack["implementation"],
                    })
    ids = [case["case_id"] for case in cases]
    if len(ids) != len(set(ids)):
        raise RuntimeError("MSB case IDs collide after official task truncation")
    if allowed_case_ids is not None:
        missing = set(allowed_case_ids).difference(ids)
        if missing:
            raise ValueError(
                f"baseline alignment contains {len(missing)} unknown MSB cases")
        cases = [case for case in cases
                 if case["case_id"] in allowed_case_ids]
    return {"schema": "msb-case-manifest-v1",
            "source_config": str(config_path.resolve()),
            "skip_tools": sorted(skipped), "case_count": len(cases),
            "alignment": dict(alignment or {}), "cases": cases}


def validate_alignment(case_path=DEFAULT_CASE_PATH,
                       tool_path=DEFAULT_TOOL_PATH) -> None:
    """Require the frozen case and Tool manifests to cover the same servers."""
    cases = json.loads(Path(case_path).read_text(encoding="utf-8"))
    tools = json.loads(Path(tool_path).read_text(encoding="utf-8"))
    case_servers = {str(case["tool"]) for case in cases.get("cases", ())}
    tool_servers = set((tools.get("servers") or {}).keys())
    if case_servers != tool_servers:
        raise ValueError(
            "MSB case/Tool manifest mismatch: "
            f"missing={sorted(case_servers - tool_servers)}, "
            f"extra={sorted(tool_servers - case_servers)}")


def _server(catalog: dict, server_name: str) -> dict:
    if catalog.get("schema") != "msb-mcp-tool-manifest-v1":
        raise ValueError("unsupported MSB Tool manifest schema")
    server = (catalog.get("servers") or {}).get(str(server_name))
    if not isinstance(server, dict):
        raise KeyError(f"MSB server is not in the trusted manifest: {server_name}")
    tools = server.get("tools")
    if not isinstance(tools, list) or not tools:
        raise ValueError(f"MSB server has no registered Tools: {server_name}")
    names = [str(tool.get("name", "")) for tool in tools]
    if any(not name for name in names) or len(names) != len(set(names)):
        raise ValueError(f"invalid Tool names for MSB server: {server_name}")
    return server


def runtime_manifest(server_name: str, path=DEFAULT_TOOL_PATH):
    """Return the exact Tool boundaries exposed by one clean MCP server.

    MCP annotations are operator attestations.  A Tool is observation-only
    only when ``readOnlyHint`` is explicitly true; missing annotations are
    conservatively treated as an effect-bearing boundary.
    """
    catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    server = _server(catalog, server_name)
    tools = [dict(tool) for tool in server["tools"]]
    for tool in tools:
        tool["x-server"] = str(server_name)
        schema = dict(tool["inputSchema"])
        # In JSON Schema, an omitted ``required`` keyword means that no
        # property is required.  Materialize that fact for the strict runtime
        # manifest validator without changing the operator's schema semantics.
        schema.setdefault("required", [])
        tool["inputSchema"] = schema
    registrations = []
    for tool in tools:
        annotations = tool.get("annotations") or {}
        effect = annotations.get("readOnlyHint") is not True
        item = registration(server_name, tool, effect=effect)
        item["outputSchema"] = (tool.get("outputSchema") or
                                {"type": "string"})
        registrations.append(item)
    mapping = {tool["name"]: item["name"]
               for tool, item in zip(tools, registrations)}
    return tools, registrations, mapping
