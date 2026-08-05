"""Deterministic clause-output resolution from bound receipts.

Acquire outputs are copied from their receipt; Conditional outputs are computed
by replaying the closed operator over already-resolved operands.  Both are pure
functions of runtime state and need no model — this is the fast common path.

Derive is the only genuinely semantic role.  A Derive is resolved by one
validated binding-agent call: the agent proposes which receipt refs the value
derives from, deterministic code checks those refs exist and that the value
introduces no entity absent from them, and binds it.  A Derive that cannot be
grounded is left UNRESOLVED — never guessed, no fallback.
"""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from datetime import datetime, timedelta
import re

from code.defense.contract import ConditionalClause, DeriveClause
from code.defense.state import (Binding, CONTEXT_REF, QUERY_REF, SEMANTIC_REF,
                                RuntimeState, UNRESOLVED)

_TRUSTED_INPUT_REFS = {"task": QUERY_REF, "runtime-context": CONTEXT_REF}


def operator_operand_type(operator: str, index: int) -> str:
    """Return the closed operator's structural requirement for one operand.

    This is part of the operator algebra, not a benchmark policy.  ``any``
    means the operator imposes no useful precondition at that position.
    """
    if operator == "add":
        return "number"
    if operator in {"gt", "lt"}:
        return "number" if index in {1, 2} else "any"
    if operator in {"argmax", "argmin"}:
        return "number-list" if index == 1 else "collection"
    if operator == "count":
        return "collection"
    if operator == "map_count":
        return "collection-list"
    if operator == "union":
        return "collection-list"
    if operator == "difference":
        return "collection"
    if operator == "field":
        return "string" if index == 1 else "object"
    if operator == "select_eq":
        return ("collection" if index == 0 else
                "string" if index == 1 else "any")
    if operator == "interval_free":
        return "collection" if index == 0 else "datetime"
    if operator in {"datetime_combine", "add_duration", "basename",
                    "path_join"}:
        return "string"
    if operator == "aligned_lookup":
        return "collection" if index in {0, 1} else "any"
    return "any"


def _is_number(value) -> bool:
    if isinstance(value, bool) or isinstance(value, (dict, list, tuple)):
        return False
    try:
        Decimal(str(value))
    except (InvalidOperation, ValueError):
        return False
    return True


def operator_value_matches(kind: str, value) -> bool:
    """Validate a materialized value against an operator operand type."""
    if kind == "any":
        return True
    if kind == "number":
        return _is_number(value)
    if kind == "number-list":
        return (isinstance(value, (list, tuple)) and bool(value) and
                all(_is_number(item) for item in value))
    if kind == "collection":
        return isinstance(value, (list, tuple, dict))
    if kind == "collection-list":
        return (isinstance(value, (list, tuple)) and
                all(isinstance(item, (list, tuple, dict)) for item in value))
    if kind == "object":
        return isinstance(value, dict)
    if kind == "string":
        return isinstance(value, str)
    if kind == "datetime":
        if not isinstance(value, str):
            return False
        try:
            datetime.fromisoformat(value.replace(" ", "T"))
        except ValueError:
            return False
        return True
    raise ValueError(f"unknown operator operand type: {kind}")


def _exact_task_span(task: str, value) -> bool:
    """Return true only for a complete scalar token literally present in task."""
    if not isinstance(value, str) or not value:
        return False
    return re.search(
        r"(?<![\w])" + re.escape(value) + r"(?![\w])", str(task)) is not None


def _operand_refs(state: RuntimeState, refs) -> tuple[str, ...]:
    out: list[str] = []
    for ref in refs:
        binding = state.bindings.get(str(ref).partition(".")[0])
        if binding is not None:
            out.extend(binding.refs)
    return tuple(dict.fromkeys(out))


def replay_operator(operator: str, operands: list):
    """Replay one closed Conditional operator; raise on an unknown operator."""
    if operator == "identity":
        return operands[0]
    if operator == "singleton":
        return [operands[0]]
    if operator == "count":
        return len(operands[0])
    if operator == "map_count":
        groups = operands[0]
        if not isinstance(groups, (list, tuple)):
            raise ValueError("map_count needs a collection of collections")
        if any(not isinstance(group, (list, tuple, dict))
               for group in groups):
            raise ValueError("map_count items must be collections")
        return [len(group) for group in groups]
    if operator == "union":
        groups = operands[0]
        if not isinstance(groups, (list, tuple)) or any(
                not isinstance(group, (list, tuple)) for group in groups):
            raise ValueError("union needs a collection of collections")
        merged: list = []
        for group in groups:
            for item in group:
                if item not in merged:
                    merged.append(item)
        return merged
    if operator == "difference":
        removed = operands[1]
        return [item for item in operands[0] if item not in removed]
    if operator == "field":
        value, field = operands
        if not isinstance(field, str):
            raise ValueError("field name must be a string")
        if isinstance(value, dict) and field in value:
            return value[field]
        if hasattr(value, field):
            return getattr(value, field)
        raise ValueError("field is absent")
    if operator == "select_eq":
        items, field, expected = operands
        if not isinstance(items, (list, tuple)) or not isinstance(field, str):
            raise ValueError("select_eq needs a collection and field")

        def equal(left, right):
            if isinstance(left, str) and isinstance(right, str):
                return left.casefold() == right.casefold()
            return type(left) is type(right) and left == right

        matches = []
        for item in items:
            actual = (item.get(field, UNRESOLVED)
                      if isinstance(item, dict)
                      else getattr(item, field, UNRESOLVED))
            if actual is not UNRESOLVED and equal(actual, expected):
                matches.append(item)
        if len(matches) != 1:
            raise ValueError("select_eq requires one unique match")
        return matches[0]
    if operator == "add":
        if any(isinstance(value, bool) for value in operands):
            raise ValueError("add operands must be numeric")
        try:
            total = sum(Decimal(str(value)) for value in operands)
        except (InvalidOperation, ValueError):
            raise ValueError("add operands must be numeric")
        return int(total) if total == total.to_integral() else float(total)
    if operator == "datetime_combine":
        date, time = map(str, operands)
        return datetime.fromisoformat(date + "T" + time).strftime(
            "%Y-%m-%d %H:%M")
    if operator == "add_duration":
        start, duration = operands
        match = re.fullmatch(
            r"\s*(\d+(?:\.\d+)?)?\s*(minute|minutes|hour|hours)\s*",
            str(duration), re.I)
        if not match:
            words = {"one": 1, "two": 2, "three": 3, "four": 4}
            match = re.fullmatch(
                r"\s*(one|two|three|four)\s*(minute|minutes|hour|hours)\s*",
                str(duration), re.I)
            if not match:
                raise ValueError("unsupported duration")
            amount = Decimal(words[match.group(1).casefold()])
        else:
            amount = Decimal(match.group(1) or "1")
        unit = match.group(2).casefold()
        minutes = float(amount * (60 if unit.startswith("hour") else 1))
        value = datetime.fromisoformat(str(start).replace(" ", "T"))
        return (value + timedelta(minutes=minutes)).strftime("%Y-%m-%d %H:%M")
    if operator == "interval_free":
        events, start, end = operands
        if not isinstance(events, (list, tuple)):
            raise ValueError("interval_free events must be a collection")
        lower = datetime.fromisoformat(str(start).replace(" ", "T"))
        upper = datetime.fromisoformat(str(end).replace(" ", "T"))
        if lower >= upper:
            raise ValueError("interval_free requires a positive interval")
        for event in events:
            if not isinstance(event, dict):
                raise ValueError("interval_free event must be an object")
            event_start = datetime.fromisoformat(
                str(event["start_time"]).replace(" ", "T"))
            event_end = datetime.fromisoformat(
                str(event["end_time"]).replace(" ", "T"))
            if lower < event_end and event_start < upper:
                return UNRESOLVED
        return start
    if operator in ("gt", "lt"):
        candidate, score, threshold = operands
        if isinstance(score, bool) or isinstance(threshold, bool):
            raise ValueError("gt/lt operands must be numeric")
        try:
            left, right = Decimal(str(score)), Decimal(str(threshold))
        except (InvalidOperation, ValueError):
            raise ValueError("gt/lt operands must be numeric")
        passed = left > right if operator == "gt" else left < right
        return candidate if passed else UNRESOLVED
    if operator in ("argmax", "argmin"):
        items, scores = operands[0], operands[1]
        if len(items) != len(scores) or not items:
            raise ValueError("argmax/argmin need aligned non-empty operands")
        pick = max if operator == "argmax" else min
        index = pick(range(len(scores)), key=lambda i: scores[i])
        return items[index]
    if operator == "aligned_lookup":
        keys, values, selected = operands
        if (not isinstance(keys, (list, tuple)) or
                not isinstance(values, (list, tuple)) or
                len(keys) != len(values)):
            raise ValueError("aligned_lookup needs aligned collections")
        matches = [index for index, key in enumerate(keys)
                   if key == selected and type(key) is type(selected)]
        if len(matches) != 1:
            raise ValueError("aligned_lookup requires one unique key")
        return values[matches[0]]
    if operator == "basename":
        return str(operands[0]).rstrip("/").rsplit("/", 1)[-1]
    if operator == "path_join":
        return str(operands[0]).rstrip("/") + "/" + str(operands[1])
    raise ValueError(f"unknown Conditional operator: {operator}")


def resolve_conditional(state: RuntimeState,
                        clause: ConditionalClause) -> Binding | None:
    operands = [
        item["literal"] if isinstance(item, dict) else state.output(item)
        for item in clause.operands]
    if any(operand is UNRESOLVED for operand in operands):
        return None
    try:
        value = replay_operator(clause.operator, operands)
    except (TypeError, ValueError):
        # A closed proof that cannot be replayed is simply unresolved.  Invalid
        # runtime operands must fail closed at WRAP, not abort the whole task.
        return None
    if value is UNRESOLVED:
        return None
    return state.bind(Binding(clause.id, "conditional", value,
                              _operand_refs(state, clause.operand_refs)))


def resolve_derive(state: RuntimeState, clause: DeriveClause, value, *,
                   task: str = "", ground=None) -> Binding | None:
    """Resolve one semantic Derive output through the single validated agent.

    Inputs are the clause's declared sources: earlier clause outputs (backed by
    their receipt refs) and the trusted origins ``task``/``runtime-context``.
    ``ground`` is ``(task, instruction, inputs, value) -> bool`` — the agent
    judges only whether ``value`` is a faithful, task-authorized instantiation
    of the role over these inputs; deterministic code owns the provenance refs
    (always the inputs' own refs, never anything the agent supplies).  A false
    judgment, a missing agent, or an unresolved input binds nothing.
    """
    inputs: dict = {}
    refs: list[str] = []
    for ref in clause.input_refs:
        if ref in _TRUSTED_INPUT_REFS:
            inputs[ref] = ref
            refs.append(_TRUSTED_INPUT_REFS[ref])
            continue
        resolved = state.output(ref)
        if resolved is UNRESOLVED:
            return None
        inputs[ref] = resolved
        binding = state.bindings.get(str(ref).partition(".")[0])
        if binding is not None:
            refs.extend(binding.refs)
    # A task-sourced exact text span is already a deterministic authority
    # witness.  Do not ask the semantic agent to rediscover or reject it.
    if "task" in clause.input_refs and _exact_task_span(task, value):
        return state.bind(Binding(clause.id, "derive", value,
                                  tuple(dict.fromkeys(refs))))
    if ground is None:
        return None
    judgment = ground(
        task=task, instruction=clause.instruction, inputs=inputs, value=value)
    grounded = (judgment.get("grounded") is True
                if isinstance(judgment, dict) else judgment is True)
    if not grounded:
        return None
    semantic_refs = (SEMANTIC_REF, *(ref for ref in refs
                                     if ref not in {QUERY_REF, CONTEXT_REF}))
    return state.bind(Binding(clause.id, "derive", value,
                              tuple(dict.fromkeys(semantic_refs))))
