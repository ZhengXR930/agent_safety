"""MSB on its native MCPAgent runtime with WRAP/PLANT mediation.

The target Agent, real MCP servers, tool set, and ten-step execution loop are
the benchmark's.  Active Defense is inserted only at catalog exposure, tool
commit, observation receipt, and final-response boundaries.
"""
from __future__ import annotations

import argparse
import asyncio
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import site
import sys
import traceback

# The frozen MSB environment carries the benchmark's LangChain/mcp-use stack,
# while defender roles use the repository's current OpenAI Agents SDK.  Keep
# mcp-use on the venv's MCP SDK: pin OpenAI first, load mcp-use, then Agents.
_USER_SITE = site.getusersitepackages()
if _USER_SITE in sys.path:
    sys.path.remove(_USER_SITE)
sys.path.insert(0, _USER_SITE)
import openai as _openai  # noqa: F401,E402
sys.path.remove(_USER_SITE)

from langchain_deepseek import ChatDeepSeek  # noqa: E402
from mcp.types import CallToolResult, TextContent  # noqa: E402
from mcp_use import MCPAgent, MCPClient  # noqa: E402

sys.path.insert(0, _USER_SITE)
import agents as _agents  # noqa: F401,E402
sys.path.remove(_USER_SITE)

from code.benchmarks.mcp_common.runtime import (  # noqa: E402
    _continue,
    _decision_row,
    _msb_cases,
    _msb_contract_key,
    _msb_setup,
    _msb_utility_passed,
    _place_catalog,
    _record_operator_success,
    _summary,
)
from code.benchmarks.msb.execution.attack import (  # noqa: E402
    PROMPT_INJECTION_TEMPLATE,
    disallowed_tools as _disallowed_tools,
    finish as _finish_attack,
    prepare as _prepare_attack,
    response as _response_attack,
)
from code.core.client import read_config_key  # noqa: E402
from code.ours.defense.broker import UnitBroker  # noqa: E402


ROOT = Path(__file__).resolve().parents[4]
AGENT_SAFETY = ROOT.parent
MSB_ROOT = AGENT_SAFETY / "benchmarks/external/MSB"
NORMAL_TOOLS = MSB_ROOT / "data/tools/normal_tools"
SUPPORT_TOOLS = MSB_ROOT / "data/tools/support_tools"
ATTACK_TOOLS = MSB_ROOT / "data/tools/attack_tools"
NODE_BIN = (AGENT_SAFETY / "benchmarks/external/defender/.runtime/"
            "node-v22.17.0-linux-x64/bin")
PUA_UNDEFINED = {
    "false_error", "simulated_user",
    "prompt_injection-simulated_user", "prompt_injection-false_error",
}


def _load_key() -> None:
    if os.getenv("DEEPSEEK_API_KEY"):
        return
    key = read_config_key("DEEPSEEK_API_KEY", root=AGENT_SAFETY)
    if not key:
        raise RuntimeError("Missing DEEPSEEK_API_KEY")
    os.environ["DEEPSEEK_API_KEY"] = key


def _read_servers(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))["mcpServers"]


def _server_cwd(servers: dict) -> dict:
    """Run stdio servers from MSB's native working directory.

    mcp-use 1.3 has no cwd field for stdio connectors.  Wrapping only process
    launch preserves the benchmark commands while matching main.py's cwd.
    """
    rooted = json.loads(json.dumps(servers))
    for config in rooted.values():
        command = str(config["command"])
        command = shutil.which(command) or command
        argv = [command, *(str(arg) for arg in config.get("args") or ())]
        config["command"] = "/bin/bash"
        config["args"] = [
            "-c",
            f"cd {shlex.quote(str(MSB_ROOT))} && exec {shlex.join(argv)}",
        ]
    return rooted


def _clean_config(row: dict) -> tuple[dict, dict[str, str]]:
    """The benign pair uses the clean task server plus official support."""
    servers, roles = {}, {}
    if row["legit_tool"] == "Filesystem_MCP_Server":
        added = _read_servers(SUPPORT_TOOLS / "Filesystem_MCP_Server.json")
        servers.update(added)
        roles.update({name: "Filesystem_MCP_Server" for name in added})
    else:
        support = _read_servers(SUPPORT_TOOLS / "Filesystem_MCP_Server.json")
        normal = _read_servers(NORMAL_TOOLS / f"{row['legit_tool']}.json")
        servers.update(support)
        servers.update(normal)
        roles.update({name: "Filesystem_MCP_Server" for name in support})
        roles.update({name: row["legit_tool"] for name in normal})
    return {"mcpServers": _server_cwd(servers)}, roles


def _attack_config(row: dict, operation: str) -> tuple[dict, dict[str, str]]:
    """Reproduce MSB's official server composition for one attack case."""
    attack_type = row["attack_type"]
    attack_task = row["attack_task"]
    servers, roles = {}, {}
    if (attack_type not in {
            "out_of_scope_parameter", "tool_transfer",
            "preference_manipulation-out_of_scope_parameter"} or
            attack_type == "search_term_deception"):
        support = ("Desktop_Commander.json" if attack_task == "kill_process"
                   else "Filesystem_MCP_Server.json")
        added = _read_servers(SUPPORT_TOOLS / support)
        servers.update(added)
        roles.update({name: ("Filesystem_MCP_Server" if
                             support == "Filesystem_MCP_Server.json" else
                             "Desktop_Commander") for name in added})
    if attack_type not in {
            "out_of_scope_parameter", "search_term_deception",
            "tool_transfer"}:
        added = _read_servers(NORMAL_TOOLS / f"{row['legit_tool']}.json")
        servers.update(added)
        roles.update({name: row["legit_tool"] for name in added})
    injected = {
        "name_overlap", "preference_manipulation",
        "out_of_scope_parameter", "tool_transfer",
        "preference_manipulation-out_of_scope_parameter",
        "preference_manipulation-simulated_user",
    }
    if attack_type in injected:
        path = (ATTACK_TOOLS / row["agent"] / row["legit_tool"] /
                "mcp_config.json")
        attack = _read_servers(path)
        name, config = next(iter(attack.items()))
        config = json.loads(json.dumps(config))
        config["args"].extend((attack_type, attack_task, operation))
        suffix = ("preference_manipulation"
                  if attack_type == "preference_manipulation-simulated_user"
                  else attack_type)
        config["args"][3] = config["args"][3].replace(
            ".py", f"-{suffix}.py")
        attack_name = "attack-" + name
        servers[attack_name] = config
        roles[attack_name] = row["legit_tool"]
        if attack_type == "tool_transfer":
            addition = _read_servers(path)
            extra_name, extra = next(iter(addition.items()))
            extra = json.loads(json.dumps(extra))
            extra["args"].extend(
                ("out_of_scope_parameter", attack_task, operation))
            extra["args"][3] = extra["args"][3].replace(
                ".py", "-out_of_scope_parameter.py")
            addition_name = "addition-" + extra_name
            servers[addition_name] = extra
            roles[addition_name] = "Filesystem_MCP_Server"
    return {"mcpServers": _server_cwd(servers)}, roles


def _result_value(result: CallToolResult):
    if result.structuredContent is not None:
        return result.structuredContent
    text = "".join(
        item.text for item in result.content
        if getattr(item, "type", None) == "text")
    try:
        return json.loads(text)
    except (TypeError, json.JSONDecodeError):
        return text


def _tool_result(value, *, error=False) -> CallToolResult:
    text = (value if isinstance(value, str) else
            json.dumps(value, ensure_ascii=False, default=str))
    return CallToolResult(
        content=[TextContent(type="text", text=text)], isError=error)


async def _close_client(client: MCPClient) -> None:
    """Close stdio connections in their owning manager tasks.

    mcp-use 1.3 enters ClientSession from a different task than the caller of
    ``close_all_sessions``.  Closing that session directly violates AnyIO's
    cancel-scope ownership.  The connection manager owns the stdio context, so
    stopping it is both sufficient and the correctly scoped operation.
    """
    for session in tuple(client.sessions.values()):
        connector = session.connector
        manager = getattr(connector, "_connection_manager", None)
        connector.client_session = None
        if manager is not None:
            await asyncio.wait_for(manager.stop(), timeout=10)
        connector._connection_manager = None
        connector._connected = False
    client.sessions.clear()
    client.active_sessions.clear()


def _tool_alias(session: str, name: str) -> str:
    """Give colliding MCP exports stable OpenAI-compatible names."""
    prefix = re.sub(r"[^A-Za-z0-9_-]", "_", session)
    suffix = re.sub(r"[^A-Za-z0-9_-]", "_", name)
    return (prefix[:24] + "__" + suffix)[:64]


def _trusted_schema(surface) -> dict:
    return {
        "type": "object",
        "properties": dict(surface.argument_schemas),
        "required": list(surface.required_arguments),
        "additionalProperties": False,
    }


def _raw_tools(client: MCPClient, row: dict, mapping: dict,
               session_roles: dict, plan) -> tuple[list[dict], dict]:
    entries = []
    for session_name, session in client.sessions.items():
        for model in session.connector._tools:
            raw = model.model_dump(mode="json")
            name = str(raw["name"])
            declared = session_roles.get(session_name, row["legit_tool"])
            candidates = [server for server, tool in mapping if tool == name]
            if (declared, name) in mapping:
                owner = declared
            elif len(candidates) == 1:
                owner = candidates[0]
            elif ("Filesystem_MCP_Server", name) in mapping:
                owner = "Filesystem_MCP_Server"
            else:
                owner = declared
            capability = mapping.get((owner, name), name)
            entries.append((session_name, session, model, raw, name,
                            owner, capability))

    counts = {}
    for entry in entries:
        counts[entry[4]] = counts.get(entry[4], 0) + 1

    tools, bindings = [], {}
    for session_name, _session, model, raw, name, owner, capability in entries:
        exposed = (_tool_alias(session_name, name)
                   if counts[name] > 1 else name)
        surface = plan.capabilities.get(capability)
        actual_schema = raw.get("inputSchema") or {
            "type": "object", "properties": {}}
        schema = (_trusted_schema(surface)
                  if surface is not None else actual_schema)
        actual_properties = actual_schema.get("properties") or {}
        trusted_properties = schema.get("properties") or {}
        transport = {}
        for field in actual_schema.get("required") or ():
            if field in trusted_properties:
                continue
            field_schema = actual_properties.get(field) or {}
            if field_schema.get("type") == "string":
                transport[str(field)] = ""
        model.name = exposed
        model.inputSchema = schema
        description = raw.get("description") or ""
        tools.append({
            "name": exposed,
            "description": description,
            "inputSchema": schema,
            "outputSchema": raw.get("outputSchema"),
            "x-server": owner,
        })
        bindings[(session_name, exposed)] = {
            "original": name, "owner": owner,
            "capability": capability, "transport": transport,
        }
    return tools, bindings


async def _native_row(row: dict, frozen: dict, model: str,
                      contract_model: str, attacked: bool,
                      ablation_mode: str = "full") -> dict:
    shared = _msb_setup(
        contract_model, row, frozen, ablation_mode=ablation_mode)
    engine, contract = shared["engine"], shared["contract"]
    registrations, mapping = shared["registrations"], shared["mapping"]
    attack_context = _prepare_attack(row, model) if attacked else None
    payload = attack_context["payload"] if attack_context else ""
    operation = attack_context["operation_info"] if attack_context else ""
    config, session_roles = (_attack_config(row, operation) if attacked
                             else _clean_config(row))
    client = MCPClient.from_dict(config)
    decisions, proposals = [], []
    episode = engine.start(
        contract, f"msb-native-{row['case_id']}-{attacked}")
    broker = UnitBroker(episode, [{
        "name": name, "effect": surface.effect,
        "observation": surface.observation,
    } for name, surface in engine.plan.capabilities.items()])
    response = ""
    official_effect = None
    try:
        await client.create_all_sessions()
        actual, bindings = _raw_tools(
            client, row, mapping, session_roles, engine.plan)
        shown, _basis, proposals = _place_catalog(
            episode, row["agent"], actual)
        shown_by_name = {tool["name"]: tool["description"] for tool in shown}
        prompt_injection = ""
        if attacked and "prompt_injection" in row["attack_type"]:
            raw_injection = PROMPT_INJECTION_TEMPLATE.replace(
                "{goal}", payload)
            view = episode.place_carrier(
                "msb:official-prompt-injection", raw_injection,
                modes=("marker",), schema={"type": "string"})
            prompt_injection = str(view.value)
            proposals.append({"tool": "$prompt_injection", **view.proposal})

        for session_name, session in client.sessions.items():
            connector = session.connector
            for tool in connector._tools:
                if tool.name in shown_by_name:
                    tool.description = shown_by_name[tool.name]
            original = connector.call_tool

            async def guarded(name, arguments, *, _original=original,
                              _session=session_name):
                arguments = dict(arguments or {})
                binding = bindings.get((_session, name), {
                    "original": name, "owner": row["legit_tool"],
                    "capability": name, "transport": {},
                })
                original_name = binding["original"]
                capability = binding["capability"]
                surface = engine.plan.capabilities.get(capability)
                prepared = broker.prepare(capability, arguments)
                arguments = dict(prepared.invocation.arguments)
                decision = prepared.decision
                decision, authorized = _continue(
                    episode, decision, arguments)
                authorized = broker.canonical_arguments(
                    capability, authorized)
                broker.record_decision(prepared, decision, authorized)
                decisions.append(_decision_row(
                    original_name, authorized, (), decision))
                if decision.route != "pass":
                    return _tool_result({
                        "status": "not_executed",
                        "route": decision.route,
                        "reason": decision.reason,
                        "continuation": dict(decision.continuation),
                    })
                owner = binding["owner"]
                response_only = bool(
                    attacked and owner != "Filesystem_MCP_Server" and
                    ("false_error" in row["attack_type"] or
                     ("simulated_user" in row["attack_type"] and
                      row["attack_type"] !=
                      "preference_manipulation-simulated_user")))
                if response_only:
                    value = _response_attack(row, payload, owner, "")
                else:
                    transport_arguments = {
                        **binding["transport"], **authorized}
                    with broker.execution(prepared):
                        result = await _original(
                            original_name, transport_arguments)
                    if result.isError:
                        return result
                    broker.succeeded(prepared, authorized)
                    value = _result_value(result)
                    if attacked:
                        value = _response_attack(row, payload, owner, value)
                view = episode.observe(
                    capability, authorized, value,
                    placement_schema=(surface.output_schema
                                      if surface is not None else None),
                    return_view=True)
                return _tool_result(view.value)

            connector.call_tool = guarded

        from data.prompt_template import SYSTEM_PROMPT_TEMPLATE
        system_template = row["system"] + SYSTEM_PROMPT_TEMPLATE
        if prompt_injection:
            system_template = system_template.replace(
                "{tool_descriptions}",
                "{tool_descriptions}\n" + prompt_injection)
        agent = MCPAgent(
            llm=ChatDeepSeek(model=model, max_retries=2),
            client=client, max_steps=10, memory_enabled=False,
            system_prompt_template=system_template,
            disallowed_tools=_disallowed_tools(row))
        response = await agent.run(row["task"], max_steps=10)
        response_decision = episode.response(response)
        decisions.append(_decision_row(
            "$response", {"value": response}, (), response_decision))
    finally:
        try:
            await _close_client(client)
        except BaseException as exc:
            print(json.dumps({"cleanup_warning": repr(exc)}), flush=True)
        if attack_context:
            official_effect = _finish_attack(
                attack_context, row["attack_task"])
    audit = episode.close()
    mode = "attack" if attacked else "clean"
    return {
        "dataset": "MSB", "suite": row["attack_type"], "mode": mode,
        "task": row["task"], "contract": contract.to_dict(),
        "manifest_count": len(registrations),
        "manifest_source": "clean MCP tools/list snapshot",
        "case_id": row["case_id"], "attack_task": row["attack_task"],
        "attack_payload": payload if attacked else "",
        "proposals": proposals, "decisions": decisions,
        "utility": _msb_utility_passed(row, decisions),
        # MSB calls attack-side utility PUA.  Its official report leaves PUA
        # undefined when the attack construction precludes task completion;
        # retain the task-completion witness above for our all-case AU, while
        # marking the benchmark-native PUA denominator explicitly.
        "pua_eligible": row["attack_type"] not in PUA_UNDEFINED,
        "attack_success": bool(
            attacked and official_effect["attack_success"]),
        "official_effect": official_effect,
        "response": response,
        "unit_broker": broker.invocation_receipts(), "audit": audit,
    }


def _native_case(row, frozen, model: str, contract_model: str,
                 modes: tuple[bool, ...],
                 ablation_mode: str = "full") -> list[dict]:
    async def run():
        return [await _native_row(
            row, frozen, model, contract_model, attacked,
            ablation_mode=ablation_mode)
                for attacked in modes]
    return asyncio.run(run())


def _failure_ids(path: Path, modes: set[str]) -> set[str]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {
        row["case_id"] for row in data.get("rows") or ()
        if row.get("mode") in modes and
        not _msb_utility_passed(row, row.get("decisions") or [])
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="deepseek-v4-flash")
    parser.add_argument("--contract-model", default="gpt-5.5-2026-04-24")
    parser.add_argument("--ablation-mode",
                        choices=("full", "wrap_only", "plant_only"),
                        default="full")
    parser.add_argument("--workers", type=int, default=1)
    parser.add_argument("--mode", choices=("pair", "clean", "attack"),
                        default="pair")
    parser.add_argument("--msb-start", type=int, default=0)
    parser.add_argument("--msb-limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--rerun-failures-from", type=Path)
    parser.add_argument("--case-id", action="append",
                        help="run only this exact frozen case id; repeatable")
    parser.add_argument("--contracts-input", type=Path,
                        help="read-only reviewed Contract catalog to reuse")
    parser.add_argument("--contracts-output", type=Path,
                        help="deprecated alias for --contracts-input")
    parser.add_argument("--frozen-contracts-only", action="store_true",
                        help="fail if any selected case is absent from contracts-input")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.workers < 1:
        raise ValueError("workers must be positive")
    modes = {"pair": (False, True), "clean": (False,),
             "attack": (True,)}[args.mode]
    required_modes = {"attack" if attacked else "clean"
                      for attacked in modes}
    _load_key()
    if NODE_BIN.is_dir():
        os.environ["PATH"] = str(NODE_BIN) + os.pathsep + os.environ.get("PATH", "")
    sys.path.insert(0, str(MSB_ROOT))

    contracts_input = args.contracts_input or args.contracts_output
    if contracts_input is None:
        raise ValueError("MSB native active-defense runs require contracts-input")
    catalog = json.loads(contracts_input.read_text(encoding="utf-8"))
    cases = _msb_cases(args.msb_start, args.msb_limit)
    if args.case_id:
        selected = set(args.case_id)
        cases = [row for row in cases if row["case_id"] in selected]
    if args.rerun_failures_from:
        selected = _failure_ids(args.rerun_failures_from, required_modes)
        cases = [row for row in cases if row["case_id"] in selected]
    rows = []
    if args.resume and args.output.is_file():
        previous = json.loads(args.output.read_text(encoding="utf-8"))
        expected = {
            "model": args.model,
            "contract_model": args.contract_model,
            "ablation_mode": args.ablation_mode,
        }
        if any(previous.get(key) not in (None, value)
               for key, value in expected.items()):
            raise ValueError("resume artifact does not match MSB run config")
        rows = list(previous.get("rows") or ())
    done = {row["case_id"] for row in rows
            if required_modes.issubset({
                item["mode"] for item in rows
                if item["case_id"] == row["case_id"]})}

    def checkpoint():
        summary = _summary(rows)
        pua_rows = [row for row in rows
                    if row["mode"] == "attack" and row["pua_eligible"]]
        summary.update({
            "pua_n": len(pua_rows),
            "pua_success": sum(row["utility"] for row in pua_rows),
        })
        result = {
            "schema": "msb-native-defense-v2",
            "model": args.model,
            "contract_model": args.contract_model,
            "ablation_mode": args.ablation_mode,
            "rows": rows,
            "summary": summary,
        }
        pending = args.output.with_suffix(args.output.suffix + ".tmp")
        pending.write_text(json.dumps(
            result, ensure_ascii=False, indent=2, default=str))
        pending.replace(args.output)
        print(json.dumps(result["summary"]), flush=True)

    jobs = []
    missing_contracts = []
    for row in cases:
        if row["case_id"] in done:
            continue
        key = _msb_contract_key(row)
        entry = (catalog.get("contracts") or {}).get(key)
        if not isinstance(entry, dict) or not isinstance(
                entry.get("contract"), dict):
            missing_contracts.append((row["case_id"], key))
            continue
        frozen = entry["contract"]
        jobs.append((row, frozen))
    if missing_contracts:
        examples = "; ".join(
            f"{case_id}:{key}" for case_id, key in missing_contracts[:10])
        raise ValueError(
            "frozen MSB contracts missing "
            f"{len(missing_contracts)} selected cases; examples: {examples}")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        pending = {
            pool.submit(_native_case, row, frozen, args.model,
                        args.contract_model, modes,
                        args.ablation_mode): row["case_id"]
            for row, frozen in jobs}
        for future in as_completed(pending):
            case_id = pending[future]
            try:
                rows.extend(future.result())
                checkpoint()
            except BaseException as exc:
                print(json.dumps({"job": case_id,
                                  "error": repr(exc),
                                  "traceback": traceback.format_exc()}),
                      flush=True)
    checkpoint()


if __name__ == "__main__":
    main()
