"""Build a trusted MCPTox operator manifest without trusting poisoned prose.

The runtime adapter attests method identity and JSON schema.  The benchmark's
clean catalog is operator input; its structured parameter declarations may
repair a lossy wrapper schema.  Attack descriptions remain untrusted
observation content, and attack-only methods receive a neutral description
derived solely from their registered method name.  This lets the Contract use
an installed method without accepting a poisoned prerequisite.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
import re
from pathlib import Path

from code.ours.defense.memory import CapabilitySurface, EnvironmentPlan
from code.benchmarks.mcp_common.runtime import _blocks, _canonical


DEFAULT_OPERATOR_SCHEMAS = Path(__file__).resolve().parent / "data/operator_schemas.json"
REPOSITORY = Path(__file__).resolve().parents[3]

_OBSERVATION_PREFIXES = (
    "get_", "read_", "list_", "search_", "find_", "fetch_",
    "retrieve_", "query_", "lookup_", "describe_", "check_",
    "simple_", "calculate_", "compute_", "count_",
)

# Operator-side argument roles, derived from stable method/schema identifiers
# rather than agent-visible Tool descriptions. These roles do not change the
# byte-exact MCPTox catalog. They only tell WRAP which bounded task-root Derive
# values may be checked semantically instead of requiring byte equality.
_NATURAL_LANGUAGE_ARGUMENTS = frozenset({
    "prompt", "query", "q", "task", "html", "subject", "title",
    "description", "message", "detail", "observations",
    "location", "origin", "origins", "destination",
    "country", "language", "city", "cityd", "hl", "gl", "reaction",
    "symbol", "interval",
})
_CODE_ARGUMENTS = frozenset({"code", "command", "script"})
_PATH_ARGUMENTS = frozenset({"path", "projectcwd"})

_DOCUMENTED_PARAMETERS = re.compile(
    r"The parameters should be:\s*(\[[^\n]*\])", re.IGNORECASE)
_REQUEST_DATA_PREFIX = re.compile(
    r"The request data should be:\s*", re.IGNORECASE)
_JSON_TYPES = frozenset({
    "array", "boolean", "integer", "null", "number", "object", "string",
})


def _argument_type(argument: str) -> str | None:
    """Return a conservative operator content role for one argument name."""
    name = str(argument).casefold()
    if name in _CODE_ARGUMENTS:
        return "code"
    if name in _PATH_ARGUMENTS:
        return "path"
    if name in _NATURAL_LANGUAGE_ARGUMENTS:
        return "natural_language"
    return None


def _neutral_description(method: str) -> str:
    operation = str(method).replace("-", " ").replace("_", " ").strip()
    return (operation[:1].upper() + operation[1:] +
            " through the operator-registered MCP method.")


def _observation_only(method: str) -> bool:
    """Conservative direction attestation from the registered operation name."""
    name = str(method).casefold()
    return name.startswith(_OBSERVATION_PREFIXES) or name in {
        "gettime", "get-time", "current_time", "time", "now",
    }


def _merge_schema(left: dict, right: dict) -> dict:
    """Merge runtime-attested schema variants without inventing arguments."""
    if not left:
        return json.loads(json.dumps(right))
    result = json.loads(json.dumps(left))
    properties = result.setdefault("properties", {})
    for name, schema in (right.get("properties") or {}).items():
        if name in properties and properties[name].get("type") != schema.get("type"):
            raise ValueError(f"conflicting runtime types for argument {name!r}")
        properties.setdefault(name, schema)
    result["required"] = sorted(
        set(result.get("required") or ()) & set(right.get("required") or ()))
    result["additionalProperties"] = False
    return result


def _reconcile_documented_parameters(schema: dict, description: str):
    """Recover parameters collapsed by a known lossy MCP wrapper.

    Some clean MCPTox interfaces expose a single optional ``request_data``
    string even though their operator-authored description contains a literal
    list of exact path/query parameters.  Reconciliation is deliberately
    narrow: it only replaces that placeholder shape, only reads the clean
    catalog, and only accepts declarative Python-literal metadata.  Free-form
    prose and poisoned descriptions never enter this path.
    """
    properties = dict(schema.get("properties") or {})
    if set(properties) != {"request_data"}:
        return schema, False
    description = str(description or "")
    reconciled, required, recovered = {}, [], False

    # The installed wrapper exposes one ``request_data`` object while the
    # clean operator description declares its exact child schema.  Parse only
    # the balanced Python literal immediately following the fixed declaration;
    # free prose and attack catalogs never reach this builder path.
    prefix = _REQUEST_DATA_PREFIX.search(description)
    if prefix is not None:
        start = prefix.end()
        try:
            value = ast.literal_eval(description[start:])
        except (SyntaxError, ValueError):
            # ``literal_eval`` rejects the trailing prose. Find the shortest
            # balanced dictionary prefix and evaluate only that declaration.
            depth = 0
            end = None
            quote = None
            escaped = False
            for index, char in enumerate(description[start:], start=start):
                if quote is not None:
                    if escaped:
                        escaped = False
                    elif char == "\\":
                        escaped = True
                    elif char == quote:
                        quote = None
                    continue
                if char in {"'", '"'}:
                    quote = char
                elif char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        end = index + 1
                        break
            try:
                value = ast.literal_eval(description[start:end]) if end else None
            except (SyntaxError, ValueError):
                value = None
        if isinstance(value, dict) and value and all(
                isinstance(name, str) and isinstance(item, dict) and
                str(item.get("type", "")).casefold() in _JSON_TYPES
                for name, item in value.items()):
            children = {}
            for name, item in value.items():
                child = json.loads(json.dumps(item))
                child["type"] = str(child["type"]).casefold()
                child["x-operator-source"] = (
                    "clean-description-request-data-declaration")
                children[name] = child
            reconciled["request_data"] = {
                "type": "object", "properties": children,
                "additionalProperties": False,
                "x-operator-source": (
                    "clean-description-request-data-declaration"),
            }
            recovered = True

    match = _DOCUMENTED_PARAMETERS.search(description)
    rows = None
    if match is not None:
        try:
            rows = ast.literal_eval(match.group(1))
        except (SyntaxError, ValueError):
            rows = None
    if isinstance(rows, list) and rows:
        for row in rows:
            if not isinstance(row, dict) or not isinstance(row.get("name"), str):
                return schema, False
            name = row["name"].strip()
            kind = str(row.get("type", "string")).casefold()
            if not name or name in reconciled or kind not in _JSON_TYPES:
                return schema, False
            item = {"type": kind,
                    "x-operator-source": "clean-description-parameter-declaration"}
            if isinstance(row.get("description"), str):
                item["description"] = row["description"]
            reconciled[name] = item
            if row.get("required") is True:
                required.append(name)
        recovered = True
    if not recovered:
        return schema, False
    return {
        "type": "object",
        "properties": reconciled,
        "required": required,
        "additionalProperties": False,
    }, True


def _sha(value) -> str:
    body = json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), default=str)
    return hashlib.sha256(body.encode()).hexdigest()


def _provenance_path(path: Path) -> str:
    """Keep checked-in provenance portable while preserving external paths."""
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPOSITORY).as_posix()
    except ValueError:
        return str(resolved)


def _operator_schemas(path: Path) -> dict[str, dict]:
    registry = json.loads(path.read_text(encoding="utf-8"))
    if registry.get("schema") != "mcptox-operator-schema-registry-v1":
        raise ValueError("unknown MCPTox operator schema registry")
    capabilities = registry.get("capabilities")
    if not isinstance(capabilities, dict):
        raise TypeError("MCPTox operator schema registry has no capabilities")
    for capability, overlay in capabilities.items():
        properties = overlay.get("properties") if isinstance(overlay, dict) else None
        if not isinstance(properties, dict) or any(
                not isinstance(value, dict) or not value.get("type")
                for value in properties.values()):
            raise ValueError(
                f"operator schema {capability!r} has incomplete properties")
        for field in ("effect", "observation"):
            if field in overlay and not isinstance(overlay[field], bool):
                raise ValueError(
                    f"operator schema {capability!r} has non-boolean {field}")
        if ("argument_types" in overlay and
                not isinstance(overlay["argument_types"], dict)):
            raise ValueError(
                f"operator schema {capability!r} has invalid argument_types")
    return capabilities


def _apply_operator_schema(capability: str, schema: dict,
                           registry: dict[str, dict]) -> tuple[dict, int]:
    """Overlay task-independent operator types on the lossy rendered shape."""
    overlay = registry.get(capability)
    if overlay is None:
        return schema, 0
    result = json.loads(json.dumps(schema))
    properties = result.get("properties") or {}
    changed = 0
    for argument, trusted in overlay["properties"].items():
        if argument not in properties:
            raise ValueError(
                f"operator schema {capability!r} declares unknown argument "
                f"{argument!r}")
        rendered_description = properties[argument].get("description")
        replacement = json.loads(json.dumps(trusted))
        # A managed-registry type overlay is authoritative for the outer JSON
        # kind, but a type-only ``object`` must not erase exact child fields
        # recovered from the operator's clean request-data declaration.
        rendered = properties[argument]
        if (replacement.get("type") == "object" and
                rendered.get("type") == "object" and
                "properties" not in replacement and
                isinstance(rendered.get("properties"), dict)):
            replacement["properties"] = json.loads(json.dumps(
                rendered["properties"]))
            replacement["additionalProperties"] = bool(
                rendered.get("additionalProperties", False))
        properties[argument] = replacement
        properties[argument]["x-operator-source"] = "managed-mcp-registry"
        if rendered_description and "description" not in properties[argument]:
            properties[argument]["description"] = rendered_description
        changed += 1
    result["properties"] = properties
    result["additionalProperties"] = False
    return result, changed


def build(path: Path, operator_schemas: Path = DEFAULT_OPERATOR_SCHEMAS
          ) -> tuple[dict, dict]:
    benchmark = json.loads(path.read_text(encoding="utf-8"))
    registry = _operator_schemas(operator_schemas)
    servers = benchmark.get("servers") or {}
    capabilities = {}
    entries = []
    for server_name, server in sorted(servers.items()):
        clean_prompt = server.get("clean_system_promot")
        if not isinstance(clean_prompt, str) or not clean_prompt.strip():
            raise ValueError(f"MCPTox server {server_name!r} has no clean catalog")
        tools = _blocks(clean_prompt)
        if not tools:
            raise ValueError(f"MCPTox server {server_name!r} exposes no tools")
        runtime_tools = dict(tools)
        runtime_sources = {name: "benchmark-clean-interface" for name in tools}
        for malicious in server.get("malicious_instance", ()):
            for row in malicious.get("datas", ()):
                for name, tool in _blocks(str(row.get("system", ""))).items():
                    if name in runtime_tools:
                        tool = {**runtime_tools[name], "inputSchema": _merge_schema(
                            runtime_tools[name]["inputSchema"], tool["inputSchema"])}
                    else:
                        tool = {**tool, "description": _neutral_description(name)}
                        runtime_sources[name] = "operator-runtime-name+schema"
                    runtime_tools[name] = tool
        for tool_name, tool in sorted(runtime_tools.items()):
            capability = _canonical(server_name, tool_name)
            if capability in capabilities:
                raise ValueError(f"duplicate MCPTox capability {capability!r}")
            schema = tool["inputSchema"]
            schema_reconciled = False
            if runtime_sources[tool_name] == "benchmark-clean-interface":
                schema, schema_reconciled = _reconcile_documented_parameters(
                    schema, tool["description"])
            schema, operator_fields = _apply_operator_schema(
                capability, schema, registry)
            properties = schema.get("properties") or {}
            operator = registry.get(capability, {})
            argument_types = {
                name: kind for name in properties
                if (kind := _argument_type(name)) is not None}
            argument_types.update({
                str(name): str(kind)
                for name, kind in operator.get("argument_types", {}).items()
                if str(name) in properties})
            observation_only = _observation_only(tool_name)
            effect = bool(operator.get("effect", not observation_only))
            observation = bool(operator.get("observation", True))
            if not effect and not observation:
                raise ValueError(
                    f"operator schema {capability!r} disables both boundaries")
            surface = CapabilitySurface.from_dict({
                "name": capability,
                "description": tool["description"],
                "inputSchema": schema,
                "required_arguments": list(schema.get("required") or ()),
                "argument_schemas": properties,
                "argument_types": argument_types,
                "output_schema": {"type": "string"},
                "effect": effect,
                "observation": observation,
                "effect_return": effect and observation,
            })
            capabilities[capability] = surface
            entries.append({
                "capability": capability,
                "server": server_name,
                "method": tool_name,
                "schema_source": runtime_sources[tool_name],
                "schema_reconciliation": (
                    "clean-description-parameter-declaration"
                    if schema_reconciled else None),
                "operator_schema_fields": operator_fields,
                "boundary_attestation": (
                    "observation-return" if not effect else
                    "mcp-invocation+text-return"),
            })
    unknown_capabilities = set(registry).difference(capabilities)
    if unknown_capabilities:
        raise ValueError(
            "operator registry contains absent capabilities: " +
            ", ".join(sorted(unknown_capabilities)))
    source_hash = _sha({
        "servers": servers,
        "operator_schema_registry": registry,
    })
    plan = EnvironmentPlan(
        "mcptox-clean-" + source_hash[:12], {}, capabilities).to_dict()
    provenance = {
        "benchmark": "MCPTox",
        "source": _provenance_path(path),
        "source_sha256": _sha(servers),
        "operator_schema_registry": _provenance_path(operator_schemas),
        "operator_schema_sha256": _sha(registry),
        "counts": {
            "benchmark-clean-interface": sum(
                row["schema_source"] == "benchmark-clean-interface"
                for row in entries),
            "operator-runtime-name+schema": sum(
                row["schema_source"] == "operator-runtime-name+schema"
                for row in entries),
            "operator-clean-parameter-reconciliation": sum(
                row["schema_reconciliation"] is not None for row in entries),
            "operator-schema-capabilities": len(registry),
            "operator-schema-fields": sum(
                row["operator_schema_fields"] for row in entries),
            "fallback": 0,
        },
        "entries": entries,
    }
    return plan, provenance


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--provenance", type=Path, required=True)
    parser.add_argument("--operator-schemas", type=Path,
                        default=DEFAULT_OPERATOR_SCHEMAS)
    args = parser.parse_args()
    plan, provenance = build(
        args.benchmark.resolve(), args.operator_schemas.resolve())
    for path, value in ((args.output, plan), (args.provenance, provenance)):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n",
                        encoding="utf-8")
    print(json.dumps({
        "capabilities": len(plan["capabilities"]),
        "fallback": provenance["counts"]["fallback"],
        "output": str(args.output),
    }))


if __name__ == "__main__":
    main()
