"""Single migration boundary for the pre-v2 implicit Clause format."""
from __future__ import annotations

import re

from .compiler import OPERATOR_ARITY
from .model import (AcquireClause, ConditionalClause, DeriveClause,
                    EffectClause, TaskContract, is_clause_ref)


def clause_from_legacy_fields(id="", instruction="", sources=None, output=None,
                              effect=None, arguments=None, relation=None):
    """Convert the historical positional Clause constructor to an explicit type."""
    sources = [str(item) for item in (sources or ())]
    arguments = dict(arguments or {})
    clause_id, instruction = str(id), str(instruction)
    if effect is not None:
        action = str(getattr(effect, "action", "") or
                     (effect.get("action", "") if isinstance(effect, dict) else ""))
        effect_arguments = dict(getattr(effect, "arguments", {}) or
                                (effect.get("arguments", {}) if isinstance(effect, dict) else {}))
        return EffectClause(clause_id, instruction, action, effect_arguments)
    if relation:
        match = re.fullmatch(r"([a-z]+)\(([^()]*)\)", str(relation).strip())
        parsed = None
        if match and match.group(1) in OPERATOR_ARITY:
            operands = tuple(item.strip() for item in match.group(2).split(",")
                             if item.strip())
            operator = match.group(1)
            if (len(operands) == OPERATOR_ARITY[operator] and
                    all(item in sources for item in operands) and
                    not (operator in {"argmin", "argmax"} and
                         operands[0] == operands[1])):
                parsed = (operator, operands)
        if parsed is not None:
            operator, operands = parsed
            return ConditionalClause(clause_id, instruction, operator,
                                     tuple(operands), str(output or ""))
    capability_candidates = [source for source in sources
                             if source not in {"task", "runtime-context"}
                             and not is_clause_ref(source)]
    if capability_candidates and (arguments or len(capability_candidates) == 1):
        return AcquireClause(clause_id, instruction, capability_candidates[0],
                             arguments, str(output or ""))
    return DeriveClause(clause_id, instruction, tuple(sources), str(output or ""))


def contract_from_legacy_dict(data: dict) -> TaskContract:
    clauses = []
    for index, raw in enumerate((data or {}).get("clauses") or []):
        if not isinstance(raw, dict):
            continue
        effect = raw.get("effect")
        clauses.append(clause_from_legacy_fields(
            f"c{index}", raw.get("instruction", ""), raw.get("sources") or (),
            raw.get("output"), effect, raw.get("arguments") or {},
            raw.get("relation")))
    return TaskContract(str((data or {}).get("task", "")), clauses)
