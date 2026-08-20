"""Thin AgentDojo substrate for the lean deterministic runtime.

Reads are bound to Acquire roles and expose a PLANT-decoyed view; effects are
gated by WRAP.  An optional trusted approver can release one exact proposal;
the defense never simulates that user or silently approves on its own.
"""
from __future__ import annotations

import json
import re

from code.ours.defense.engine import Engine
from code.ours.defense.broker import UnitBroker
from code.ours.defense.continuation import (ReplanRequired,
                                       render_recovery_task,
                                       replan_state_from_exception)
from code.core.manifest import validate_registrations
from code.ours.manifests.agentdojo import (
    COMMIT_ENTRIES, MEDIATED_OBSERVATIONS, NATURAL_LANGUAGE_ARGUMENTS,
    OUTPUT_TYPES)


def tool_schemas(suite, boundary_mode: str = "declared") -> list[dict]:
    suite_name = str(getattr(suite, "name", ""))
    declared = COMMIT_ENTRIES.get(suite_name)
    mediated_observations = MEDIATED_OBSERVATIONS.get(
        suite_name, frozenset())
    natural_language_arguments = NATURAL_LANGUAGE_ARGUMENTS.get(suite_name, {})
    output_types = OUTPUT_TYPES.get(suite_name, {})
    if boundary_mode != "declared":
        raise ValueError("only operator-declared capability manifests are accepted")
    if declared is None:
        raise ValueError("no declared capability manifest for this suite")
    out = []
    for tool in suite.tools:
        fields = getattr(getattr(tool, "parameters", None), "model_fields", {}) or {}
        item = {"name": str(tool.name), "description": str(getattr(tool, "description", "")),
                "arguments": list(fields),
                "argument_types": {
                    name: "natural_language"
                    for name in natural_language_arguments.get(str(tool.name), ())
                },
                "output_types": dict(output_types.get(str(tool.name), {})),
                "required_arguments": [
                    str(name) for name, field in fields.items() if field.is_required()
                ]}
        item["effect"] = str(tool.name) in declared
        item["observation"] = (str(tool.name) not in declared or
                               str(tool.name) in mediated_observations)
        out.append(item)
    return out


def tool_registrations(suite, boundary_mode: str = "declared") -> list[dict]:
    """Return trusted full interfaces for one-time environment perception."""
    compact = {item["name"]: item for item in tool_schemas(suite, boundary_mode)}
    out = []
    for tool in suite.tools:
        parameters = getattr(tool, "parameters", None)
        build_schema = getattr(parameters, "model_json_schema", None)
        schema = (build_schema() if callable(build_schema)
                  else {"type": "object", "properties": {}})
        for argument_schema in (schema.get("properties") or {}).values():
            description = str(argument_schema.get("description", "")).lower()
            if (isinstance(argument_schema, dict) and
                    argument_schema.get("type") == "string" and
                    "url" in description):
                argument_schema["format"] = "uri"
                argument_schema["x-canonicalization"] = "url-default-https"
                argument_schema["x-authority-scope"] = "same-origin"
            if (isinstance(argument_schema, dict) and
                    argument_schema.get("type") == "string" and
                    "yyyy-mm-dd hh:mm" in description):
                argument_schema["format"] = "date-time"
                argument_schema["x-completion"] = "date-to-local-datetime"
        try:
            from pydantic import TypeAdapter
            output_schema = TypeAdapter(getattr(tool, "return_type", None)).json_schema()
        except Exception:
            output_schema = None
        item = compact[str(tool.name)]
        if item.get("observation", False) and isinstance(output_schema, dict) and output_schema.get("type") == "null":
            output_schema = None
        produces_return = bool(item.get("observation", False) or
                               (isinstance(output_schema, dict) and
                                output_schema.get("type") != "null"))
        out.append({"name": str(tool.name),
                    "description": str(getattr(tool, "description", "")),
                    "inputSchema": schema,
                    # Preserve an explicitly empty required set.  Pydantic
                    # omits ``required`` when every position is optional;
                    # without this field CapabilitySurface must conservatively
                    # treat every argument as required.
                    "required_arguments": list(item["required_arguments"]),
                    "outputSchema": output_schema,
                    "argument_types": item.get("argument_types", {}),
                    "output_types": item.get("output_types", {}),
                    "receipt_role": "data",
                    **({"effect": item["effect"]} if "effect" in item else {}),
                    **({"observation": bool(item["observation"] or produces_return)}
                       if "observation" in item else {}),
                    "effect_return": bool(item.get("effect", False) and
                                          item.get("observation", False) and
                                          produces_return)})
    return out


def _json_shape(value):
    """Preserve operator field types while converting models to JSON nodes."""
    if isinstance(value, dict):
        return {str(key): _json_shape(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_shape(item) for item in value]
    dump = getattr(value, "model_dump", None)
    return _json_shape(dump(mode="json")) if callable(dump) else value


def _result_value(text):
    """Convert one operator return into an immutable JSON-shaped Receipt.

    A string returned as the complete tool response may be a JSON transport
    envelope. Strings inside an already structured return are schema values
    and must not be reparsed (for example, the string identifier ``"24"``).
    """
    if not isinstance(text, str):
        return _json_shape(text)
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text or "", re.S)
    candidate = fenced.group(1) if fenced else text
    try:
        value = json.loads(candidate)
    except (TypeError, json.JSONDecodeError):
        match = re.search(r"\{.*\}", candidate or "", re.S)
        if not match:
            return text
        try:
            value = json.loads(match.group(0))
        except json.JSONDecodeError:
            return text
    value = (value["result"] if isinstance(value, dict) and
             set(value) == {"result"} else value)
    return _json_shape(value)


def _tool_view(value):
    """Return a formatter-safe view without changing the canonical Receipt."""
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return value


def _safe_task_check(suite, task, output, before, after, trace) -> bool:
    """An incomplete simulated state is a failed check, never a runner crash."""
    if task is None:
        return False
    try:
        return bool(suite._check_task_result(task, output, before, after, trace))
    except (KeyError, IndexError, TypeError, ValueError, AttributeError):
        return False


class AgentDojoRunner:
    """Drive one AgentDojo task through the lean deterministic defense."""

    def __init__(self, suite, pipeline, engine: Engine, approver=None):
        self.suite, self.pipeline, self.engine = suite, pipeline, engine
        self.approver = approver
        if engine.plan is None:
            registrations = tool_registrations(suite)
            validate_registrations(
                registrations, f"AgentDojo/{getattr(suite, 'name', '')}")
            engine.perceive(registrations)

    def run(self, user_task, *, injection_task=None, injections=None,
            contract=None):
        from agentdojo.functions_runtime import FunctionCall, FunctionsRuntime
        from agentdojo.task_suite.task_suite import model_output_from_messages

        environment = self.suite.load_and_inject_default_environment(injections or {})
        external_contract = contract is not None
        if contract is None:
            contract = self.engine.contract(user_task.PROMPT)
        contract_trace = (
            {"source": "external_contract"}
            if external_contract else self.engine.contract_trace(user_task.PROMPT)
        )
        task_environment = user_task.init_environment(environment)
        before = task_environment.model_copy(deep=True)
        episode = self.engine.start(contract)
        plan = self.engine.plan
        effect_names = {name for name, surface in plan.capabilities.items()
                        if surface.effect}
        observation_names = {name for name, surface in plan.capabilities.items()
                             if surface.observation}
        broker = UnitBroker(episode, [{
            "name": name, "effect": surface.effect,
            "observation": surface.observation,
        } for name, surface in plan.capabilities.items()])
        approver = self.approver
        decisions: list[dict] = []
        trace: list = []

        class GuardedRuntime(FunctionsRuntime):
            def run_function(self, env, function, args, *extra, **kwargs):
                name, arguments = str(function), dict(args or {})
                prepared = broker.prepare(name, arguments)
                arguments = dict(prepared.invocation.arguments)
                if name in effect_names:
                    decision = prepared.decision
                    decisions.append({"effect": name, "arguments": arguments,
                                      "route": decision.route,
                                      "reason": decision.reason,
                                      "refs": list(decision.refs),
                                      "commitments": list(decision.commitments),
                                      "approval_id": decision.approval_id})
                    if decision.route == "approval" and approver is not None:
                        approved = bool(approver(dict(decision.approval)))
                        episode.decide_approval(decision.approval_id, approved)
                        prepared = broker.prepare(name, arguments)
                        decision = prepared.decision
                        decisions.append({
                            "effect": name, "arguments": arguments,
                            "route": decision.route,
                            "reason": decision.reason,
                            "refs": list(decision.refs),
                            "commitments": list(decision.commitments),
                            "approval_id": decision.approval_id,
                        })
                    if decision.continuation_id:
                        decision = episode.continue_decision(decision)
                        if decision.authorized_arguments:
                            arguments = broker.canonical_arguments(
                                name, decision.authorized_arguments)
                        decisions.append({
                            "effect": name, "arguments": arguments,
                            "route": decision.route,
                            "reason": decision.reason,
                            "refs": list(decision.refs),
                            "commitments": list(decision.commitments),
                            "continuation": dict(decision.continuation),
                        })
                    broker.record_decision(prepared, decision, arguments)
                    if decision.route != "pass":
                        if decision.route == "replan":
                            raise ReplanRequired(decision.continuation["state"])
                        verb = ("Awaiting user approval" if
                                decision.route == "approval" else
                                "Blocked by the active defense")
                        return ("%s (%s): this action was not authorized."
                                % (verb, decision.reason)), None
                    with broker.execution(prepared):
                        result = super().run_function(
                            env, function, arguments, *extra, **kwargs)
                    output, error = (result if isinstance(result, tuple) and
                                     len(result) == 2 else (result, None))
                    if error is None:
                        if decision.approval_id:
                            episode.approval_succeeded(decision.approval_id)
                        broker.succeeded(prepared, arguments)
                        trace.append(FunctionCall(function=name, args=arguments))
                        if name in observation_names:
                            output = _tool_view(episode.observe(
                                name, arguments, _result_value(output)))
                    return output, error
                with broker.execution(prepared):
                    result = super().run_function(
                        env, function, arguments, *extra, **kwargs)
                output, error = (result if isinstance(result, tuple) and
                                 len(result) == 2 else (result, None))
                if error is None:
                    broker.succeeded(prepared, arguments)
                    trace.append(FunctionCall(function=name, args=arguments))
                    if name in observation_names:
                        output = _tool_view(episode.observe(
                            name, arguments, _result_value(output)))
                return output, error

        runtime = GuardedRuntime(self.suite.tools)
        continuation_state = None
        output, response_decision = "", None
        attempts = 1 + (episode.continuation.max_total_replans
                        if episode.continuation is not None else 0)
        for attempt in range(attempts):
            prompt = user_task.PROMPT
            if continuation_state is not None:
                prompt = render_recovery_task(prompt, continuation_state)
            try:
                _, runtime, task_environment, turn_messages, _ = self.pipeline.query(
                    prompt, runtime, task_environment, messages=[])
            except Exception as error:
                continuation_state = replan_state_from_exception(error)
                if continuation_state is None:
                    raise
                if attempt + 1 < attempts:
                    continue
                break
            output = model_output_from_messages(turn_messages) or ""
            response_decision = episode.response(output)
            if response_decision.continuation_id:
                response_decision = episode.continue_decision(response_decision)
            if (response_decision.route == "replan" and
                    attempt + 1 < attempts):
                continuation_state = response_decision.continuation["state"]
                continue
            break
        if response_decision is None:
            response_decision = episode.response(output)
        if response_decision.route != "pass":
            decisions.append({
                "effect": "$response", "arguments": {},
                "route": response_decision.route,
                "reason": response_decision.reason,
                "refs": list(response_decision.refs),
                "commitments": list(response_decision.commitments),
                "continuation": dict(response_decision.continuation),
            })
            output = [{
                "type": "text",
                "content": "Response blocked by the active defense.",
            }]
        utility = _safe_task_check(
            self.suite, user_task, output, before, task_environment, trace)
        asr = _safe_task_check(
            self.suite, injection_task, output, before, task_environment, trace)
        audit = episode.close()
        return {"utility": bool(utility), "asr": bool(asr), "output": output,
                "decisions": decisions, "contract": contract.to_dict(),
                "contract_trace": contract_trace,
                "unit_broker": broker.invocation_receipts(), "audit": audit}
