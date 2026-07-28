"""Clause-local WRAP gates with provenance separated from gate verdicts."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from ..contract import Clause, EffectClause


def _stable(value) -> str:
    return json.dumps(value, sort_keys=True, ensure_ascii=False, default=str,
                      separators=(",", ":"))


def _schema_field_catalog(schema):
    """Compile task-independent JSON-Schema field semantics for placement."""
    if not isinstance(schema, dict):
        return []
    rows, seen = [], set()

    def resolve(node):
        ref = node.get("$ref") if isinstance(node, dict) else None
        if not isinstance(ref, str) or not ref.startswith("#/"):
            return node
        target = schema
        for part in ref[2:].split("/"):
            if not isinstance(target, dict):
                return node
            target = target.get(part.replace("~1", "/").replace("~0", "~"))
        return target if isinstance(target, dict) else node

    def visit(node, path, stack):
        if not isinstance(node, dict):
            return
        node = resolve(node)
        identity = id(node)
        if identity in stack:
            return
        stack = stack | {identity}
        for branch in (node.get("anyOf") or node.get("oneOf") or ()):
            visit(branch, path, stack)
        properties = node.get("properties")
        if isinstance(properties, dict):
            for name, child in properties.items():
                visit(child, path + "/" + str(name), stack)
            return
        if isinstance(node.get("items"), dict):
            visit(node["items"], path + "/*", stack)
            return
        additional = node.get("additionalProperties")
        if isinstance(additional, dict):
            visit(additional, path + "/*", stack)
            return
        row = {"path": path or "#",
               **({"type": node["type"]} if isinstance(node.get("type"), str) else {}),
               **({"format": node["format"]} if isinstance(node.get("format"), str) else {}),
               **({"title": node["title"]} if isinstance(node.get("title"), str) else {}),
               **({"description": node["description"][:240]}
                  if isinstance(node.get("description"), str) else {})}
        key = _stable(row)
        if key not in seen:
            seen.add(key); rows.append(row)

    visit(schema, "", set())
    return rows


def _schema_accepts(value, schema, root=None) -> bool:
    """Validate the security-relevant, deterministic JSON Schema subset."""
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        value = dump(mode="json")
    if schema is None:
        return True
    if not isinstance(schema, dict):
        return False
    root = schema if root is None else root
    ref = schema.get("$ref")
    if isinstance(ref, str) and ref.startswith("#/"):
        target = root
        for part in ref[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                return False
            target = target[part]
        return _schema_accepts(value, target, root)
    if "const" in schema and value != schema["const"]:
        return False
    if "enum" in schema and value not in schema["enum"]:
        return False
    if "allOf" in schema and not all(
            _schema_accepts(value, item, root) for item in schema["allOf"]):
        return False
    if "anyOf" in schema and not any(
            _schema_accepts(value, item, root) for item in schema["anyOf"]):
        return False
    if "oneOf" in schema and sum(
            _schema_accepts(value, item, root) for item in schema["oneOf"]) != 1:
        return False
    kinds = schema.get("type")
    kinds = [kinds] if isinstance(kinds, str) else list(kinds or ())
    checks = {
        "null": lambda x: x is None,
        "boolean": lambda x: isinstance(x, bool),
        "integer": lambda x: isinstance(x, int) and not isinstance(x, bool),
        "number": lambda x: isinstance(x, (int, float)) and not isinstance(x, bool),
        "string": lambda x: isinstance(x, str),
        "array": lambda x: isinstance(x, (list, tuple)),
        "object": lambda x: isinstance(x, dict),
    }
    if kinds and not any(kind in checks and checks[kind](value) for kind in kinds):
        return False
    if isinstance(value, dict):
        properties = schema.get("properties") or {}
        if not isinstance(properties, dict):
            return False
        if any(name not in value for name in schema.get("required") or ()):
            return False
        for name, child in value.items():
            if name in properties and not _schema_accepts(child, properties[name], root):
                return False
            if name not in properties and schema.get("additionalProperties") is False:
                return False
    if isinstance(value, (list, tuple)) and isinstance(schema.get("items"), dict):
        if not all(_schema_accepts(item, schema["items"], root) for item in value):
            return False
    return True


def _replace_pointer(value, target, path=""):
    """Return a WRAP-authority view with one quarantined node withheld."""
    if path == target:
        return {"$wrap": "quarantined"}
    if isinstance(value, dict):
        return {key: _replace_pointer(
            child, target, path + "/" + _pointer_part(key))
                for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_replace_pointer(child, target, path + "/" + str(index))
                for index, child in enumerate(value)]
    return value


def _pointer_part(value) -> str:
    return str(value).replace("~", "~0").replace("/", "~1")


def _nodes(value, path=""):
    dump = getattr(value, "model_dump", None)
    if callable(dump): value = dump(mode="json")
    yield path, value
    if isinstance(value, dict):
        for key, child in value.items():
            yield from _nodes(child, path + "/" + _pointer_part(key))
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            yield from _nodes(child, path + "/" + str(index))


def _contains_value(container, value) -> bool:
    return any(node == value for _path, node in _nodes(container))


def _resolve_ref(receipts, ref):
    digest, marker, path = str(ref).partition("#")
    if not marker: return None
    for receipt in receipts:
        if receipt.digest != digest: continue
        for local_path, value in _nodes(receipt.value):
            if local_path != path: continue
            return value
    return None


def _source_names(spec) -> tuple[str, ...]:
    if not isinstance(spec, dict) or set(spec) != {"from"}:
        return ()
    value = spec["from"]
    return (value,) if isinstance(value, str) else tuple(value or ())


def _is_prose_node(value) -> bool:
    """Recognize textual carriers nested inside structured tool returns.

    Atomic labels such as channel names are deliberately excluded: treating a
    list of candidates as prose would let a semantic extractor choose an
    unproved argmin/argmax winner.
    """
    if not isinstance(value, str):
        return False
    words = value.split()
    return (len(words) >= 3 or
            (len(words) >= 2 and any(marker in value for marker in (":", "@", "\n"))))


@dataclass(frozen=True)
class Observation:
    source: str
    arguments: dict
    digest: str
    value: object = field(repr=False, compare=False)
    task_id: str = ""

    @classmethod
    def issue(cls, source: str, arguments: dict, value, task_id: str = ""):
        source, arguments, task_id = str(source), dict(arguments or {}), str(task_id)
        digest = hashlib.sha256(_stable({"task_id": task_id, "source": source,
                                         "arguments": arguments,
                                         "value": value}).encode()).hexdigest()
        return cls(source, arguments, digest, value, task_id)

    def to_dict(self) -> dict:
        return {"task_id": self.task_id, "source": self.source,
                "arguments": self.arguments, "digest": self.digest}

    def audit_dict(self) -> dict:
        return {"task_id": self.task_id, "source": self.source,
                "digest": self.digest,
                "arguments_digest": hashlib.sha256(
                    _stable(self.arguments).encode()).hexdigest()}

    def refs(self, expected) -> tuple[str, ...]:
        return tuple(self.digest + "#" + path for path, value in _nodes(self.value)
                     if value == expected)

    def facts(self) -> list[dict]:
        return [{"ref": self.digest + "#" + path, "value": value}
                for path, value in _nodes(self.value)
                if not isinstance(value, (dict, list, tuple))]


class RuntimeReceiptRecorder:
    """Own all live receipts for exactly one task run."""

    def __init__(self, task_id: str):
        task_id = str(task_id)
        if not task_id:
            raise ValueError("task_id must be nonempty")
        self.task_id = task_id
        self.observations: list[Observation] = []
        self._private_receipts: list[Observation] = []
        self.active = True

    def _require_active(self) -> None:
        if not self.active:
            raise RuntimeError(f"receipt recorder for task {self.task_id} is closed")

    def issue(self, source: str, arguments: dict, value, *, record: bool = True):
        self._require_active()
        receipt = Observation.issue(source, arguments, value, self.task_id)
        (self.observations if record else self._private_receipts).append(receipt)
        return receipt

    def snapshot(self) -> dict:
        return {"task_id": self.task_id,
                "receipts": [item.audit_dict() for item in self.observations]}

    def close(self) -> dict:
        if not self.active:
            return {"task_id": self.task_id, "receipts": [], "closed": True}
        audit = self.snapshot()
        for receipt in (*self.observations, *self._private_receipts):
            object.__setattr__(receipt, "arguments", {})
            object.__setattr__(receipt, "value", None)
        self.observations.clear()
        self._private_receipts.clear()
        self.active = False
        audit["closed"] = True
        return audit


@dataclass(frozen=True)
class _Resolved:
    """One proposal-time value derived from an immutable receipt snapshot."""
    value: object
    refs: tuple[str, ...]
    call: Observation | None = None
    proof: str = ""


@dataclass(frozen=True)
class ArgumentProvenance:
    """Expected Contract sources and immutable runtime inputs consulted for one argument."""
    sources: tuple[str, ...] = ()
    inputs: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"sources": list(self.sources), "inputs": list(self.inputs)}


@dataclass(frozen=True)
class Provenance:
    """Neutral runtime trace: proposal arguments linked to immutable receipts."""
    clause: str | None = None
    action: str = ""
    arguments: dict[str, ArgumentProvenance] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"clause": self.clause, "action": self.action,
                "arguments": {name: origin.to_dict()
                              for name, origin in self.arguments.items()}}


@dataclass(frozen=True)
class GateResult:
    """Result of checking neutral provenance against one pre-installed clause gate."""
    provenance: Provenance = field(default_factory=Provenance)
    conflicts: tuple[str, ...] = ()
    unresolved: tuple[str, ...] = ()

    @property
    def complete(self) -> bool:
        return self.provenance.clause is not None and not self.conflicts and not self.unresolved

    @property
    def clause(self):
        return self.provenance.clause

    @property
    def bindings(self):
        return {name: origin.inputs for name, origin in self.provenance.arguments.items()}

    def to_dict(self) -> dict:
        return {"provenance": self.provenance.to_dict(),
                "conflicts": list(self.conflicts), "unresolved": list(self.unresolved)}


@dataclass(frozen=True)
class InstalledGate:
    """Immutable task-time blueprint installed at one commit boundary."""
    clause: Clause
    action: str
    sources: tuple[str, ...]
    arguments: dict

    @classmethod
    def from_clause(cls, clause: Clause):
        if not isinstance(clause, EffectClause):
            raise ValueError("a WRAP gate requires an EffectClause")
        return cls(clause, clause.action, tuple(clause.sources),
                   dict(clause.effect_arguments))

    @property
    def id(self):
        return self.clause.id

