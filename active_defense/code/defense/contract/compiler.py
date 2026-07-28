"""Deterministic compiler for the explicit four-Clause TaskContract DSL."""
from __future__ import annotations

from .model import is_clause_ref


OPERATOR_ARITY = {
    "identity": 1, "singleton": 1, "count": 1, "union": 1,
    "difference": 2, "argmin": 2, "argmax": 2,
    "basename": 1, "path_join": 2,
}


def normalize_contract(data):
    """Canonicalize ids and unambiguous aliases without adding a Clause."""
    if not isinstance(data, dict) or not isinstance(data.get("clauses"), list):
        return data
    aliases = {}
    for index, raw in enumerate(data["clauses"]):
        output = raw.get("output") if isinstance(raw, dict) else None
        if isinstance(output, str) and output:
            aliases[f"c{index}"] = f"c{index}.{output}"
            aliases[f"c{index}.output"] = f"c{index}.{output}"

    def ref(value):
        return aliases.get(value, value) if isinstance(value, str) else value

    def spec(value):
        if not isinstance(value, dict) or set(value) != {"from"}:
            return value
        origins = value["from"]
        if isinstance(origins, str):
            return {"from": ref(origins)}
        if isinstance(origins, list):
            return {"from": [ref(item) for item in origins]}
        return value

    clauses = []
    for index, raw in enumerate(data["clauses"]):
        if not isinstance(raw, dict):
            clauses.append(raw)
            continue
        clause = {key: value for key, value in raw.items() if value is not None}
        clause["id"] = f"c{index}"
        if isinstance(clause.get("arguments"), dict):
            clause["arguments"] = {
                name: spec(value) for name, value in clause["arguments"].items()}
        if isinstance(clause.get("from"), list):
            clause["from"] = [ref(item) for item in clause["from"]]
        if isinstance(clause.get("operands"), list):
            clause["operands"] = [ref(item) for item in clause["operands"]]
        clauses.append(clause)
    normalized = {"task": data.get("task", ""), "clauses": clauses}
    if "delegations" in data:
        normalized["delegations"] = data.get("delegations")
    return normalized


def validate_contract(data, trusted_task, actions, environment_sources,
                      allowed_args, required_args=None,
                      effect_return_actions=None, observation_actions=None):
    if not isinstance(data, dict):
        return ["contract is not an object"]
    errors = []
    if set(data) not in ({"task", "clauses"},
                         {"task", "clauses", "delegations"}):
        errors.append("contract fields mismatch")
    if data.get("task") != trusted_task:
        errors.append("task mismatch")
    clauses = data.get("clauses")
    if not isinstance(clauses, list):
        return errors + ["clauses is not a list"]
    available = {"task"}
    if "runtime-context" in set(environment_sources):
        available.add("runtime-context")
    effect_return_actions = set(effect_return_actions or ())
    observation_actions = set(observation_actions or allowed_args)
    required_args = required_args or {}
    prior_effects = {}
    acquire_outputs = set()
    effect_ids = set()

    def output_valid(value):
        return isinstance(value, str) and bool(value) and "." not in value

    def references(spec, prefix):
        if not isinstance(spec, dict) or len(spec) != 1:
            errors.append(prefix + " argument must be exactly literal or from")
            return ()
        if set(spec) == {"literal"}:
            return ()
        if set(spec) != {"from"}:
            errors.append(prefix + " argument must be exactly literal or from")
            return ()
        raw = spec["from"]
        refs = (raw,) if isinstance(raw, str) else tuple(raw or ())
        if not refs or any(not isinstance(ref, str) or ref not in available or
                           ref == "task" for ref in refs):
            errors.append(prefix + " invalid from reference")
            return ()
        return refs

    common = {"id", "type", "instruction"}
    fields = {
        "acquire": common | {"capability", "arguments", "output"},
        "derive": common | {"from", "output"},
        "conditional": common | {"operator", "operands", "output"},
        "effect": common | {"action", "arguments"},
    }
    for index, raw in enumerate(clauses):
        prefix = f"clause[{index}]"
        if not isinstance(raw, dict):
            errors.append(prefix + " is not an object")
            continue
        kind = raw.get("type")
        if kind not in fields or set(raw) != fields.get(kind):
            errors.append(prefix + " fields mismatch")
            continue
        if raw.get("id") != f"c{index}":
            errors.append(prefix + " invalid id")
        if not isinstance(raw.get("instruction"), str) or not raw["instruction"].strip():
            errors.append(prefix + " invalid instruction")

        if kind == "derive":
            inputs = raw.get("from")
            if (not isinstance(inputs, list) or not inputs or
                    any(not isinstance(ref, str) or ref not in available
                        for ref in inputs)):
                errors.append(prefix + " invalid derive inputs")
            output = raw.get("output")
            if not output_valid(output):
                errors.append(prefix + " invalid output")
            else:
                available.add(f"c{index}.{output}")
            continue

        if kind == "conditional":
            operator, operands = raw.get("operator"), raw.get("operands")
            arity = OPERATOR_ARITY.get(operator)
            if (arity is None or not isinstance(operands, list) or
                    len(operands) != arity or
                    any(not isinstance(ref, str) or ref not in available or
                        not is_clause_ref(ref) for ref in operands) or
                    (operator in {"argmin", "argmax"} and
                     len(operands) == 2 and operands[0] == operands[1])):
                errors.append(prefix + " invalid conditional")
            output = raw.get("output")
            if not output_valid(output):
                errors.append(prefix + " invalid output")
            else:
                available.add(f"c{index}.{output}")
            continue

        arguments = raw.get("arguments")
        if not isinstance(arguments, dict):
            errors.append(prefix + " invalid arguments")
            continue
        name = raw.get("capability") if kind == "acquire" else raw.get("action")
        if kind == "acquire":
            if name not in observation_actions:
                errors.append(prefix + " unknown observation capability")
        elif name not in actions:
            errors.append(prefix + " unknown action")
        allowed = set(allowed_args.get(name, ()))
        if not set(arguments).issubset(allowed):
            errors.append(prefix + " arguments must be registered schema positions")
        missing = set(required_args.get(name, ())) - set(arguments)
        if missing:
            errors.append(prefix + " missing required arguments: " +
                          ",".join(sorted(missing)))
        role_uses = {}
        for argument, value in arguments.items():
            refs = references(value, prefix + "." + str(argument))
            if kind == "effect":
                for ref in refs:
                    if is_clause_ref(ref):
                        role_uses.setdefault(ref, []).append(str(argument))
        if kind == "effect":
            for ref, names in role_uses.items():
                if len(set(names)) > 1:
                    errors.append(prefix + " output " + ref +
                                  " binds multiple argument roles; split scalar outputs")

        if kind == "acquire":
            output = raw.get("output")
            if not output_valid(output):
                errors.append(prefix + " invalid output")
            else:
                available.add(f"c{index}.{output}")
                acquire_outputs.add(f"c{index}.{output}")
            if (name in effect_return_actions and
                    arguments not in prior_effects.get(name, ())):
                errors.append(prefix + " effect-return Acquire must be immediately preceded by an Effect Clause for the same capability with byte-for-byte identical arguments; insert the Effect, not another Acquire")
        elif name in actions:
            prior_effects.setdefault(name, []).append(arguments)
            effect_ids.add(f"c{index}")
    delegations = data.get("delegations", [])
    if not isinstance(delegations, list):
        errors.append("delegations is not a list")
    else:
        seen_delegations = set()
        for index, raw in enumerate(delegations):
            prefix = f"delegation[{index}]"
            if (not isinstance(raw, dict) or "from" not in raw or
                    not set(raw).issubset({"from", "to"}) or
                    not isinstance(raw.get("from"), str) or
                    ("to" in raw and not isinstance(raw.get("to"), str))):
                errors.append(prefix + " fields mismatch")
                continue
            edge = (raw["from"], raw.get("to", ""))
            if edge in seen_delegations:
                errors.append(prefix + " duplicate edge")
            seen_delegations.add(edge)
            if raw["from"] not in acquire_outputs:
                errors.append(prefix + " source must be an Acquire output")
            if raw.get("to") and raw["to"] not in effect_ids:
                errors.append(prefix + " target must be an existing Effect Clause")
    return errors


def task_contract_tool_schema():
    argument = {"oneOf": [
        {"type": "object", "properties": {"literal": {}},
         "required": ["literal"], "additionalProperties": False},
        {"type": "object", "properties": {"from": {"oneOf": [
            {"type": "string"}, {"type": "array", "items": {"type": "string"},
                                "minItems": 1}]}},
         "required": ["from"], "additionalProperties": False},
    ]}
    arguments = {"type": "object", "additionalProperties": argument}
    common = {"id": {"type": "string"}, "instruction": {"type": "string"}}

    def variant(kind, properties, required):
        return {"type": "object", "properties": {**common,
                "type": {"type": "string", "enum": [kind]}, **properties},
                "required": ["id", "type", "instruction", *required],
                "additionalProperties": False}

    clause = {"oneOf": [
        variant("acquire", {"capability": {"type": "string"},
                            "arguments": arguments, "output": {"type": "string"}},
                ["capability", "arguments", "output"]),
        variant("derive", {"from": {"type": "array",
                                     "items": {"type": "string"}, "minItems": 1},
                           "output": {"type": "string"}}, ["from", "output"]),
        variant("conditional", {"operator": {"type": "string",
                                               "enum": list(OPERATOR_ARITY)},
                                "operands": {"type": "array",
                                             "items": {"type": "string"},
                                             "minItems": 1, "maxItems": 2},
                                "output": {"type": "string"}},
                ["operator", "operands", "output"]),
        variant("effect", {"action": {"type": "string"},
                           "arguments": arguments}, ["action", "arguments"]),
    ]}
    return {"type": "function", "function": {
        "name": "emit_task_contract",
        "description": "Return one explicit validated TaskContract candidate.",
        "parameters": {"type": "object", "properties": {
            "task": {"type": "string"},
            "clauses": {"type": "array", "items": clause},
            "delegations": {"type": "array", "items": {
                "type": "object", "properties": {
                    "from": {"type": "string"}, "to": {"type": "string"}},
                "required": ["from"], "additionalProperties": False}}},
            "required": ["task", "clauses"], "additionalProperties": False}}}
