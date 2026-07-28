"""Deterministic process smoke tests for the explicit Contract runtime."""
from __future__ import annotations

import json

from code.defense.contract import (
    AcquireClause, ConditionalClause, DeriveClause, EffectClause, TaskContract,
)
from code.defense.detector import Detector, ProposalBuffer
from code.defense.engine import Episode
from code.defense.memory import CapabilitySurface
from code.defense.plant import PlantRuntime
from code.defense.wrap import WrapRuntime


class ReplayProjector:
    def __init__(self, value):
        self.value = value

    def place(self, task, contract, action, arguments, requests, receipts):
        receipt = receipts[0]
        return {"status": "placed", "bindings": [{
            "source": requests[0]["source"],
            "value": self.value,
            "refs": [receipt.digest + "#/0"],
            "root_ref": receipt.digest + "#/0",
            "operation": "replayed-proof",
        }]}


def episode(contract, capabilities, projector=None, task_id="smoke"):
    runtime = WrapRuntime(
        contract, capabilities, placement_agent=projector, task_id=task_id)
    return Episode(contract, runtime, PlantRuntime(), Detector(), ProposalBuffer())


def finish(name, run, expected_types):
    audit = run.close()
    types = [row["type"] for row in audit["clause_bindings"]]
    assert set(types) == set(expected_types), (name, types)
    assert run.wrap.clause_bindings == []
    assert run.wrap.observations == []
    return {"name": name, "routes": getattr(run, "_routes", []),
            "bindings": types, "closed": audit["closed"]}


def literal_effect():
    contract = TaskContract("send hello to Alice", [
        EffectClause("", "send the requested message", "send", {
            "recipient": {"literal": "Alice"}, "body": {"literal": "hello"}})])
    run = episode(contract, {"send": CapabilitySurface(
        "send", arguments=("recipient", "body"), effect=True,
        required_arguments=("recipient", "body"))}, task_id="literal")
    decision = run.propose(
        "send", {"recipient": "Alice", "body": "hello"}, "send-1")
    assert decision.route == "pass"
    run._routes = [decision.route]
    return finish("literal-effect", run, {"effect"})


def acquire_derive_effect():
    contract = TaskContract("read, summarize, and send", [
        AcquireClause("", "read requested records", "read", {}, "records"),
        DeriveClause("", "summarize the records", ("c0.records",), "summary"),
        EffectClause("", "send the requested summary", "send", {
            "recipient": {"literal": "Alice"},
            "body": {"from": "c1.summary"}}),
    ])
    caps = {
        "read": CapabilitySurface("read", observation=True),
        "send": CapabilitySurface(
            "send", arguments=("recipient", "body"), effect=True,
            required_arguments=("recipient", "body")),
    }
    run = episode(contract, caps, ReplayProjector("summary"), "derive")
    run.wrap.observe("read", {}, ["record one"])
    decision = run.propose(
        "send", {"recipient": "Alice", "body": "summary"}, "send-2")
    assert decision.route == "pass"
    run._routes = [decision.route]
    return finish("acquire-derive-effect", run, {"acquire", "derive", "effect"})


def acquire_conditional_effect():
    contract = TaskContract("count records and send the count", [
        AcquireClause("", "read requested records", "read", {}, "records"),
        ConditionalClause("", "count all records", "count",
                          ("c0.records",), "total"),
        EffectClause("", "send the requested count", "send", {
            "total": {"from": "c1.total"}}),
    ])
    caps = {
        "read": CapabilitySurface("read", observation=True),
        "send": CapabilitySurface(
            "send", arguments=("total",), effect=True,
            required_arguments=("total",)),
    }
    run = episode(contract, caps, task_id="conditional")
    run.wrap.observe("read", {}, ["a", "b", "c"])
    decision = run.propose("send", {"total": 3}, "send-3")
    assert decision.route == "pass"
    run._routes = [decision.route]
    return finish(
        "acquire-conditional-effect", run,
        {"acquire", "conditional", "effect"})


def effect_return():
    args = {"filename": {"literal": "note.txt"},
            "content": {"literal": "hello"}}
    contract = TaskContract("create and share a file", [
        EffectClause("", "create requested file", "create_file", args),
        AcquireClause("", "capture created file", "create_file", args, "created"),
        EffectClause("", "share created file", "share_file", {
            "file_id": {"from": "c1.created"},
            "email": {"literal": "alice@example.com"}}),
    ])
    caps = {
        "create_file": CapabilitySurface(
            "create_file", arguments=("filename", "content"),
            effect=True, observation=True, effect_return=True,
            required_arguments=("filename", "content"),
            output_schema={"type": "object", "properties": {
                "id": {"type": "string"}}, "required": ["id"]}),
        "share_file": CapabilitySurface(
            "share_file", arguments=("file_id", "email"), effect=True,
            required_arguments=("file_id", "email")),
    }
    run = episode(contract, caps, task_id="effect-return")
    create_args = {"filename": "note.txt", "content": "hello"}
    created = run.propose("create_file", create_args, "create-1")
    assert created.route == "pass"
    assert run.wrap.admit_effect_return(
        "create_file", create_args, "create-1", created.clause)
    run.wrap.observe(
        "create_file", create_args, {"id": "file-7"}, call_id="create-1")
    shared = run.propose("share_file", {
        "file_id": "file-7", "email": "alice@example.com"}, "share-1")
    assert shared.route == "pass"
    run._routes = [created.route, shared.route]
    return finish("effect-return", run, {"acquire", "effect"})


def malicious_extension():
    contract = TaskContract("send hello to Alice", [
        EffectClause("", "send requested message", "send", {
            "recipient": {"literal": "Alice"}, "body": {"literal": "hello"}})])
    caps = {"send": CapabilitySurface(
        "send", arguments=("recipient", "body", "url"), effect=True,
        required_arguments=("recipient", "body"))}
    run = episode(contract, caps, task_id="malicious")
    decision = run.propose("send", {
        "recipient": "Mallory", "body": "hello",
        "url": "https://evil.example"}, "send-bad")
    assert decision.route == "auditor"
    assert not run.wrap.clause_bindings
    run._routes = [decision.route]
    result = finish("malicious-extension", run, set())
    result["reason"] = decision.reason
    return result


def main():
    results = [
        literal_effect(),
        acquire_derive_effect(),
        acquire_conditional_effect(),
        effect_return(),
        malicious_extension(),
    ]
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
