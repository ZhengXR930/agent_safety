# Authentication DAG for Small Local Tool-Use Guards

## One-Sentence Summary

Use an explicit authentication DAG as the symbolic validator for a small local
tool-use guard, so the guard can cheaply decide whether a proposed sensitive
tool action is actually authorized by the user.

## Problem

Tool-using agents often confuse evidence with authorization. A tool return,
webpage, skill instruction, retrieved document, or intermediate analysis may
suggest an action, but that does not mean the user authorized the action.

The core problem is therefore:

> Before executing a sensitive tool action, check whether its required authority
> can be derived from the user's grant under a small set of explicit DAG rules.

The practical target is a local guard that can run at high-frequency tool-call
boundaries without sending private traces, tool arguments, or user context to a
closed-source judge.

## Core Idea

Represent authorization as a directed derivation graph:

```text
user grant
  -> narrower scope grant
  -> authorized action class
  -> authorized action arguments
```

Tool outputs and external content may provide evidence, candidate targets, or
payload data, but they must not create user authority.

## Canonical Violations

- `A1 Fabricated Authorization`: no valid user grant exists for the action.
- `A2 Escalated Authorization`: evidence, observation, advice, or retrieved
  content is incorrectly upgraded into action authority.
- `A3 Exceeded Scope`: the user authorized the action class, but the concrete
  target, amount, recipient, time, payload, or side effect exceeds the grant.
- `D1 Source / Taint Failure`: an authority-bearing argument or sensitive
  payload is controlled by an untrusted source.

## Decision Rule

```text
if A1 or A2 or A3:
    block
elif D1:
    warn
else:
    allow
```

`warn` is reserved for cases where the action itself is authorized but the data
flow or payload source is risky. If the authority target itself is tainted, the
decision is `block`.

## Working Hypothesis

The project does not need to change topic if the innovation is framed as:

> Authentication DAG supplies the symbolic validator; a small local guard uses
> this validator as supervision, filtering, or consistency checking.

The DAG alone is not the final product. The small model alone is also not the
core contribution. The useful combination is:

```text
Authentication DAG rules
  -> symbolic validator
  -> labeled / filtered dangerous tool-use examples
  -> small local guard
  -> fast allow / warn / block at runtime
```

This preserves the original authorization-chain idea while making the
deployable contribution clearer: latency, privacy, local deployment, and lower
cost than closed LLM judges.

## Immediate Validation Target

Before training, the next experiment must test whether the symbolic validator
itself is useful:

- it should catch A1/A2/A3 violations better than a sensitive-tool blocker;
- it should not overblock clean high-permission tool use;
- it should correctly reserve `warn` for D1-only source/payload risk;
- it should produce labels stable enough to train or evaluate a small local
  guard.

If the symbolic validator fails this gate, the small-model part has no clean
supervision target.

## Scope

This repository now keeps the authentication DAG as the core mechanism and
small local dangerous tool-use guard as the plausible deployment framing.
Previous explorations around skill/MCP risk prediction, proof-as-paper-core
framing, AgentTrap-specific proof labels, broad multi-agent safety, and
literature collection were discarded as non-core.

The public validation boundary is now clearer:

- **In scope**: indirect tool-call attacks where external content, tool
  returns, retrieved documents, or intermediate evidence are laundered into
  action authority.
- **Out of scope for DAG alone**: direct harmful user intent. If the user
  explicitly asks for a harmful action, an authorization DAG can still find a
  valid user-rooted grant; a separate harm-policy model or rule layer is needed.

## Next Minimal Experiment

Use a small fixed set of tool-call traces to test:

- attack catch rate for A1/A2/A3 violations;
- clean allow rate for legitimate high-permission tasks;
- warn precision for D1-only payload/source risks;
- whether the DAG rules reduce errors compared with a simple sensitive-tool
  blocker.

## Current Evidence Snapshot

ToolSafe AgentDojo official trajectory validation supports the immediate gate:
the scope-aware Authentication DAG validator reaches F1=0.986, attack
catch=0.994, clean allow=0.946 on 489 official sensitive/action steps.

ToolSafe AgentHarm official trajectory validation falsifies a broader claim:
the same validator reaches only F1=0.110 and attack catch=0.059 on 190
sensitive/action steps under strict labels. This confirms that the idea should
not be framed as a universal harmful-tool-use guard unless a separate harm
policy component is added.
